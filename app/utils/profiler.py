import threading
import time
from contextlib import contextmanager

_local = threading.local()


def reset_profiler() -> None:
    _local.timings = {}


def get_timings() -> dict[str, float]:
    return getattr(_local, "timings", {})


@contextmanager
def profile(name: str):
    start = time.perf_counter()
    try:
        yield
    finally:
        if not hasattr(_local, "timings"):
            _local.timings = {}

        _local.timings[name] = time.perf_counter() - start


def record(name: str, value: float) -> None:
    """
    Record externally measured values (e.g. Ollama timings)
    without using the context manager.
    """
    if not hasattr(_local, "timings"):
        _local.timings = {}

    _local.timings[name] = value


def record_ollama_metrics(data: dict) -> None:
    record("ollama.load", data["load_duration"] / 1e9)
    record("ollama.prompt_eval", data["prompt_eval_duration"] / 1e9)
    record("ollama.eval", data["eval_duration"] / 1e9)

    record("ollama.prompt_tokens", data["prompt_eval_count"])
    record("ollama.completion_tokens", data["eval_count"])

    prompt_seconds = data["prompt_eval_duration"] / 1e9
    eval_seconds = data["eval_duration"] / 1e9

    record(
        "ollama.prompt_tps",
        data["prompt_eval_count"] / prompt_seconds if prompt_seconds else 0,
    )

    record(
        "ollama.generation_tps",
        data["eval_count"] / eval_seconds if eval_seconds else 0,
    )
