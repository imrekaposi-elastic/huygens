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
C_DONE = "#ffd43b"  # completed phases (roadmap) — distinct from planned blue #a5d8ff
C_LOW = "#e9ecef"  # lowest-priority planned phase (14)
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
        curved: bool = True,
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
            "roundness": {"type": 2} if curved else None,
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
    """Top-down: console → IAM/projects/inventory; agent HTTPS; Kafka → ES for audit/search."""
    d = Diagram()
    d.label("title", 40, 20, "Huygens — System context", size=28)
    d.label(
        "flow",
        40,
        52,
        "PG = system of record · ES = audit/search · inventory snapshots → Kafka → SSE (Phase 5 ✅)",
        size=14,
    )

    d.box("cp-boundary", 40, 200, 760, 440, "", bg="#f8f9fa", stroke_style="dashed", underlay=True)
    d.label("cp-lbl", 50, 206, "Control plane", size=14)

    d.box("operator", 320, 70, 160, 52, "Operator", bg=C_USER)
    d.box("console", 220, 150, 360, 56, "Web console", bg=C_UI)
    d.box("iam", 100, 250, 150, 64, "IAM", bg=C_SVC)
    d.box("projects", 500, 250, 170, 64, "Projects\n(proxy + CRUD)", bg=C_SVC)
    d.box("inventory-api", 300, 250, 150, 64, "Inventory\n(read API)", bg=C_SVC)
    d.box("registry", 160, 370, 150, 64, "Registry", bg=C_SVC)
    d.box("inventory-poller", 480, 370, 150, 64, "Inventory\npoller", bg=C_SVC)
    d.box("kafka", 200, 490, 200, 56, "Kafka\n(event bus)", bg=C_BUS)
    d.box("es", 500, 490, 220, 56, "Elasticsearch\naudit · sessions · search", bg=C_DATA)
    d.box("pg", 120, 600, 560, 56, "PostgreSQL (system of record)", bg=C_DATA)

    d.box("agent", 820, 360, 150, 72, "Libvirt agent", bg=C_AGENT)

    # Operator journey
    d.arrow("a1", "operator", "console")
    d.arrow("a2", "console", "iam", src_side="bottom", dst_side="top", label="auth")
    d.arrow("a3", "console", "projects", src_side="bottom", dst_side="top", label="mutate")
    d.arrow("a4", "console", "inventory-api", src_side="bottom", dst_side="top", label="read + SSE")

    # Projects → registry for agent connect (not inventory)
    d.arrow("a5", "projects", "registry", src_side="bottom", dst_side="top", label="connect")

    # Direct HTTPS to hypervisor (implemented)
    d.arrow("a6", "inventory-poller", "agent", src_side="right", dst_side="left", label="poll")
    d.arrow("a7", "projects", "agent", src_side="right", dst_side="left", label="proxy")

    # Kafka event bus (partially WIP — see ADR 0004)
    d.arrow("a8", "inventory-poller", "kafka", src_side="bottom", dst_side="top", label="snapshots")
    d.arrow("a9", "agent", "kafka", src_side="left", dst_side="top", label="events", dashed=True)
    d.arrow("a10", "registry", "kafka", src_side="bottom", dst_side="top", label="consume", dashed=True)
    d.arrow("a11", "kafka", "es", src_side="right", dst_side="left", label="audit ingest")

    # System of record + operational DB for inventory API
    d.arrow("a12", "iam", "pg", src_side="bottom", dst_side="top")
    d.arrow("a13", "projects", "pg", src_side="bottom", dst_side="top")
    d.arrow("a14", "registry", "pg", src_side="bottom", dst_side="top")
    d.arrow("a15", "inventory-poller", "pg", src_side="bottom", dst_side="top")
    d.arrow("a16", "inventory-api", "pg", src_side="bottom", dst_side="top")
    return d


