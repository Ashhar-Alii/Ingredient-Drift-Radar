import hashlib

import pytest

from ingredient_drift import raw_store
from ingredient_drift.raw_store import (
    read_revision, revision_exists, revision_path, write_revision,
)


def test_path_layout(tmp_path):
    assert revision_path(tmp_path, "00071109", 12) == tmp_path / "00071109" / "rev_000012.json.gz"


def test_lexicographic_order_is_numeric_order(tmp_path):
    revs = [1, 2, 9, 10, 99, 100, 9999, 10000, 123456]
    names = [revision_path(tmp_path, "00071109", r).name for r in revs]
    assert names == sorted(names)


def test_roundtrip_and_checksum(tmp_path):
    body = b'{"code":"00071109"}'
    stored = write_revision(tmp_path, "00071109", 3, body)
    assert read_revision(stored.path) == body
    assert stored.sha256 == hashlib.sha256(body).hexdigest()
    assert stored.size_bytes == len(body)
    assert revision_exists(tmp_path, "00071109", 3)


def test_refuses_overwrite(tmp_path):
    write_revision(tmp_path, "00071109", 3, b"a")
    with pytest.raises(FileExistsError):
        write_revision(tmp_path, "00071109", 3, b"b")
    assert read_revision(revision_path(tmp_path, "00071109", 3)) == b"a"


def test_no_temp_files_after_success(tmp_path):
    write_revision(tmp_path, "00071109", 3, b"a")
    assert not list(tmp_path.rglob("*.tmp"))


def test_failed_write_leaves_nothing(tmp_path, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(raw_store.os, "replace", boom)
    with pytest.raises(OSError):
        write_revision(tmp_path, "00071109", 3, b"a")
    assert not revision_exists(tmp_path, "00071109", 3)
    assert not list(tmp_path.rglob("*.tmp"))


def test_same_body_gives_identical_bytes(tmp_path):
    a = write_revision(tmp_path / "a", "00071109", 3, b"same body")
    b = write_revision(tmp_path / "b", "00071109", 3, b"same body")
    assert a.path.read_bytes() == b.path.read_bytes()


@pytest.mark.parametrize("code", ["", "../x", "12a", "²³"])
def test_rejects_bad_code(tmp_path, code):
    with pytest.raises(ValueError):
        revision_path(tmp_path, code, 1)


def test_rejects_bad_revision(tmp_path):
    with pytest.raises(ValueError):
        revision_path(tmp_path, "00071109", 0)