"""RBAC re-export surface."""

from huy_iam import rbac


def test_rbac_exports() -> None:
    assert rbac.AuthContext is not None
    assert "admin" in rbac.ROLE_PERMISSIONS
    assert rbac.PERM_INVENTORY_READ == "inventory:read"