def diagram_deployment() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Deployment topology", size=28)
    d.box("host", 40, 80, 320, 380, "", bg="#f8f9fa", stroke_style="dashed", underlay=True)
    d.label("host-lbl", 50, 88, "Hypervisor host (e.g. dommel)", size=16)
    d.box("systemd", 60, 130, 280, 56, "systemd\nhuy-libvirt-agent", bg=C_AGENT)
    d.box("agent-api", 60, 210, 280, 64, "FastAPI agent :8080", bg=C_AGENT)
    d.box("libvirt", 60, 300, 130, 72, "libvirt / KVM", bg=C_INFRA)
    d.box("vms", 210, 300, 130, 72, "VMs + vnets\n(lab0, …)", bg=C_DATA)
    d.label("cluster-lbl", 410, 88, "Control plane (K8s or VMs, Phase 10+)", size=16)
    d.box("cluster", 400, 80, 400, 380, "", bg="#f8f9fa", stroke_style="dashed", underlay=True)
    d.box("web", 420, 130, 115, 56, "web\n(nginx)", bg=C_UI)
    d.box("iam", 550, 130, 115, 56, "huy-iam", bg=C_SVC)
    d.box("reg", 680, 130, 100, 56, "huy-registry", bg=C_SVC)
    d.box("proj", 420, 210, 115, 56, "huy-projects", bg=C_SVC)
    d.box("inv", 550, 210, 115, 56, "huy-inventory", bg=C_SVC)
    d.box("pg", 680, 210, 100, 56, "PostgreSQL", bg=C_DATA)
    d.box("kafka", 420, 290, 115, 56, "Kafka", bg=C_BUS)
    d.box("otel", 550, 290, 115, 56, "OTel / EDOT\n(optional)", bg=C_INFRA)
    d.box("es", 680, 290, 100, 56, "Elasticsearch\n(optional)", bg=C_DATA)

    d.arrow("d0", "web", "iam", label="proxy")
    d.arrow("d0b", "web", "proj", src_side="bottom", dst_side="top")
    d.arrow("d1", "agent-api", "libvirt", label="write queue")
    d.arrow("d2", "agent-api", "vms", src_side="right", dst_side="left", label="read path")
    d.arrow("d3", "systemd", "agent-api")
    d.arrow("d4", "inv", "agent-api", src_side="left", dst_side="right", label="poll")
    d.arrow("d5", "proj", "agent-api", src_side="left", dst_side="right", label="proxy")
    d.arrow("d6", "proj", "reg", src_side="left", dst_side="top", label="connect")
    d.arrow("d7", "reg", "pg")
    d.arrow("d8", "inv", "kafka")
    d.arrow("d9", "proj", "pg", src_side="bottom", dst_side="top")
    d.arrow("d10", "kafka", "es", dashed=True)
    return d


def diagram_tenancy() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Tenancy model", size=28)
    d.box("org", 300, 60, 200, 56, "Organization", bg=C_USER)
    d.box("provider", 80, 160, 160, 56, "Provider", bg=C_SVC)
    d.box("region", 80, 260, 160, 56, "Region", bg=C_SVC)
    d.box("agent", 80, 360, 160, 64, "Agent", bg=C_AGENT)
    d.box("project", 480, 160, 160, 56, "Project\n(projects svc)", bg=C_SVC)
    d.box("proj-api", 300, 260, 150, 56, "Projects API\n(proxy)", bg=C_SVC)
    d.box("vnet", 400, 280, 140, 56, "VNet", bg=C_DATA)
    d.box("vm", 560, 280, 140, 56, "VM", bg=C_DATA)
    d.box("compliance", 480, 60, 200, 56, "Org compliance\ncatalog", bg=C_INFRA)
    d.box("criticality", 560, 380, 180, 64, "Asset criticality\nassignment", bg=C_INFRA)

    d.arrow("t1", "org", "provider", src_side="left", dst_side="top")
    d.arrow("t2", "provider", "region")
    d.arrow("t3", "region", "agent")
    d.arrow("t4", "org", "project", src_side="right", dst_side="top")
    d.arrow("t4b", "proj-api", "project", src_side="right", dst_side="left", label="CRUD")
    d.arrow("t4c", "proj-api", "agent", src_side="left", dst_side="right", label="proxy", dashed=True)
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
    d.label("ce", 40, 52, "Left → right · CloudEvents 1.0 + JSON (schemas/kafka/)", size=14)

    row_h = 56
    y1, y2, y3, y4, y5 = 110, 190, 270, 350, 430
    side = {"src_side": "right", "dst_side": "left", "curved": False}

    # Column 1 — publishers
    d.box("agent", 40, y1, 130, row_h, "Libvirt\nagent", bg=C_AGENT)
    d.box("inv", 40, y2, 130, row_h, "Inventory\npoller", bg=C_SVC)
    d.box("proj-link", 40, y3, 130, row_h, "Projects\nlink recon.", bg=C_SVC)
    d.box("svc", 40, y4, 130, row_h, "All services\n(audit)", bg=C_SVC)
    # Column 2 — Kafka topics
    d.box("t-agent", 220, y1, 230, 52, "huy.agent.events", bg=C_BUS)
    d.box("t-inv", 220, y2, 230, 52, "huy.inventory.snapshots", bg=C_BUS)
    d.box("t-links", 220, y3, 230, 52, "huy.network.links", bg=C_BUS)
    d.box("t-audit", 220, y4, 230, 52, "huy.audit.events", bg=C_BUS)
    # Column 3 — consumers
    d.box("reg", 520, y1, 130, 52, "Registry", bg=C_SVC)
    d.box("pg", 520, y2, 130, 52, "PostgreSQL", bg=C_DATA)
    d.box("console", 690, y2, 130, 52, "Console", bg=C_UI)
    d.box(
        "links-mvp",
        520,
        y3,
        300,
        52,
        "No topic consumer (MVP) · topology via GET /topology",
        bg="#f8f9fa",
        stroke_style="dashed",
        font_size=13,
    )
    d.box("es", 520, y5, 130, 52, "ES ingest", bg=C_DATA)

    d.arrow("e1", "agent", "t-agent", **side)
    d.arrow("e2", "inv", "t-inv", **side)
    d.arrow("e2b", "proj-link", "t-links", **side)
    d.arrow("e3", "svc", "t-audit", **side)
    d.arrow("e4", "t-agent", "reg", label="consume", **side)
    d.arrow("e5", "t-inv", "pg", **side)
    d.arrow("e6", "t-inv", "console", label="SSE hub", **side)
    d.arrow("e7", "t-audit", "es", **side)
    d.arrow("e8", "t-links", "links-mvp", label="publish only", **side, dashed=True)
    return d


