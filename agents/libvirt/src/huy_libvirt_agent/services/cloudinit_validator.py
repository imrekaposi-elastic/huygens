"""Validate cloud-init user-data, meta-data, and network-config before use."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

CloudInitValidationMode = Literal["off", "basic", "schema"]

USER_DATA_HEADERS = (
    "#cloud-config",
    "#include",
    "#include-once",
    "#cloud-config-archive",
    "#cloud-boothook",
    "#part-handler",
)

SSH_KEY_PREFIXES = (
    "ssh-rsa ",
    "ssh-ed25519 ",
    "ssh-dss ",
    "ecdsa-sha2-",
    "sk-ssh-ed25519 ",
    "sk-ecdsa-sha2-",
)


class CloudInitValidationError(Exception):
    """Raised when cloud-init configuration fails validation."""

    def __init__(self, message: str, issues: list[ValidationIssue] | None = None) -> None:
        self.issues = issues or []
        super().__init__(message)


@dataclass
class ValidationIssue:
    field: str
    path: str
    message: str
    line: int | None = None
    column: int | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "field": self.field,
            "path": self.path,
            "message": self.message,
        }
        if self.line is not None:
            out["line"] = self.line
        if self.column is not None:
            out["column"] = self.column
        return out


@dataclass
class CloudInitPayload:
    user_data: str
    meta_data: str = "instance-id: local\n"
    network_config: str | None = None
    ssh_keys: list[str] = field(default_factory=list)


class CloudInitValidator:
    def __init__(self, mode: CloudInitValidationMode = "basic") -> None:
        self._mode = mode

    def validate(self, payload: CloudInitPayload) -> None:
        if self._mode == "off":
            return
        issues: list[ValidationIssue] = []
        issues.extend(self._validate_user_data(payload.user_data))
        issues.extend(self._validate_meta_data(payload.meta_data))
        if payload.network_config:
            issues.extend(self._validate_network_config(payload.network_config))
        issues.extend(self._validate_ssh_keys(payload.ssh_keys))
        if issues:
            raise CloudInitValidationError(
                "Cloud-init configuration is invalid",
                issues=issues,
            )
        if self._mode == "schema":
            self._validate_with_schema_backend(payload)

    def _validate_user_data(self, user_data: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if not user_data or not user_data.strip():
            issues.append(
                ValidationIssue(
                    "user_data",
                    "",
                    "user_data is required and cannot be empty",
                )
            )
            return issues
        if "\t" in user_data:
            issues.append(
                ValidationIssue(
                    "user_data",
                    "",
                    "YAML must use spaces for indentation, not tab characters",
                )
            )
        first_line = user_data.splitlines()[0].strip()
        if not any(first_line.startswith(h) for h in USER_DATA_HEADERS):
            issues.append(
                ValidationIssue(
                    "user_data",
                    "line 1",
                    "First line must be a cloud-init header such as '#cloud-config'",
                    line=1,
                )
            )
            return issues
        if first_line.startswith("#cloud-config"):
            body = "\n".join(user_data.splitlines()[1:])
            if not body.strip():
                issues.append(
                    ValidationIssue(
                        "user_data",
                        "",
                        "#cloud-config header present but no YAML body follows",
                        line=2,
                    )
                )
                return issues
            issues.extend(self._parse_yaml(body, "user_data", header_lines=1))
        return issues

    def _validate_meta_data(self, meta_data: str) -> list[ValidationIssue]:
        if not meta_data or not meta_data.strip():
            return [
                ValidationIssue(
                    "meta_data",
                    "",
                    "meta_data is required (e.g. 'instance-id: my-vm\\nlocal-hostname: my-vm\\n')",
                )
            ]
        issues = self._parse_yaml(meta_data, "meta_data")
        if issues:
            return issues
        try:
            parsed = yaml.safe_load(meta_data)
        except yaml.YAMLError:
            return issues
        if parsed is not None and not isinstance(parsed, dict):
            issues.append(
                ValidationIssue(
                    "meta_data",
                    "",
                    "meta_data must parse to a YAML mapping (key: value pairs)",
                )
            )
        return issues

    def _validate_network_config(self, network_config: str) -> list[ValidationIssue]:
        if not network_config.strip():
            return [
                ValidationIssue(
                    "network_config",
                    "",
                    "network_config cannot be empty when provided",
                )
            ]
        issues = self._parse_yaml(network_config, "network_config")
        if issues:
            return issues
        try:
            parsed = yaml.safe_load(network_config)
        except yaml.YAMLError:
            return issues
        if not isinstance(parsed, dict):
            issues.append(
                ValidationIssue(
                    "network_config",
                    "",
                    "network-config must be a YAML mapping",
                )
            )
            return issues
        version = parsed.get("version")
        if version not in (1, 2, "1", "2"):
            issues.append(
                ValidationIssue(
                    "network_config",
                    "version",
                    "network-config must set 'version: 1' or 'version: 2'",
                )
            )
            return issues
        ver = int(version) if isinstance(version, str) else version
        if ver == 1:
            if "config" not in parsed:
                issues.append(
                    ValidationIssue(
                        "network_config",
                        "config",
                        "network-config v1 requires a top-level 'config' list",
                    )
                )
        elif ver == 2:
            stanzas = ("ethernets", "bonds", "bridges", "vlans", "wifis", "dummy-devices")
            if not any(k in parsed for k in stanzas):
                issues.append(
                    ValidationIssue(
                        "network_config",
                        "",
                        "network-config v2 needs at least one stanza "
                        "(ethernets, bonds, bridges, vlans, wifis, or dummy-devices)",
                    )
                )
        return issues

    def _validate_ssh_keys(self, ssh_keys: list[str]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for i, key in enumerate(ssh_keys):
            key = key.strip()
            if not key:
                issues.append(
                    ValidationIssue(
                        "ssh_keys",
                        str(i),
                        "SSH public key cannot be empty",
                    )
                )
                continue
            if not any(key.startswith(p) for p in SSH_KEY_PREFIXES):
                issues.append(
                    ValidationIssue(
                        "ssh_keys",
                        str(i),
                        "SSH key should start with a recognized type "
                        "(ssh-rsa, ssh-ed25519, ecdsa-sha2-*, sk-ssh-ed25519, ...)",
                    )
                )
            parts = key.split()
            if len(parts) < 2:
                issues.append(
                    ValidationIssue(
                        "ssh_keys",
                        str(i),
                        "SSH key must contain algorithm and base64 key material",
                    )
                )
        return issues

    def _parse_yaml(
        self, text: str, field: str, *, header_lines: int = 0
    ) -> list[ValidationIssue]:
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            line = column = None
            mark = getattr(exc, "problem_mark", None) or getattr(exc, "context_mark", None)
            if mark is not None:
                line = int(mark.line) + 1 + header_lines
                column = int(mark.column) + 1
            return [
                ValidationIssue(
                    field,
                    f"line {line}" if line else "yaml",
                    f"Invalid YAML: {exc}",
                    line=line,
                    column=column,
                )
            ]
        if parsed is None:
            return [
                ValidationIssue(
                    field,
                    "",
                    "YAML document is empty",
                )
            ]
        if field == "user_data" and not isinstance(parsed, (dict, list)):
            return [
                ValidationIssue(
                    field,
                    "",
                    "#cloud-config body must be a YAML mapping or list (merge syntax)",
                )
            ]
        return []

    def _validate_with_schema_backend(self, payload: CloudInitPayload) -> None:
        if self._try_python_schema(payload):
            return
        if self._try_cli_schema(payload):
            return
        raise CloudInitValidationError(
            "schema validation requested but cloud-init is not installed on this host "
            "(install cloud-init package or set HUY_CLOUD_INIT_VALIDATION=basic)",
            issues=[
                ValidationIssue(
                    "user_data",
                    "",
                    "Install cloud-init on the hypervisor for full schema validation, "
                    "or use HUY_CLOUD_INIT_VALIDATION=basic",
                )
            ],
        )

    def _try_python_schema(self, payload: CloudInitPayload) -> bool:
        try:
            from cloudinit.config.schema import (  # type: ignore[import-untyped]
                SchemaType,
                SchemaValidationError,
                validate_cloudconfig_schema,
            )
        except ImportError:
            return False

        issues: list[ValidationIssue] = []
        body = self._cloud_config_body(payload.user_data)
        if body is not None:
            try:
                config = yaml.safe_load(body)
                validate_cloudconfig_schema(
                    config,
                    schema_type=SchemaType.CLOUD_CONFIG,
                    strict=True,
                    log_details=False,
                )
            except SchemaValidationError as exc:
                for problem in exc.schema_errors or []:
                    issues.append(
                        ValidationIssue("user_data", problem.path, problem.message)
                    )
            except (yaml.YAMLError, RuntimeError, ValueError) as exc:
                issues.append(ValidationIssue("user_data", "", str(exc)))

        if payload.network_config:
            try:
                net = yaml.safe_load(payload.network_config)
                validate_cloudconfig_schema(
                    net,
                    schema_type=SchemaType.NETWORK_CONFIG,
                    strict=True,
                    log_details=False,
                )
            except SchemaValidationError as exc:
                for problem in exc.schema_errors or []:
                    issues.append(
                        ValidationIssue(
                            "network_config", problem.path, problem.message
                        )
                    )
            except (yaml.YAMLError, RuntimeError, ValueError) as exc:
                issues.append(ValidationIssue("network_config", "", str(exc)))

        if issues:
            raise CloudInitValidationError(
                "Cloud-init schema validation failed", issues=issues
            )
        return True

    def _try_cli_schema(self, payload: CloudInitPayload) -> bool:
        if not shutil.which("cloud-init"):
            return False
        issues: list[ValidationIssue] = []
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            user_path = tmp_path / "user-data"
            user_path.write_text(payload.user_data)
            issues.extend(
                self._run_cloud_init_schema_cli(user_path, "user_data", "cloud-config")
            )
            if payload.network_config:
                net_path = tmp_path / "network-config"
                net_path.write_text(payload.network_config)
                issues.extend(
                    self._run_cloud_init_schema_cli(
                        net_path, "network_config", "network-config"
                    )
                )
        if issues:
            raise CloudInitValidationError(
                "Cloud-init schema validation failed", issues=issues
            )
        return True

    def _run_cloud_init_schema_cli(
        self, config_path: Path, field: str, schema_type: str
    ) -> list[ValidationIssue]:
        proc = subprocess.run(
            [
                "cloud-init",
                "schema",
                "--config-file",
                str(config_path),
                "--schema-type",
                schema_type,
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return []
        output = (proc.stderr or proc.stdout or "").strip()
        parsed = self._parse_cli_schema_output(output)
        if parsed:
            return [ValidationIssue(field, path, msg) for path, msg in parsed]
        return [
            ValidationIssue(
                field,
                "",
                output or "cloud-init schema reported validation errors",
            )
        ]

    @staticmethod
    def _parse_cli_schema_output(output: str) -> list[tuple[str, str]]:
        problems: list[tuple[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            match = re.match(r"^([\w.-]+):\s*(.+)$", line)
            if match:
                problems.append((match.group(1), match.group(2)))
        return problems

    @staticmethod
    def _cloud_config_body(user_data: str) -> str | None:
        lines = user_data.splitlines()
        if not lines or not lines[0].strip().startswith("#cloud-config"):
            return None
        return "\n".join(lines[1:])
