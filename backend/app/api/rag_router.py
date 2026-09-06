import asyncio
import json
import logging
import uuid
from typing import Annotated

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.messaging.publisher import publish_chat_job
from app.models.chat import ChatMessage, ChatScope, ChatSession
from app.schemas.rag_schema import AskRequest
from app.services import document_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/rag",
    tags=["RAG"],
)


async def get_or_create_session(
    session_id: str | None, payload: AskRequest, db: AsyncSession
) -> ChatSession:
    """Finds existing session (and auto-titles it) or creates a new one with correct scope."""
    if session_id:
        result = await db.execute(
            select(ChatSession).filter(ChatSession.id == session_id)
        )
        session = result.scalars().first()
        if session:
            # THE FIX: If the UI created a blank "New Chat", rename it based on the first question
            if session.title == "New Chat":
                words = payload.question.split()
                session.title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
                db.add(session)
            return session

    # Fallback: Create a new session if the frontend forgot to initialize one
    new_id = str(uuid.uuid4())
    words = payload.question.split()
    title = " ".join(words[:5]) + ("..." if len(words) > 5 else "")

    # Infer scope from the payload
    scope_type = (
        ChatScope.ALL_DOCUMENTS
        if not payload.document_ids
        else ChatScope.SELECTED_DOCUMENTS
    )
    if len(payload.document_ids) == 1:
        scope_type = ChatScope.THIS_DOCUMENT

    new_session = ChatSession(
        id=new_id, title=title, scope_type=scope_type, document_ids=payload.document_ids
    )
    db.add(new_session)
    await db.commit()
    return new_session


