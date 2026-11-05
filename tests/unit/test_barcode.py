import pytest

from ingredient_drift.barcode import BarcodeStatus, normalise_barcode

S = BarcodeStatus


@pytest.mark.parametrize(
    "raw, expected, status",
    [
        ("071109", "00071109", S.ADJUSTED),            # real case: L10
        ("00071109", "00071109", S.OK),                # already canonical
        ("3174332018297", "3174332018297", S.OK),      # real case, EAN-13
        ("036000291452", "0036000291452", S.ADJUSTED), # UPC-A, 12 digits
        (" 3174332018297 ", "3174332018297", S.OK),    # whitespace
    ],
)
def test_recognised_codes(raw, expected, status):
    result = normalise_barcode(raw)
    assert result.normalised_code == expected
    assert result.status == status
    assert result.raw_code == raw  # raw always preserved


@pytest.mark.parametrize("raw", [None, "", "   ", "12a45", "0000", 3174332018297, "²³"])
def test_invalid_input_never_raises(raw):
    result = normalise_barcode(raw)
    assert result.status == S.INVALID_INPUT
    assert result.normalised_code is None


def test_unrecognised_length_is_passed_through():
    result = normalise_barcode("12345678901234")  # 14 digits
    assert result.status == S.UNRECOGNISED_LENGTH
    assert result.normalised_code == "12345678901234"
    assert result.check_digit_valid is None


def test_bad_check_digit_is_flagged_not_rejected():
    result = normalise_barcode("3174332018298")
    assert result.status == S.OK
    assert result.check_digit_valid is False


def test_valid_check_digits():
    assert normalise_barcode("3174332018297").check_digit_valid is True
    assert normalise_barcode("071109").check_digit_valid is True


@pytest.mark.parametrize("raw", ["071109", "036000291452", "3174332018297"])
def test_idempotent(raw):
    once = normalise_barcode(raw).normalised_code
    assert normalise_barcode(once).normalised_code == once


def test_many_leading_zeros_collapse_current_rule():
    # Documents behaviour of the CURRENT unverified rule. Revisit after
    # checking OFF's source; this is a key-collision risk.
    assert normalise_barcode("0000000071109").normalised_code == "00071109"