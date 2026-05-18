"""DNAT rule persistence and iptables reconciliation."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from huy_libvirt_agent.api.schemas.agent import AgentLabels
from huy_libvirt_agent.api.schemas.network import DnatRuleCreate, DnatRuleResponse
from huy_libvirt_agent.services.breakout_service import BreakoutService


class DnatService:
    def __init__(self, vnets_dir: Path, breakout: BreakoutService, labels: dict[str, str]) -> None:
        self._vnets_dir = vnets_dir
        self._breakout = breakout
        self._labels = labels

    def _dnat_path(self, vnet: str) -> Path:
        p = self._vnets_dir / vnet
        p.mkdir(parents=True, exist_ok=True)
        return p / "dnat.json"

    def _load(self, vnet: str) -> list[dict]:
        path = self._dnat_path(vnet)
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def _save(self, vnet: str, rules: list[dict]) -> None:
        self._dnat_path(vnet).write_text(json.dumps(rules, indent=2))

    def list_rules(self, vnet: str) -> list[DnatRuleResponse]:
        return [self._to_response(r) for r in self._load(vnet)]

    def add_rule(self, vnet: str, body: DnatRuleCreate, vnet_cidr: str) -> DnatRuleResponse:
        rules = self._load(vnet)
        rule = {
            "rule_id": str(uuid.uuid4()),
            "labels": self._labels,
            **body.model_dump(),
        }
        rules.append(rule)
        self._save(vnet, rules)
        breakout = self._breakout.get_breakout(vnet)
        self._breakout._reconcile_iptables(vnet, vnet_cidr, breakout)
        return self._to_response(rule)

    def delete_rule(self, vnet: str, rule_id: str, vnet_cidr: str) -> None:
        rules = [r for r in self._load(vnet) if r.get("rule_id") != rule_id]
        self._save(vnet, rules)
        breakout = self._breakout.get_breakout(vnet)
        self._breakout._reconcile_iptables(vnet, vnet_cidr, breakout)

    def _to_response(self, rule: dict) -> DnatRuleResponse:
        labels = rule.get("labels", self._labels)
        return DnatRuleResponse(
            rule_id=rule["rule_id"],
            labels=AgentLabels(**labels),
            public_host=rule["public_host"],
            public_port=rule["public_port"],
            protocol=rule["protocol"],
            guest_ip=rule["guest_ip"],
            guest_port=rule["guest_port"],
            comment=rule.get("comment"),
        )