async def fetch_sliding_window_history(
    session_id: str, db: AsyncSession, limit: int = 4
) -> list[ChatMessage]:
    """Fetches the last N messages to prevent LLM context overflow."""
    # BUG FIX: order by `seq` (stable insertion order), not `created_at`,
    # since user/assistant pairs can share an identical timestamp - see
    # the note in chat.py's get_recent_messages for full details.
    stmt = (
        select(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(desc(ChatMessage.seq))
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return list(reversed(messages))


# producer (fire and forget)
@router.post("/ask", status_code=status.HTTP_202_ACCEPTED)
async def ask(
    payload: AskRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Instantly saves the question, creates a placeholder for the answer,
    publishes to RabbitMQ, and returns the message IDs.
    """

    if payload.document_ids:
        # The router delegates business logic to the service
        missing_ids = await document_service.validate_document_ids(
            payload.document_ids, db
        )

        if missing_ids:
            # The router handles the HTTP response
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documents not found: {', '.join(missing_ids)}",
            )
    # Resolve the Chat Session
    active_session = await get_or_create_session(
        session_id=payload.session_id, payload=payload, db=db
    )

    # Save the User's Question instantly
    user_msg_id = str(uuid.uuid4())
    user_msg = ChatMessage(
        id=user_msg_id,
        session_id=active_session.id,
        role="user",
        content=payload.question,
        citations=[],
        document_ids=payload.document_ids,
    )
    db.add(user_msg)

    # ID so the frontend can listen for THIS specific message's tokens
    assistant_msg_id = str(uuid.uuid4())
    assistant_msg = ChatMessage(
        id=assistant_msg_id,
        session_id=active_session.id,
        role="assistant",
        content="",
        citations=[],
        status="queued",
        document_ids=payload.document_ids,
    )
    db.add(assistant_msg)

    await db.commit()

    # Hand the heavy work off to the ChatWorker running in a background process
    # Publish to RabbitMQ
    await publish_chat_job(
        message_id=assistant_msg_id,
        session_id=active_session.id,
        question=payload.question,
        document_ids=payload.document_ids,
    )

    # Return instantly.
    return {
        "session_id": active_session.id,
        "user_message_id": user_msg_id,
        "assistant_message_id": assistant_msg_id,
    }


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes an entire chat session and all its messages (via CASCADE)."""
    # 1. Fetch the session
    stmt = select(ChatSession).filter(ChatSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # 2. Delete it. Postgres CASCADE automatically drops the related chat_messages.
    await db.delete(session)
    await db.commit()

    return {"status": "success", "message": f"Session {session_id} deleted."}


# Initialize Valkey/Redis client pool (using the standard redis-py async client)
valkey_client = redis.from_url(
    settings.valkey_url,
    decode_responses=True,
    socket_timeout=None,  # Prevents read timeouts during XREAD block=5000
    socket_connect_timeout=5.0,
)  # Fails fast only if Valkey container is entirely down


@router.get("/stream/{message_id}")
async def stream_chat(message_id: str, request: Request, last_offset: str = "0"):
    stream_key = f"chat:stream:{message_id}"

    # THE FIX: Reconnects (hard refresh / tab switch / EventSource auto-retry)
    # now ALWAYS replay the stream from the very beginning ("0"), regardless of
    # what offset the client thinks it's at. Valkey keeps the full history for
    # 10 minutes (see Chatworker.py), and it's only a handful of small JSON
    # events, so there's no need for a fragile client-tracked offset. This
    # guarantees the UI can always deterministically reconstruct the exact
    # status message and any partial tokens generated so far, instead of
    # depending on `localStorage`/`Last-Event-ID` bookkeeping that can get out
    # of sync (or poisoned) across remounts.

    async def event_generator():
        current_offset = "0"

        # PHASE 0: WAIT FOR RETRIEVAL
        while True:
            async with AsyncSessionLocal() as db:
                stmt = select(ChatMessage).filter(ChatMessage.id == message_id)
                result = await db.execute(stmt)
                msg = result.scalar_one_or_none()

                if not msg:
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {"type": "error", "error": "Message not found."}
                        ),
                    }
                    return

                if msg.status == "completed":
                    citations = (
                        json.loads(msg.citations)
                        if isinstance(msg.citations, str)
                        else (msg.citations or [])
                    )
                    if msg.content:
                        yield {
                            "event": "message",
                            "data": json.dumps(
                                {"type": "token", "content": msg.content}
                            ),
                        }
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "done", "citations": citations}),
                    }
                    return

                if msg.status == "failed":
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {"type": "error", "error": "Generation failed."}
                        ),
                    }
                    return

            exists = await valkey_client.exists(stream_key)
            if exists:
                break

            yield {
                "event": "message",
                "data": json.dumps(
                    {"type": "status", "message": "Initializing worker..."}
                ),
            }
            await asyncio.sleep(2.0)

        try:
            # PHASE 1: FULL REPLAY
            # Always dump the entire buffered history (every status + token
            # event emitted so far) so a freshly (re)mounted React tree can
            # rebuild the exact UI state in one shot.
            historical = await valkey_client.xrange(stream_key, min="0", max="+")

            for msg_id, fields in historical:
                current_offset = msg_id
                yield {"event": "message", "id": msg_id, "data": fields["payload"]}

                payload_dict = json.loads(fields["payload"])
                if payload_dict.get("type") in ("done", "error"):
                    return

            # PHASE 2: LIVE TAILING
            while True:
                streams = await valkey_client.xread(
                    {stream_key: current_offset}, count=10, block=5000
                )

                if streams:
                    for _, messages in streams:
                        for msg_id, fields in messages:
                            current_offset = msg_id
                            yield {
                                "event": "message",
                                "id": msg_id,
                                "data": fields["payload"],
                            }

                            payload_dict = json.loads(fields["payload"])
                            if payload_dict.get("type") in ("done", "error"):
                                return
                else:
                    async with AsyncSessionLocal() as db:
                        stmt = select(ChatMessage).filter(ChatMessage.id == message_id)
                        result = await db.execute(stmt)
                        msg = result.scalar_one_or_none()

                        if msg and msg.status == "completed":
                            citations = (
                                json.loads(msg.citations)
                                if isinstance(msg.citations, str)
                                else (msg.citations or [])
                            )
                            done_payload = json.dumps(
                                {"type": "done", "citations": citations}
                            )
                            yield {
                                "event": "message",
                                "id": current_offset,
                                "data": done_payload,
                            }
                            return
                        elif msg and msg.status == "failed":
                            error_payload = json.dumps(
                                {"type": "error", "error": "Worker crashed."}
                            )
                            yield {
                                "event": "message",
                                "id": current_offset,
                                "data": error_payload,
                            }
                            return

                    ping = json.dumps({"type": "ping", "message": "still thinking..."})
                    yield {"event": "message", "id": current_offset, "data": ping}

        finally:
            pass

    return EventSourceResponse(event_generator())
