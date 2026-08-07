from pathlib import Path

import pytest

from computer_agent.config import memory_file
from computer_agent.memory import MemoryStore


def test_memory_store_persists_entries_and_allows_deletion(tmp_path: Path) -> None:
    path = tmp_path / "memory.json"
    store = MemoryStore(path)

    store.add_entry("user_name", "Ada", kind="fact", approved=True)
    store.add_entry("theme", "dark", kind="preference", approved=True)

    reloaded = MemoryStore(path)
    entries = reloaded.list_entries()

    assert len(entries) == 2
    assert entries[0]["key"] == "user_name"
    assert entries[0]["value"] == "Ada"
    assert entries[1]["kind"] == "preference"

    reloaded.delete_entry("theme")
    assert reloaded.list_entries() == [
        {"key": "user_name", "value": "Ada", "kind": "fact", "approved": True}
    ]


def test_memory_store_rejects_unapproved_entries(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.json")

    with pytest.raises(ValueError, match="approved"):
        store.add_entry("secret", "value", approved=False)

    assert store.list_entries() == []


def test_memory_file_uses_user_config_directory(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("INTERLY_CONFIG_DIR", str(tmp_path))

    assert memory_file() == tmp_path / "memory.json"
