"""Unit tests for task selector parsing (T053/T054, FR-014b)."""

import pytest

from ai_factory.shared.folder_adapter.selector import (
    SelectorError,
    parse_selector,
    resolve_selector,
)

IDS = ["T001", "T002", "T003", "T004", "T005", "T006", "T007"]


def test_single() -> None:
    sel = resolve_selector("T3", IDS)
    assert sel.includes("T003")
    assert not sel.includes("T004")


def test_list() -> None:
    sel = resolve_selector("T3,T5", IDS)
    assert sel.includes("T003") and sel.includes("T005")
    assert not sel.includes("T004")


def test_range() -> None:
    sel = resolve_selector("T3-T5", IDS)
    assert sel.includes("T003") and sel.includes("T004") and sel.includes("T005")


def test_open_range() -> None:
    sel = resolve_selector("T5-", IDS)
    assert sel.includes("T005") and sel.includes("T007")
    assert not sel.includes("T004")


def test_all() -> None:
    sel = parse_selector("*")
    assert sel.all
    sel2 = parse_selector("all")
    assert sel2.all


def test_unknown_task_raises() -> None:
    with pytest.raises(SelectorError):
        resolve_selector("T999", IDS)


def test_malformed_raises() -> None:
    with pytest.raises(SelectorError):
        parse_selector("hello")
