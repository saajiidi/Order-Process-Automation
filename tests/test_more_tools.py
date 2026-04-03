import pandas as pd

from app_modules.more_tools import _evaluate_data_quality, _is_valid_phone


def test_phone_validation_variants():
    assert _is_valid_phone("01712345678")
    assert _is_valid_phone("+8801712345678")
    assert not _is_valid_phone("1712345678")
    assert not _is_valid_phone("abcd")


def test_evaluate_data_quality_counts_issues():
    df = pd.DataFrame(
        {
            "Product Name": ["A", None, "C", "D"],
            "Item Cost": [100, 0, 120000, "x"],
            "Quantity": [1, -2, 150, None],
            "Order ID": ["O1", "O1", "O3", "O4"],
            "Phone": ["01712345678", "111", "+8801712345678", "01812345678"],
        }
    )

    auto_cols, missing_required, issues_df, quality_score = _evaluate_data_quality(df)

    assert "name" in auto_cols and "cost" in auto_cols and "qty" in auto_cols
    assert missing_required == []
    assert 0 <= quality_score <= 100

    issue_map = {row["Issue"]: int(row["Count"]) for _, row in issues_df.iterrows()}
    assert issue_map["Missing Product Name"] == 1
    assert issue_map["Duplicate Order IDs"] == 1
    assert issue_map["Suspicious Price"] >= 2
    assert issue_map["Suspicious Quantity"] >= 2
    assert issue_map["Invalid Phone Format"] == 1


def test_evaluate_data_quality_detects_missing_required_columns():
    df = pd.DataFrame({"Only Col": [1, 2, 3]})
    _, missing_required, issues_df, score = _evaluate_data_quality(df)

    assert set(missing_required) == {"name", "cost", "qty"}
    assert list(issues_df["Issue"]) == [
        "Duplicate Order IDs",
        "Suspicious Price",
        "Suspicious Quantity",
        "Invalid Phone Format",
    ]
    assert 0 <= score <= 100
