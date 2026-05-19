"""Inventory service entrypoint (Phase 0 scaffold)."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

from huy_inventory import __version__

app = FastAPI(
    title="Huygens Inventory",
    version=__version__,
    description="Agent inventory poller (Phase 1)",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "huy-inventory", "version": __version__}


def run() -> None:
    host = os.getenv("HUY_INVENTORY_HOST", "127.0.0.1")
    port = int(os.getenv("HUY_INVENTORY_PORT", "8083"))
    uvicorn.run("huy_inventory.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
