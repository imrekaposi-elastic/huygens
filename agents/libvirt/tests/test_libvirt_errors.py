"""Libvirt native error translation tests."""

from __future__ import annotations

import pytest

from huy_libvirt_agent.services.libvirt_client import LibvirtError
from huy_libvirt_agent.services.libvirt_errors import translate_libvirt_exception

pytest.importorskip("libvirt")
import libvirt


def _make_libvirt_error(code: int, message: str) -> libvirt.libvirtError:
    exc = libvirt.libvirtError(message)
    exc.err = [code, 0, message, 0, 0, 0, 0, 0]
    return exc


def test_domain_not_found_maps_to_404_code() -> None:
    exc = _make_libvirt_error(libvirt.VIR_ERR_NO_DOMAIN, "Domain not found: missing")
    err = translate_libvirt_exception(exc)
    assert err.code == "DOMAIN_NOT_FOUND"
    assert "not found" in str(err).lower()


def test_network_not_found_maps_to_network_not_found() -> None:
    exc = _make_libvirt_error(libvirt.VIR_ERR_NO_NETWORK, "Network not found: missing")
    err = translate_libvirt_exception(exc)
    assert err.code == "NETWORK_NOT_FOUND"


def test_domain_exists_maps_to_domain_exists() -> None:
    exc = _make_libvirt_error(libvirt.VIR_ERR_DOM_EXIST, "Domain exists")
    err = translate_libvirt_exception(exc)
    assert err.code == "DOMAIN_EXISTS"


def test_xml_error_maps_to_xml_error() -> None:
    exc = _make_libvirt_error(libvirt.VIR_ERR_XML_ERROR, "XML error")
    err = translate_libvirt_exception(exc)
    assert err.code == "XML_ERROR"


def test_libvirt_error_passthrough() -> None:
    original = LibvirtError("agent", "NOT_FOUND")
    assert translate_libvirt_exception(original) is original