def diagram_phases() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Delivery phases 0–17", size=28)
    d.label(
        "legend",
        40,
        52,
        "Yellow = complete  ·  Blue = planned  ·  Grey = adoption track 14–17 (lowest priority, RO)",
        size=14,
    )

    # (id, label, status) — status: done | planned | low
    phases_spec: list[tuple[str, str, str]] = [
        ("p0", "0\nFoundation", "done"),
        ("p1a", "1a\nIAM", "done"),
        ("p1b", "1b\nAgent I/O", "done"),
        ("p1", "1\nRegistry", "done"),
        ("p2", "2\nSSO", "done"),
        ("p3", "3\nProjects", "done"),
        ("p4", "4\nIPAM", "done"),
        ("p5", "5\nConsole", "done"),
        ("p6", "6\nBreakout", "done"),
        ("p7", "7\nCompliance", "planned"),
        ("p8", "8\nOTel", "planned"),
        ("p9", "9\nSSH VM", "planned"),
        ("p10", "10\nHardening", "planned"),
        ("p11", "11\nK8s inv", "planned"),
        ("p12", "12\nK8s access", "planned"),
        ("p13", "13\nPlaybooks", "planned"),
        ("p14", "14\nProxmox", "low"),
        ("p15", "15\nAWS (RO)", "low"),
        ("p16", "16\nGCP (RO)", "low"),
        ("p17", "17\nAzure (RO)", "low"),
    ]

    status_bg = {"done": C_DONE, "planned": C_SVC, "low": C_LOW}

    box_w, box_h, gap = 80, 58, 8
    x0, y0_row1, y0_row2, y0_row3 = 40, 95, 195, 295
    row1 = phases_spec[:8]
    row2 = phases_spec[8:16]
    row3 = phases_spec[16:]

    def _draw_row(
        spec: list[tuple[str, str, str]], y0: float, *, chain: bool = True
    ) -> list[str]:
        track_w = len(spec) * box_w + (len(spec) - 1) * gap + 24
        d.box(
            f"track-{y0}",
            x0 - 12,
            y0 - 12,
            track_w,
            box_h + 24,
            "",
            bg="#f8f9fa",
            stroke_style="solid",
            underlay=True,
        )
        ids: list[str] = []
        for i, (eid, lbl, status) in enumerate(spec):
            x = x0 + i * (box_w + gap)
            stroke = "dashed" if status == "low" else "solid"
            d.box(
                eid,
                x,
                y0,
                box_w,
                box_h,
                lbl,
                bg=status_bg[status],
                font_size=13,
                stroke_style=stroke,
            )
            ids.append(eid)
        if chain:
            for i in range(len(ids) - 1):
                d.arrow(
                    f"ph-{ids[i]}-{ids[i + 1]}",
                    ids[i],
                    ids[i + 1],
                    src_side="right",
                    dst_side="left",
                )
        return ids

    _draw_row(row1, y0_row1)
    _draw_row(row2, y0_row2)
    _draw_row(row3, y0_row3)
    d.label(
        "row3-lbl",
        x0,
        y0_row3 - 22,
        "Adoption track (after 0–13) — inventory read-only; no arrow from Phase 13",
        size=12,
    )

    d.label(
        "adr-note",
        40,
        y0_row3 + box_h + 28,
        "ADR-linked: 0006/1b Agent I/O · 0010→7 know-why · 0011→2 SSO · 0012→6+6.1 links/flat UI · 0013→14–17 adoption",
        size=13,
    )
    d.label("p6-defer", x0 + 6 * (box_w + gap) + 4, y0_row2 + box_h + 6, "6.1 flat L2 UI", size=11)
    return d


def diagram_air_gapped() -> Diagram:
    d = Diagram()
    d.label("title", 40, 20, "Huygens — Air-gapped deployment", size=28)
    d.box("boundary", 40, 70, 720, 420, "", bg="#fff5f5", stroke_style="dashed", underlay=True)
    d.label("b-lbl", 50, 78, "Customer network — no outbound internet", size=16)
    d.box("agents", 60, 120, 160, 80, "Agents\n(hypervisors)", bg=C_AGENT)
    d.box("cp", 260, 120, 280, 80, "Control plane\nIAM · Registry · Inventory · Projects", bg=C_SVC)
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
