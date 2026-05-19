"""Registry service entrypoint (Phase 0 scaffold)."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

from huy_registry import __version__

app = FastAPI(
    title="Huygens Registry",
    version=__version__,
    description="Agent enrollment and token vault (Phase 1)",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "huy-registry", "version": __version__}


def run() -> None:
    host = os.getenv("HUY_REGISTRY_HOST", "127.0.0.1")
    port = int(os.getenv("HUY_REGISTRY_PORT", "8082"))
    uvicorn.run("huy_registry.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
