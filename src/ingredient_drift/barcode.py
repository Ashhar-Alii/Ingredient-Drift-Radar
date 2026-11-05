from dataclasses import dataclass
from enum import Enum


class BarcodeStatus(str, Enum):
    OK = "ok"
    ADJUSTED = "adjusted"
    UNRECOGNISED_LENGTH = "unrecognised_length"
    INVALID_INPUT = "invalid_input"


# (min_len, max_len, target_width), applied AFTER stripping leading zeros.
# Unverified against OFF's product-opener source. Change here if it differs.
PAD_RULES = ((1, 7, 8), (9, 12, 13))
KEEP_LENGTHS = frozenset({8, 13})


@dataclass(frozen=True)
class BarcodeResult:
    raw_code: object
    normalised_code: str | None
    status: BarcodeStatus
    check_digit_valid: bool | None


def has_valid_check_digit(code: str) -> bool:
    """GS1 check digit, valid for EAN-8 and EAN-13 (also UPC-A once padded to 13)."""
    body, check = code[:-1], int(code[-1])
    total = sum(
        int(d) * (3 if i % 2 == 0 else 1)
        for i, d in enumerate(reversed(body))
    )
    return (10 - total % 10) % 10 == check


def normalise_barcode(raw: object) -> BarcodeResult:
    if not isinstance(raw, str):
        return BarcodeResult(raw, None, BarcodeStatus.INVALID_INPUT, None)

    text = raw.strip()
    if not text or not text.isascii() or not text.isdigit():
        return BarcodeResult(raw, None, BarcodeStatus.INVALID_INPUT, None)

    core = text.lstrip("0")
    if not core:  # all zeros
        return BarcodeResult(raw, None, BarcodeStatus.INVALID_INPUT, None)

    n = len(core)
    target = n if n in KEEP_LENGTHS else None
    for lo, hi, width in PAD_RULES:
        if lo <= n <= hi:
            target = width

    if target is None:
        return BarcodeResult(raw, text, BarcodeStatus.UNRECOGNISED_LENGTH, None)

    code = core.zfill(target)
    status = BarcodeStatus.OK if code == text else BarcodeStatus.ADJUSTED
    return BarcodeResult(raw, code, status, has_valid_check_digit(code))