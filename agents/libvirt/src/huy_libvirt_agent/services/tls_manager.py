"""Auto-generated TLS CA and server certificate for HTTPS API."""

from __future__ import annotations

import datetime
import ipaddress
import os
import shutil
import socket
from dataclasses import dataclass
from pathlib import Path

import structlog
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

logger = structlog.get_logger(__name__)

CA_DAYS = 3650
SERVER_DAYS = 825


@dataclass(frozen=True)
class TlsMaterial:
    cert_dir: Path
    ca_cert: Path
    ca_key: Path
    server_cert: Path
    server_key: Path


def _write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(path, 0o600)


def _write_cert(path: Path, cert: x509.Certificate) -> None:
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(path, 0o644)


def _collect_sans(hostname: str) -> list[x509.GeneralName]:
    names: list[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.DNSName(hostname),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    fqdn = socket.getfqdn()
    if fqdn and fqdn != hostname:
        names.append(x509.DNSName(fqdn))
    if "." in hostname:
        short = hostname.split(".", 1)[0]
        names.append(x509.DNSName(short))

    seen: set[str] = set()
    for host in {hostname, fqdn, "localhost"}:
        if not host:
            continue
        try:
            for info in socket.getaddrinfo(host, None):
                ip = info[4][0]
                if ip in seen:
                    continue
                seen.add(ip)
                try:
                    names.append(x509.IPAddress(ipaddress.ip_address(ip)))
                except ValueError:
                    continue
        except socket.gaierror:
            continue
    return names


def ca_fingerprint(ca_cert_path: Path) -> str:
    cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())
    digest = cert.fingerprint(hashes.SHA256())
    return ":".join(f"{b:02x}" for b in digest)


def _generate_ca(ca_cert: Path, ca_key: Path, common_name: str) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    _write_private_key(ca_key, key)
    _write_cert(ca_cert, cert)


def _generate_server_cert(
    ca_cert: Path,
    ca_key: Path,
    server_cert: Path,
    server_key: Path,
    hostname: str,
) -> None:
    ca = x509.load_pem_x509_certificate(ca_cert.read_bytes())
    ca_priv = serialization.load_pem_private_key(ca_key.read_bytes(), password=None)
    if not isinstance(ca_priv, rsa.RSAPrivateKey):
        raise TypeError("CA key must be RSA")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Huy Libvirt Agent"),
        ]
    )
    now = datetime.datetime.now(datetime.UTC)
    san = x509.SubjectAlternativeName(_collect_sans(hostname))
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=SERVER_DAYS))
        .add_extension(san, critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_priv, hashes.SHA256())
    )
    _write_private_key(server_key, key)
    _write_cert(server_cert, cert)


def ensure_tls_material(
    cert_dir: Path,
    hostname: str,
    *,
    auto_generate: bool = True,
    regenerate: bool = False,
) -> TlsMaterial:
    cert_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(cert_dir, 0o700)
    paths = TlsMaterial(
        cert_dir=cert_dir,
        ca_cert=cert_dir / "ca.pem",
        ca_key=cert_dir / "ca-key.pem",
        server_cert=cert_dir / "server.crt",
        server_key=cert_dir / "server.key",
    )
    if regenerate and paths.ca_cert.exists():
        shutil.rmtree(cert_dir)
        cert_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(cert_dir, 0o700)

    have_all = all(
        p.exists() for p in (paths.ca_cert, paths.ca_key, paths.server_cert, paths.server_key)
    )
    if not have_all:
        if not auto_generate:
            raise FileNotFoundError(f"TLS material missing under {cert_dir}")
        cn = f"Huy Libvirt Agent CA ({hostname})"
        _generate_ca(paths.ca_cert, paths.ca_key, cn)
        _generate_server_cert(
            paths.ca_cert,
            paths.ca_key,
            paths.server_cert,
            paths.server_key,
            hostname,
        )
        logger.info(
            "tls_material_generated",
            cert_dir=str(cert_dir),
            ca_fingerprint=ca_fingerprint(paths.ca_cert),
        )
    return paths
