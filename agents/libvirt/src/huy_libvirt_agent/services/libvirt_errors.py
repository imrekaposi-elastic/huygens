"""Map libvirt-python exceptions to agent LibvirtError codes."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

try:
    import libvirt

    LIBVIRT_AVAILABLE = True
except ImportError:
    libvirt = None  # type: ignore
    LIBVIRT_AVAILABLE = False

T = TypeVar("T")


class LibvirtError(Exception):
    def __init__(self, message: str, code: str = "LIBVIRT_ERROR") -> None:
        self.code = code
        super().__init__(message)


def translate_libvirt_exception(exc: BaseException) -> LibvirtError:
    """Convert libvirt.libvirtError (and others) into LibvirtError with a stable code."""
    if isinstance(exc, LibvirtError):
        return exc
    if LIBVIRT_AVAILABLE and isinstance(exc, libvirt.libvirtError):
        return _from_libvirt_error(exc)
    return LibvirtError(str(exc), "LIBVIRT_FAILED")


def _from_libvirt_error(exc: Any) -> LibvirtError:
    err_code = exc.get_error_code()
    message = (exc.get_error_message() or str(exc)).strip()
    code = _map_error_code(err_code)
    if err_code == getattr(libvirt, "VIR_ERR_NO_DOMAIN", 42):
        code = "DOMAIN_NOT_FOUND"
    elif err_code == getattr(libvirt, "VIR_ERR_NO_NETWORK", 49):
        code = "NETWORK_NOT_FOUND"
    elif err_code == getattr(libvirt, "VIR_ERR_DOM_EXIST", 39):
        code = "DOMAIN_EXISTS"
    elif err_code == getattr(libvirt, "VIR_ERR_NETWORK_EXIST", 57):
        code = "NETWORK_EXISTS"
    elif err_code == getattr(libvirt, "VIR_ERR_XML_ERROR", 17):
        code = "XML_ERROR"
    elif err_code == getattr(libvirt, "VIR_ERR_OPERATION_INVALID", 55):
        code = "OPERATION_INVALID"
    elif err_code == getattr(libvirt, "VIR_ERR_AUTH_FAILED", 7):
        code = "AUTH_FAILED"
    elif err_code == getattr(libvirt, "VIR_ERR_NO_STORAGE_POOL", 50):
        code = "NOT_FOUND"
    return LibvirtError(message, code)


def _map_error_code(err_code: int) -> str:
    if not LIBVIRT_AVAILABLE:
        return "LIBVIRT_FAILED"
    system_error = getattr(libvirt, "VIR_ERR_SYSTEM_ERROR", 1)
    internal_error = getattr(libvirt, "VIR_ERR_INTERNAL_ERROR", 2)
    if err_code in (system_error, internal_error):
        return "LIBVIRT_SYSTEM_ERROR"
    return "LIBVIRT_FAILED"


def libvirt_wrapped(method: Callable[..., T]) -> Callable[..., T]:
    """Decorator for LibvirtClient methods: translate libvirt.libvirtError."""

    @wraps(method)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return method(*args, **kwargs)
        except LibvirtError:
            raise
        except Exception as exc:
            raise translate_libvirt_exception(exc) from exc

    return wrapper
