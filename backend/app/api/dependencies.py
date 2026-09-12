import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import settings

# HTTPBearer automatically looks for the "Authorization: Bearer ..." header
security = HTTPBearer()

# 1. Initialize the JWKS client.
# This fetches Supabase's public keys dynamically so you don't need a hardcoded secret.
jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(jwks_url)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    Decodes the Supabase JWT, verifies the signature dynamically via JWKS,
    and returns the user_id. Fails with 401 if the token is missing, expired, or forged.
    """
    token = credentials.credentials
    try:
        # 2. Fetch the correct public key for this specific token header
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # 3. Decode and verify using the public key and modern algorithms
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256", "HS256"],
            audience="authenticated",
        )

        # Extract the subject (user_id)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )

        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token signature: {e}",
        )
    except Exception:#noqa
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )
