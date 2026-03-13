"""
Tests for VTU Dashboard core modules.
Run with:  python -m pytest tests/ -v
"""

import sys
import os
import time
import json
import pytest
import pandas as pd
import numpy as np

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ================================================================
# Test: security.py
# ================================================================
class TestSanitizeText:
    def test_removes_html_tags(self):
        from security import sanitize_text
        assert sanitize_text("<b>hello</b>") == "hello"
        assert sanitize_text('<script>alert("x")</script>') == 'alert("x")'

    def test_limits_length(self):
        from security import sanitize_text
        long_text = "a" * 600
        assert len(sanitize_text(long_text)) == 500

    def test_none_input(self):
        from security import sanitize_text
        assert sanitize_text(None) == ""
        assert sanitize_text("") == ""


class TestValidateEmail:
    def test_valid_emails(self):
        from security import validate_email
        assert validate_email("user@example.com") is True
        assert validate_email("test.user+tag@domain.co.in") is True

    def test_invalid_emails(self):
        from security import validate_email
        assert validate_email("not-an-email") is False
        assert validate_email("@no-user.com") is False
        assert validate_email("user@") is False

    def test_optional_empty(self):
        from security import validate_email
        assert validate_email("") is True
        assert validate_email(None) is True


class TestRateLimiter:
    def test_allows_within_limit(self):
        from security import RateLimiter
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.is_allowed("test_key") is True
        assert limiter.is_allowed("test_key") is True
        assert limiter.is_allowed("test_key") is True

    def test_blocks_over_limit(self):
        from security import RateLimiter
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("k") is True
        assert limiter.is_allowed("k") is True
        assert limiter.is_allowed("k") is False

    def test_different_keys_independent(self):
        from security import RateLimiter
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        assert limiter.is_allowed("a") is True
        assert limiter.is_allowed("b") is True
        assert limiter.is_allowed("a") is False


# ================================================================
# Test: services/credit_service.py
# ================================================================
class TestCreditService:
    def test_load_2022_scheme(self):
        from services.credit_service import load_credit_map
        data = load_credit_map("2022", 1)
        assert isinstance(data, dict)
        # Should have at least some credit entries
        assert len(data) > 0

    def test_load_nonexistent_returns_empty(self):
        from services.credit_service import load_credit_map
        data = load_credit_map("9999", 99)
        assert data == {}

    def test_load_2025_with_cycle(self):
        from services.credit_service import load_credit_map
        data = load_credit_map("2025", 1, cycle="physics")
        assert isinstance(data, dict)

    def test_get_credit(self):
        from services.credit_service import load_credit_map, get_credit
        credit_map = load_credit_map("2022", 1)
        if credit_map:
            first_code = next(iter(credit_map))
            c = get_credit(first_code, credit_map)
            assert isinstance(c, (int, float))
            assert c >= 0


# ================================================================
# Test: utils/analytics_engine.py
# ================================================================
def _make_sample_df():
    """Create a sample student DataFrame for testing."""
    return pd.DataFrame({
        "Student_ID": ["S001", "S002", "S003", "S004", "S005"],
        "Name": ["Alice", "Bob", "Carol", "Dave", "Eve"],
        "BCS501_Internal": [45, 30, 10, 40, 25],
        "BCS501_External": [50, 35, 8, 45, 20],
        "BCS501_Total": [95, 65, 18, 85, 45],
        "BCS501_Result": ["P", "P", "F", "P", "P"],
        "BCS502_Internal": [40, 20, 15, 38, 10],
        "BCS502_External": [42, 15, 12, 40, 8],
        "BCS502_Total": [82, 35, 27, 78, 18],
        "BCS502_Result": ["P", "F", "F", "P", "F"],
        "BCS503_Internal": [48, 42, 25, 44, 30],
        "BCS503_External": [46, 38, 20, 42, 28],
        "BCS503_Total": [94, 80, 45, 86, 58],
        "BCS503_Result": ["P", "P", "P", "P", "P"],
    })


class TestIdentifyAtRisk:
    def test_returns_dict(self):
        from utils.analytics_engine import identify_at_risk_students
        df = _make_sample_df()
        result = identify_at_risk_students(df, ["BCS501", "BCS502", "BCS503"])
        assert isinstance(result, dict)
        assert "at_risk_students" in result
        assert "risk_summary" in result

    def test_detects_failures(self):
        from utils.analytics_engine import identify_at_risk_students
        df = _make_sample_df()
        result = identify_at_risk_students(df, ["BCS501", "BCS502", "BCS503"])
        at_risk = result["at_risk_students"]
        if not at_risk.empty:
            # S003 has 2 failures -> should be flagged
            s003 = at_risk[at_risk["Student_ID"] == "S003"]
            assert not s003.empty

    def test_empty_df(self):
        from utils.analytics_engine import identify_at_risk_students
        empty = pd.DataFrame()
        result = identify_at_risk_students(empty)
        assert isinstance(result, dict)
        assert result["at_risk_students"].empty


class TestGenerateInsights:
    def test_returns_list(self):
        from utils.analytics_engine import generate_insights
        df = _make_sample_df()
        result = generate_insights(df, ["BCS501", "BCS502", "BCS503"])
        assert isinstance(result, list)

    def test_insights_have_required_keys(self):
        from utils.analytics_engine import generate_insights
        df = _make_sample_df()
        insights = generate_insights(df, ["BCS501", "BCS502", "BCS503"])
        for insight in insights:
            assert "type" in insight
            assert "message" in insight
            assert insight["type"] in ("danger", "warning", "info", "success")

    def test_empty_subjects(self):
        from utils.analytics_engine import generate_insights
        df = _make_sample_df()
        result = generate_insights(df, [])
        assert isinstance(result, list)


