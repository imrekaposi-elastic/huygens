#!/usr/bin/env python3
"""Generate Huygens architecture Excalidraw diagrams (boxes + arrows)."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parents[1] / "docs" / "architecture" / "diagrams"

# Excalidraw palette
C_USER = "#ffc9c9"
C_UI = "#d0bfff"
C_SVC = "#a5d8ff"
C_DATA = "#b2f2bb"
C_INFRA = "#ffec99"
C_AGENT = "#ffd8a8"
C_BUS = "#e599f7"
C_BORDER = "#1e1e1e"


def _seed() -> int:
    return random.randint(1, 2**31 - 1)


class Diagram:
    def __init__(self) -> None:
        self.elements: list[dict[str, Any]] = []
        self._underlay: list[dict[str, Any]] = []
        self._boxes: dict[str, dict[str, float]] = {}

    def box(
        self,
        eid: str,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        *,
        bg: str = C_SVC,
        font_size: int = 16,
        stroke_style: str = "solid",
        underlay: bool = False,
    ) -> str:
        self._boxes[eid] = {"x": x, "y": y, "w": w, "h": h}
        target = self._underlay if underlay else self.elements
        s = _seed()
        rect: dict[str, Any] = {
            "id": eid,
            "type": "rectangle",
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "angle": 0,
            "strokeColor": C_BORDER,
            "backgroundColor": bg,
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": stroke_style,
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 3},
            "seed": s,
            "version": 1,
            "versionNonce": s + 1,
            "isDeleted": False,
            "boundElements": [{"id": f"{eid}-txt", "type": "text"}],
            "updated": 1,
            "link": None,
            "locked": False,
        }
        target.append(rect)
        tid = f"{eid}-txt"
        if not label:
            return eid
        target.append(
            {
                "id": tid,
                "type": "text",
                "x": x + 8,
                "y": y + h / 2 - (label.count("\n") + 1) * font_size * 0.35,
                "width": w - 16,
                "height": h - 8,
                "angle": 0,
                "strokeColor": C_BORDER,
                "backgroundColor": "transparent",
                "fillStyle": "solid",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 0,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "roundness": None,
                "seed": s + 2,
                "version": 1,
                "versionNonce": s + 3,
                "isDeleted": False,
                "boundElements": None,
                "updated": 1,
                "link": None,
                "locked": False,
                "text": label,
                "fontSize": font_size,
                "fontFamily": 1,
                "textAlign": "center",
                "verticalAlign": "middle",
                "containerId": eid,
                "originalText": label,
                "autoResize": True,
                "lineHeight": 1.25,
            }
        )
        return eid

    def label(self, eid: str, x: float, y: float, text: str, *, size: int = 20) -> None:
        s = _seed()
        self.elements.append(
            {
                "id": eid,
                "type": "text",
                "x": x,
                "y": y,
                "width": len(text) * size * 0.55,
                "height": size * 1.4,
                "angle": 0,
                "strokeColor": C_BORDER,
                "backgroundColor": "transparent",
                "fillStyle": "solid",
                "strokeWidth": 1,
                "strokeStyle": "solid",
                "roughness": 0,
                "opacity": 100,
                "groupIds": [],
                "frameId": None,
                "roundness": None,
                "seed": s,
                "version": 1,
                "versionNonce": s + 1,
                "isDeleted": False,
                "boundElements": None,
                "updated": 1,
                "link": None,
                "locked": False,
                "text": text,
                "fontSize": size,
                "fontFamily": 1,
                "textAlign": "left",
                "verticalAlign": "top",
                "containerId": None,
                "originalText": text,
                "autoResize": True,
                "lineHeight": 1.25,
            }
        )

    def arrow(
        self,
        eid: str,
        src: str,
        dst: str,
        *,
        src_side: str = "bottom",
        dst_side: str = "top",
        label: str | None = None,
        dashed: bool = False,
    ) -> None:
        sb = self._boxes[src]
        db = self._boxes[dst]
        sx, sy = self._anchor(sb, src_side)
        ex, ey = self._anchor(db, dst_side)
        dx, dy = ex - sx, ey - sy
        s = _seed()
        focus_map = {
            "top": [0, -1],
            "bottom": [0, 1],
            "left": [-1, 0],
            "right": [1, 0],
        }
        el: dict[str, Any] = {
            "id": eid,
            "type": "arrow",
            "x": sx,
            "y": sy,
            "width": dx,
            "height": dy,
            "angle": 0,
            "strokeColor": C_BORDER,
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 2,
            "strokeStyle": "dashed" if dashed else "solid",
            "roughness": 1,
            "opacity": 100,
            "groupIds": [],
            "frameId": None,
            "roundness": {"type": 2},
            "seed": s,
            "version": 1,
            "versionNonce": s + 1,
            "isDeleted": False,
            "boundElements": None,
            "updated": 1,
            "link": None,
            "locked": False,
            "points": [[0, 0], [dx, dy]],
            "lastCommittedPoint": None,
            "startBinding": {
                "elementId": src,
                "focus": focus_map[src_side],
                "gap": 6,
            },
            "endBinding": {
                "elementId": dst,
                "focus": focus_map[dst_side],
                "gap": 6,
            },
            "startArrowhead": None,
            "endArrowhead": "arrow",
        }
        self.elements.append(el)
        if label:
            self.label(
                f"{eid}-lbl",
                sx + dx / 2 - 40,
                sy + dy / 2 - 20,
                label,
                size=14,
            )

    @staticmethod
    def _anchor(b: dict[str, float], side: str) -> tuple[float, float]:
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        if side == "top":
            return x + w / 2, y
        if side == "bottom":
            return x + w / 2, y + h
        if side == "left":
            return x, y + h / 2
        return x + w, y + h / 2

    def to_file(self) -> dict[str, Any]:
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "https://huygens.dev",
            "elements": self._underlay + self.elements,
            "appState": {
                "gridSize": 20,
                "viewBackgroundColor": "#ffffff",
            },
            "files": {},
        }


def diagram_system_context() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — System context", size=28)
    d.box("cp-boundary", 20, 250, 500, 250, "", bg="#f8f9fa", stroke_style="dashed", underlay=True)
    d.label("cp-lbl", 30, 255, "Control plane", size=14)
    d.box("operator", 320, 60, 160, 56, "Operator", bg=C_USER)
    d.box("console", 280, 160, 240, 64, "Web console\n(Phase 5)", bg=C_UI)
    d.box("iam", 40, 280, 140, 72, "IAM\n(local auth)", bg=C_SVC)
    d.box("registry", 200, 280, 140, 72, "Registry\n(agents)", bg=C_SVC)
    d.box("inventory", 360, 280, 140, 72, "Inventory\n(poller)", bg=C_SVC)
    d.box("pg", 80, 420, 160, 64, "PostgreSQL\n(SoR)", bg=C_DATA)
    d.box("kafka", 280, 420, 160, 64, "Kafka", bg=C_BUS)
    d.box("es", 480, 420, 160, 64, "Elasticsearch\n(audit ECS)", bg=C_DATA)
    d.box("agent", 560, 160, 180, 88, "Libvirt agent\n(hypervisor)", bg=C_AGENT)

    d.arrow("a1", "operator", "console")
    d.arrow("a2", "console", "iam", src_side="bottom", dst_side="top")
    d.arrow("a3", "console", "registry", src_side="bottom", dst_side="top")
    d.arrow("a4", "console", "inventory", src_side="bottom", dst_side="top")
    d.arrow("a5", "iam", "pg", src_side="bottom", dst_side="top")
    d.arrow("a6", "registry", "pg", src_side="bottom", dst_side="top")
    d.arrow("a7", "inventory", "pg", src_side="bottom", dst_side="top")
    d.arrow("a8", "inventory", "kafka", src_side="bottom", dst_side="top")
    d.arrow("a9", "agent", "kafka", src_side="left", dst_side="right", label="events")
    d.arrow("a10", "registry", "agent", src_side="right", dst_side="left", label="enroll")
    d.arrow("a11", "inventory", "agent", src_side="right", dst_side="bottom", label="poll")
    d.arrow("a12", "kafka", "es", src_side="right", dst_side="left", label="audit")
    return d


def diagram_deployment() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Deployment topology", size=28)
    d.box("host", 40, 80, 320, 380, "", bg="#f8f9fa", stroke_style="dashed", underlay=True)
    d.box("cluster", 400, 80, 360, 380, "", bg="#f8f9fa", stroke_style="dashed", underlay=True)
    d.label("host-lbl", 50, 88, "Hypervisor host (e.g. dommel)", size=16)
    d.box("systemd", 60, 130, 280, 56, "systemd\nhuy-libvirt-agent", bg=C_AGENT)
    d.box("agent-api", 60, 210, 280, 64, "FastAPI agent :8080", bg=C_AGENT)
    d.box("libvirt", 60, 300, 130, 72, "libvirt / KVM", bg=C_INFRA)
    d.box("vms", 210, 300, 130, 72, "VMs + vnets\n(lab0, …)", bg=C_DATA)
    d.label("cluster-lbl", 410, 88, "Control plane (K8s or VMs, Phase 10+)", size=16)
    d.box("iam", 420, 130, 150, 56, "huy-iam", bg=C_SVC)
    d.box("reg", 590, 130, 150, 56, "huy-registry", bg=C_SVC)
    d.box("inv", 420, 210, 150, 56, "huy-inventory", bg=C_SVC)
    d.box("pg", 590, 210, 150, 56, "PostgreSQL", bg=C_DATA)
    d.box("kafka", 420, 290, 150, 56, "Kafka", bg=C_BUS)
    d.box("otel", 590, 290, 150, 56, "OTel / EDOT\n(optional)", bg=C_INFRA)
    d.box("es", 505, 370, 150, 56, "Elasticsearch\n(optional)", bg=C_DATA)

    d.arrow("d1", "agent-api", "libvirt", label="write queue")
    d.arrow("d2", "agent-api", "vms", src_side="right", dst_side="left", label="read path")
    d.arrow("d3", "systemd", "agent-api")
    d.arrow("d4", "agent-api", "reg", src_side="right", dst_side="left", label="HTTPS")
    d.arrow("d5", "inv", "agent-api", src_side="left", dst_side="right", label="poll")
    d.arrow("d6", "reg", "pg")
    d.arrow("d7", "inv", "kafka")
    d.arrow("d8", "kafka", "es", dashed=True)
    return d


def diagram_tenancy() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Tenancy model", size=28)
    d.box("org", 300, 60, 200, 56, "Organization", bg=C_USER)
    d.box("provider", 80, 160, 160, 56, "Provider", bg=C_SVC)
    d.box("region", 80, 260, 160, 56, "Region", bg=C_SVC)
    d.box("agent", 80, 360, 160, 64, "Agent", bg=C_AGENT)
    d.box("project", 480, 160, 160, 56, "Project", bg=C_SVC)
    d.box("vnet", 400, 280, 140, 56, "VNet", bg=C_DATA)
    d.box("vm", 560, 280, 140, 56, "VM", bg=C_DATA)
    d.box("compliance", 480, 60, 200, 56, "Org compliance\ncatalog", bg=C_INFRA)
    d.box("criticality", 560, 380, 180, 64, "Asset criticality\nassignment", bg=C_INFRA)

    d.arrow("t1", "org", "provider", src_side="left", dst_side="top")
    d.arrow("t2", "provider", "region")
    d.arrow("t3", "region", "agent")
    d.arrow("t4", "org", "project", src_side="right", dst_side="top")
    d.arrow("t5", "project", "vnet")
    d.arrow("t6", "project", "vm", src_side="right", dst_side="left")
    d.arrow("t7", "org", "compliance", src_side="right", dst_side="left")
    d.arrow("t8", "vm", "criticality")
    d.arrow("t9", "compliance", "criticality", src_side="bottom", dst_side="top", dashed=True)
    d.label("note", 40, 460, "RBAC scoped by organization_id · platform_admin registers agents", size=14)
    return d


def diagram_dual_io() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Libvirt agent — Dual I/O (ADR 0006)", size=28)
    d.box("api", 280, 60, 240, 56, "FastAPI routes", bg=C_UI)
    d.box("write-q", 80, 180, 200, 72, "Write queue\n(serialized)", bg=C_AGENT)
    d.box("read", 520, 180, 200, 72, "Read path\n(non-blocking)", bg=C_AGENT)
    d.box("libvirt-w", 80, 320, 200, 64, "libvirt\nmutations", bg=C_INFRA)
    d.box("libvirt-r", 520, 320, 200, 64, "libvirt\nlist / metrics", bg=C_INFRA)
    d.box(
        "ops-w",
        40,
        420,
        280,
        100,
        "define, create, destroy\nnetwork start/stop",
        bg="#f8f9fa",
        stroke_style="dashed",
        underlay=True,
    )
    d.box(
        "ops-r",
        480,
        420,
        280,
        100,
        "list_*, domain_state\nDHCP lease IP (no qemu-ga block)",
        bg="#f8f9fa",
        stroke_style="dashed",
        underlay=True,
    )

    d.arrow("w1", "api", "write-q", src_side="left", dst_side="top")
    d.arrow("w2", "api", "read", src_side="right", dst_side="top")
    d.arrow("w3", "write-q", "libvirt-w")
    d.arrow("w4", "read", "libvirt-r")
    d.label("warn", 200, 540, "Poller & GET /networks must use read path only", size=14)
    return d


def diagram_event_flow() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Event flow (Kafka)", size=28)
    d.box("agent", 40, 140, 140, 72, "Libvirt\nagent", bg=C_AGENT)
    d.box("inv", 40, 280, 140, 72, "Inventory\npoller", bg=C_SVC)
    d.box("svc", 40, 420, 140, 72, "All services", bg=C_SVC)
    d.box("t-agent", 240, 140, 220, 56, "huy.agent.events", bg=C_BUS)
    d.box("t-inv", 240, 280, 220, 56, "huy.inventory.snapshots", bg=C_BUS)
    d.box("t-audit", 240, 420, 220, 56, "huy.audit.events", bg=C_BUS)
    d.box("reg", 520, 120, 140, 56, "Registry", bg=C_SVC)
    d.box("pg", 520, 200, 140, 56, "PostgreSQL", bg=C_DATA)
    d.box("console", 520, 300, 140, 56, "Console", bg=C_UI)
    d.box("es", 520, 420, 140, 56, "ES ingest", bg=C_DATA)

    d.arrow("e1", "agent", "t-agent", src_side="right", dst_side="left")
    d.arrow("e2", "inv", "t-inv", src_side="right", dst_side="left")
    d.arrow("e3", "svc", "t-audit", src_side="right", dst_side="left")
    d.arrow("e4", "t-agent", "reg", label="consume")
    d.arrow("e5", "t-inv", "pg")
    d.arrow("e6", "t-inv", "console", src_side="right", dst_side="left")
    d.arrow("e7", "t-audit", "es")
    d.label("ce", 240, 80, "CloudEvents 1.0 envelope + JSON data (schemas/kafka/)", size=14)
    return d


def diagram_phases() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Delivery phases", size=28)
    phases = [
        ("p0", 40, 120, "Phase 0\nFoundation"),
        ("p1a", 180, 120, "Phase 1a\nIAM"),
        ("p1b", 320, 120, "Phase 1b\nAgent I/O"),
        ("p1", 460, 120, "Phase 1\nRegistry"),
        ("p2", 600, 120, "Phase 2\nSSO"),
        ("p3", 180, 240, "Phase 3\nProjects"),
        ("p5", 320, 240, "Phase 5\nConsole"),
        ("p7", 460, 240, "Phase 7\nCompliance"),
        ("p11", 600, 240, "Phase 11\nKubernetes"),
    ]
    for eid, x, y, lbl in phases:
        d.box(eid, x, y, 120, 72, lbl, bg=C_SVC if "0" not in eid else C_INFRA)
    for a, b in [
        ("p0", "p1a"),
        ("p1a", "p1b"),
        ("p1b", "p1"),
        ("p1", "p2"),
        ("p2", "p3"),
        ("p3", "p5"),
        ("p5", "p7"),
        ("p7", "p11"),
    ]:
        d.arrow(f"ph-{a}-{b}", a, b, src_side="right", dst_side="left")
    d.arrow("ph-1-3", "p1", "p3", src_side="bottom", dst_side="top")
    return d


def diagram_air_gapped() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Air-gapped deployment", size=28)
    d.box("boundary", 40, 70, 720, 420, "", bg="#fff5f5", stroke_style="dashed", underlay=True)
    d.label("b-lbl", 50, 78, "Customer network — no outbound internet", size=16)
    d.box("agents", 60, 120, 160, 80, "Agents\n(hypervisors)", bg=C_AGENT)
    d.box("cp", 260, 120, 280, 80, "Control plane\nIAM · Registry · Inventory", bg=C_SVC)
    d.box("pg", 580, 120, 160, 80, "PostgreSQL", bg=C_DATA)
    d.box("kafka", 260, 240, 160, 72, "Kafka\n(on-site)", bg=C_BUS)
    d.box("es", 460, 240, 160, 72, "Elasticsearch\n(BYO, optional)", bg=C_DATA)
    d.box("edot", 260, 360, 160, 72, "EDOT collector\n(offline bundle)", bg=C_INFRA)
    d.box("blocked", 580, 360, 160, 72, "Internet /\nElastic Cloud", bg="#ffc9c9", stroke_style="dashed")

    d.arrow("ag1", "agents", "cp", src_side="right", dst_side="left")
    d.arrow("ag2", "cp", "pg", src_side="right", dst_side="left")
    d.arrow("ag3", "cp", "kafka")
    d.arrow("ag4", "kafka", "es", dashed=True)
    d.arrow("ag5", "edot", "es", src_side="right", dst_side="left", label="OTLP")
    d.arrow("ag6", "blocked", "es", src_side="left", dst_side="right", label="blocked", dashed=True)
    d.label("note", 60, 500, "Degraded: poll-only without Kafka · audit in PG without ES", size=14)
    return d


DIAGRAMS = [
    ("01-system-context", diagram_system_context),
    ("02-deployment", diagram_deployment),
    ("03-tenancy", diagram_tenancy),
    ("04-agent-dual-io", diagram_dual_io),
    ("05-event-flow", diagram_event_flow),
    ("06-phase-roadmap", diagram_phases),
    ("07-air-gapped", diagram_air_gapped),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, builder in DIAGRAMS:
        path = OUT / f"{name}.excalidraw"
        doc = builder().to_file()
        path.write_text(json.dumps(doc, indent=2) + "\n")
        print(f"wrote {path} ({len(doc['elements'])} elements)")


if __name__ == "__main__":
    main()
