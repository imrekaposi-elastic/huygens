"""IAM service entrypoint (Phase 0 scaffold)."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from huy_iam import __version__

app = FastAPI(
    title="Huygens IAM",
    version=__version__,
    description="Local authentication and RBAC (Phase 1a)",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "huy-iam", "version": __version__}


def run() -> None:
    uvicorn.run("huy_iam.main:app", host="127.0.0.1", port=8081, reload=False)


if __name__ == "__main__":
    run()
