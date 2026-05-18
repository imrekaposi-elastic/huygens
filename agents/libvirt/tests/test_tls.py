"""TLS material generation tests."""

from pathlib import Path

from huy_libvirt_agent.services.tls_manager import ca_fingerprint, ensure_tls_material


def test_ensure_tls_material_generates_files(tmp_path: Path) -> None:
    material = ensure_tls_material(tmp_path / "tls", "test-host.example", auto_generate=True)
    assert material.ca_cert.is_file()
    assert material.server_cert.is_file()
    assert material.server_key.is_file()
    fp1 = ca_fingerprint(material.ca_cert)
    assert len(fp1.split(":")) == 32

    # Idempotent: second call does not regenerate
    material2 = ensure_tls_material(tmp_path / "tls", "test-host.example", auto_generate=True)
    assert ca_fingerprint(material2.ca_cert) == fp1


def test_regenerate_replaces_material(tmp_path: Path) -> None:
    cert_dir = tmp_path / "tls"
    ensure_tls_material(cert_dir, "host-a", auto_generate=True)
    fp_a = ca_fingerprint(cert_dir / "ca.pem")
    ensure_tls_material(cert_dir, "host-b", auto_generate=True, regenerate=True)
    fp_b = ca_fingerprint(cert_dir / "ca.pem")
    assert fp_a != fp_b
