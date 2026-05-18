#!/usr/bin/env python3
"""Export OpenAPI schema to openapi/openapi.json."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Minimal env for schema generation
os.environ.setdefault("HUY_AGENT_TOKEN", "export-token")
os.environ.setdefault("HUY_AGENT_COUNTRY", "NL")
os.environ.setdefault("HUY_AGENT_CITY", "Amsterdam")
os.environ.setdefault("HUY_AGENT_COMPANY", "Huygens")
os.environ.setdefault("HUY_DATA_DIR", "/tmp/huy-libvirt-agent")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from huy_libvirt_agent.config import get_settings
from huy_libvirt_agent.main import create_app

get_settings.cache_clear()
app = create_app()
schema = app.openapi()
out_dir = ROOT / "openapi"
out_dir.mkdir(exist_ok=True)
out_path = out_dir / "openapi.json"
out_path.write_text(json.dumps(schema, indent=2))
print(f"Wrote {out_path}")