class TestComputeBacklogs:
    def test_returns_dict(self):
        from utils.analytics_engine import compute_backlogs
        df = _make_sample_df()
        result = compute_backlogs(df, ["BCS501", "BCS502", "BCS503"])
        assert isinstance(result, dict)
        assert "backlog_df" in result
        assert "summary" in result

    def test_backlog_counts(self):
        from utils.analytics_engine import compute_backlogs
        df = _make_sample_df()
        result = compute_backlogs(df, ["BCS501", "BCS502", "BCS503"])
        backlog_df = result["backlog_df"]
        # S003 should have 2 backlogs (BCS501_F, BCS502_F)
        s003 = backlog_df[backlog_df["Student_ID"] == "S003"]
        if not s003.empty:
            assert s003.iloc[0]["Backlog_Count"] == 2


class TestBranchKpis:
    def test_returns_dict(self):
        from utils.analytics_engine import branch_kpis
        df_long = pd.DataFrame({
            "Student_ID": ["S1", "S1", "S2", "S2"],
            "Subject": ["BCS501", "BCS502", "BCS501", "BCS502"],
            "Internal": [40, 35, 20, 10],
            "External": [45, 30, 15, 5],
            "Total": [85, 65, 35, 15],
            "Result": ["P", "P", "F", "F"],
            "Branch": ["CS", "CS", "CS", "CS"],
        })
        result = branch_kpis(df_long)
        assert isinstance(result, dict)


# ================================================================
# Test: branch_processor.py
# ================================================================
class TestBranchProcessor:
    def test_normalize_student_id(self):
        from branch_processor import normalize_student_id
        df = pd.DataFrame({"USN": ["1xx23cs001", "1XX23CS002"], "Name": ["A", "B"]})
        result = normalize_student_id(df)
        assert "Student_ID" in result.columns

    def test_extract_subject_codes(self):
        from branch_processor import extract_subject_codes
        cols = ["Student_ID", "Name", "BCS501_Internal", "BCS501_External", "BCS502_Total"]
        codes = extract_subject_codes(cols)
        assert "BCS501" in codes
        assert "BCS502" in codes
        assert "Student_ID" not in codes

    def test_compute_overall_result(self):
        from branch_processor import compute_overall_result
        df = pd.DataFrame({
            "BCS501_Result": ["P", "F", "P"],
            "BCS502_Result": ["P", "P", "F"],
            "BCS501_Internal": [40, 10, 40],
            "BCS501_External": [40, 10, 40],
            "BCS501_Total": [80, 20, 80],
            "BCS502_Internal": [40, 40, 10],
            "BCS502_External": [40, 40, 10],
            "BCS502_Total": [80, 80, 20],
        })
        result = compute_overall_result(df, ["BCS501", "BCS502"])
        assert "Overall_Result" in result.columns
        assert result["Overall_Result"].iloc[0] == "P"
        assert result["Overall_Result"].iloc[1] == "F"
        assert result["Overall_Result"].iloc[2] == "F"

    def test_assign_category(self):
        from branch_processor import assign_category
        df = pd.DataFrame({
            "Overall_Result": ["P", "P", "P", "F", "A"],
            "Percentage": [75.0, 62.0, 52.0, 30.0, 0.0],
        })
        result = assign_category(df)
        assert "Category" in result.columns
        assert result["Category"].iloc[0] == "FCD"
        assert result["Category"].iloc[1] == "FC"
        assert result["Category"].iloc[2] == "SC"
        assert result["Category"].iloc[3] == "Fail"
        assert result["Category"].iloc[4] == "Absent"


# ================================================================
# Test: services/pdf_service.py
# ================================================================
class TestPdfService:
    def test_student_report_pdf(self):
        from services.pdf_service import generate_student_report_pdf
        student = {
            "Student ID": "1XX23CS001",
            "Name": "Test Student",
            "Overall_Result": "P",
            "Section": "A",
            "Total_Marks": 580,
            "BCS501_Internal": 45,
            "BCS501_External": 50,
            "BCS501_Total": 95,
            "BCS501_Result": "P",
        }
        pdf_bytes = generate_student_report_pdf(student, ["BCS501"])
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 100

    def test_class_summary_pdf(self):
        from services.pdf_service import generate_class_summary_pdf
        df = _make_sample_df()
        pdf_bytes = generate_class_summary_pdf(df, ["BCS501", "BCS502", "BCS503"])
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_pdf_to_download_data(self):
        from services.pdf_service import pdf_to_download_data
        result = pdf_to_download_data(b"%PDF-fake", "test.pdf")
        assert result["filename"] == "test.pdf"
        assert result["base64"] is True
        assert isinstance(result["content"], str)


# ================================================================
# Test: data_processing.py (if functions exist)
# ================================================================
class TestDataProcessing:
    def test_import_succeeds(self):
        import data_processing
        assert hasattr(data_processing, "__name__")


# ================================================================
# Test: config.py
# ================================================================
class TestConfig:
    def test_config_defaults(self):
        from config import Config
        assert isinstance(Config.PORT, int)
        assert isinstance(Config.DEBUG, bool)
        assert Config.MAX_UPLOAD_SIZE_MB > 0
        assert Config.RATE_LIMIT_FEEDBACK > 0


# ================================================================
# Test: logging_config.py
# ================================================================
class TestLoggingConfig:
    def test_get_logger(self):
        from logging_config import get_logger
        lg = get_logger("test_module")
        assert lg is not None
        assert lg.name == "test_module"

    def test_timing_context(self):
        import logging
        from logging_config import TimingContext
        lg = logging.getLogger("test_timing")
        with TimingContext(lg, "test_operation") as tc:
            time.sleep(0.01)
        # Should not raise
