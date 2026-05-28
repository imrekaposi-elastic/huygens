"""Export PDF display-name helpers."""

from huy_compliance.services.export_service import format_user_display_name


def test_format_user_display_name_username_and_email() -> None:
    assert (
        format_user_display_name(username="alice", email="alice@example.com", user_id="uuid-1")
        == "alice (alice@example.com)"
    )


def test_format_user_display_name_username_only() -> None:
    assert format_user_display_name(username="bob", email="", user_id="uuid-2") == "bob"


def test_format_user_display_name_falls_back_to_user_id() -> None:
    assert format_user_display_name(username="", email="", user_id="uuid-3") == "uuid-3"
