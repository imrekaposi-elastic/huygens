"""Region tree helpers."""

from huy_compliance.services.region_tree import ancestor_region_ids, parent_map_from_regions


def test_ancestor_region_ids_walks_parents() -> None:
    parent_by_id = {
        "fs6": "falkenstein",
        "falkenstein": "hetzner-root",
        "hetzner-root": None,
    }
    assert ancestor_region_ids("fs6", parent_by_id) == [
        "fs6",
        "falkenstein",
        "hetzner-root",
    ]


def test_parent_map_from_regions() -> None:
    regions = [
        {"id": "a", "parent_region_id": None},
        {"id": "b", "parent_region_id": "a"},
    ]
    assert parent_map_from_regions(regions) == {"a": None, "b": "a"}
