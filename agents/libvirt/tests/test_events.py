"""Domain event bus tests."""

from pathlib import Path

from huy_libvirt_agent.events.bus import EventBus, FileEventPublisher


def test_file_publisher(tmp_path: Path) -> None:
    bus = EventBus([FileEventPublisher(tmp_path / "events")])
    bus.publish("huy.test.event", "/test", {"foo": "bar"}, correlation_id="cid-1")
    files = list((tmp_path / "events").glob("*.jsonl"))
    assert files
    content = files[0].read_text()
    assert "huy.test.event" in content
    assert "cid-1" in content
