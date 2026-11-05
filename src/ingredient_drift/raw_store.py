import gzip
import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredFile:
    path: Path
    sha256: str      # of the uncompressed body, exactly as received
    size_bytes: int  # uncompressed size


def revision_path(root: Path, normalised_code: str, revision: int) -> Path:
    if not (normalised_code.isascii() and normalised_code.isdigit()):
        raise ValueError(f"bad normalised code: {normalised_code!r}")
    if revision < 1:
        raise ValueError("revision must be >= 1")
    return root / normalised_code / f"rev_{revision:06d}.json.gz"


def revision_exists(root: Path, normalised_code: str, revision: int) -> bool:
    return revision_path(root, normalised_code, revision).exists()


def write_revision(root: Path, normalised_code: str, revision: int, body: bytes) -> StoredFile:
    final = revision_path(root, normalised_code, revision)
    if final.exists():
        raise FileExistsError(final)  # raw layer is immutable
    final.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=final.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
                gz.write(body)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, final)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return StoredFile(final, hashlib.sha256(body).hexdigest(), len(body))


def read_revision(path: Path) -> bytes:
    with gzip.open(path, "rb") as f:
        return f.read()