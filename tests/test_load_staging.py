import pytest

from src.load.load_staging import check_header, to_snake_case


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("ACCIDENT_NO", "accident_no"),
        ("LGA NAME ALL", "lga_name_all"),
        ("VEHICLE 1 COLL PT DESC", "vehicle_1_coll_pt_desc"),
        (" NODE_ID ", "node_id"),
    ],
)
def test_to_snake_case(header, expected):
    assert to_snake_case(header) == expected


def test_check_header_accepts_matching_columns():
    check_header(["a", "b"], ["a", "b"], "example")


def test_check_header_reports_new_and_missing_columns():
    with pytest.raises(ValueError, match=r"new columns \['c'\], missing columns \['b'\]"):
        check_header(["a", "c"], ["a", "b"], "example")


def test_check_header_detects_reordered_columns():
    with pytest.raises(ValueError, match="column order changed"):
        check_header(["b", "a"], ["a", "b"], "example")
