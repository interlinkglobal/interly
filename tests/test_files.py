import json
from pathlib import Path

from computer_agent.files import (
    compare_files,
    create_text_file,
    edit_text_file,
    manage_path,
    read_text_file,
    search_files,
)


def test_search_and_read_text_file(tmp_path: Path) -> None:
    target = tmp_path / "hello.js"
    target.write_text("const greeting = 'hello';", encoding="utf-8")

    found = search_files(str(tmp_path), "hello", "js", "greeting")
    read = read_text_file(str(target))

    assert json.loads(found)[0]["path"] == str(target)
    assert "const greeting" in read


def test_create_and_edit_never_blindly_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "note.txt"

    assert "Created" in create_text_file(str(target), "before")
    assert "nothing was overwritten" in create_text_file(str(target), "wrong")
    assert "Updated" in edit_text_file(str(target), "before", "after")
    assert target.read_text(encoding="utf-8") == "after"


def test_copy_move_mkdir_and_compare(tmp_path: Path) -> None:
    source = tmp_path / "one.txt"
    source.write_text("one", encoding="utf-8")
    copy = tmp_path / "two.txt"
    moved = tmp_path / "three.txt"
    folder = tmp_path / "folder"

    assert "Copied" in manage_path("copy", str(source), str(copy))
    assert "Moved" in manage_path("move", str(copy), str(moved))
    assert "Created directory" in manage_path("mkdir", "", str(folder))
    assert moved.exists()
    assert folder.is_dir()


def test_compare_files_reports_difference(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("old", encoding="utf-8")
    right.write_text("new", encoding="utf-8")

    result = compare_files(str(left), str(right))

    assert "-old" in result
    assert "+new" in result
