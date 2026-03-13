"""
Branch processing service.
Centralizes branch-level data normalization, Excel parsing, and 
result computation used by branch_analysis.py and branch_intelligence.py.
"""

import pandas as pd
import numpy as np
import re
import base64
import io
from logging_config import get_logger

logger = get_logger("branch_processor")


def parse_branch_excel(contents):
    """
    Parse raw base64-encoded Excel contents into a clean DataFrame.
    Handles 2-row and 3-row VTU header formats.
    Returns an empty DataFrame on failure.
    """
    if not contents:
        return pd.DataFrame()

    try:
        content_type, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string)
    except Exception as e:
        logger.error("Failed to decode uploaded file: %s", e)
        return pd.DataFrame()

    try:
        df_preview = pd.read_excel(io.BytesIO(decoded), header=None, nrows=10)
    except Exception as e:
        logger.error("Error reading Excel preview: %s", e)
        return pd.DataFrame()

    # Detect header depth
    header_row_count = 2
    for i, row in df_preview.iterrows():
        row_str = row.astype(str).str.lower().tolist()
        if any("internal" in x for x in row_str) and any("external" in x for x in row_str):
            header_row_count = i + 1
            break

    header_indices = list(range(header_row_count))
    try:
        df_raw = pd.read_excel(io.BytesIO(decoded), header=header_indices)
    except Exception as e:
        logger.error("Error reading Excel with headers: %s", e)
        return pd.DataFrame()

    fixed_cols = []
    last_valid_code = None
    is_empty = lambda h: str(h).lower() == "nan" or str(h).startswith("Unnamed:")

    for col_tuple in df_raw.columns:
        if header_row_count == 3:
            h1 = str(col_tuple[0]).strip()
            h2 = str(col_tuple[1]).strip()
            h3 = str(col_tuple[2]).strip()

            if not is_empty(h1):
                last_valid_code = h1
            elif last_valid_code:
                h1 = last_valid_code

            if is_empty(h3):
                val = h1 if not is_empty(h1) else h2
                fixed_cols.append("Name" if "name" in val.lower() else val)
            else:
                fixed_cols.append(f"{h1}_{h3}")
        else:
            h1 = str(col_tuple[0]).strip()
            h2 = str(col_tuple[1]).strip()

            if not is_empty(h1):
                last_valid_code = h1
            elif last_valid_code:
                h1 = last_valid_code

            if is_empty(h2):
                fixed_cols.append("Name" if "name" in h1.lower() else h1)
            else:
                fixed_cols.append(f"{h1}_{h2}")

    df_raw.columns = fixed_cols
    df = df_raw.dropna(how="all").reset_index(drop=True)

    logger.info("Parsed branch Excel: %d rows, %d columns", len(df), len(df.columns))
    return df


def normalize_student_id(df):
    """Identify and rename the student ID column to 'Student_ID'."""
    for c in df.columns:
        cl = c.lower()
        if any(k in cl for k in ["usn", "seat", "roll", "register", "id"]):
            df = df.rename(columns={c: "Student_ID"})
            return df
    df = df.rename(columns={df.columns[0]: "Student_ID"})
    return df


def extract_subject_codes(columns):
    """Extract valid VTU subject codes from column names."""
    subjects = set()
    for col in columns:
        if "_" not in col:
            continue
        prefix, suffix = col.rsplit("_", 1)
        if suffix not in {"Internal", "External", "Total", "Result"}:
            continue
        if re.fullmatch(r"\d?[A-Z]{2,}\d{3}[A-Z]?", prefix):
            subjects.add(prefix)
    return sorted(subjects)


def compute_overall_result(df, subject_codes):
    """
    Compute Overall_Result for each student based on per-subject results.
    Returns the DataFrame with 'Overall_Result' column added.
    """
    result_cols = [f"{sub}_Result" for sub in subject_codes if f"{sub}_Result" in df.columns]

    if not result_cols:
        df["Overall_Result"] = "P"
        return df

    def _row_result(row):
        statuses = []
        for res_col in result_cols:
            sub = res_col.replace("_Result", "")
            ext_col = f"{sub}_External"
            int_col = f"{sub}_Internal"
            tot_col = f"{sub}_Total"

            i_raw = row.get(int_col)
            e_raw = row.get(ext_col)
            t_raw = row.get(tot_col)
            r_raw = row.get(res_col)

            # Elective: all blank → skip
            if all(pd.isna(v) or str(v).strip() == "" for v in [i_raw, e_raw, t_raw, r_raw]):
                continue

            e_val = pd.to_numeric(e_raw, errors="coerce")
            if pd.isna(e_val):
                e_val = 0
            r_str = str(r_raw).strip().upper() if pd.notna(r_raw) else ""

            if e_val == 0 and r_str in ("A", "ABSENT", ""):
                statuses.append("A")
            elif r_str in ("F", "FAIL"):
                statuses.append("F")
            else:
                statuses.append("P")

        if not statuses:
            return "P"
        if statuses.count("A") == len(statuses):
            return "A"
        if "F" in statuses or "A" in statuses:
            return "F"
        return "P"

    df["Overall_Result"] = df.apply(_row_result, axis=1)
    return df


def compute_percentage(df, subject_codes):
    """
    Compute percentage for each student based on subject totals.
    Returns the DataFrame with 'Percentage' column added.
    """
    total_cols = [f"{sub}_Total" for sub in subject_codes if f"{sub}_Total" in df.columns]

    if not total_cols:
        df["Percentage"] = 0.0
        return df

    for c in total_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if "Total_Marks" not in df.columns:
        df["Total_Marks"] = df[total_cols].sum(axis=1)

    # Count active subjects per student
    active_counts = (df[total_cols] > 0).sum(axis=1)
    mode_val = active_counts.mode()
    std_count = int(mode_val.iloc[0]) if not mode_val.empty and mode_val.iloc[0] > 0 else len(total_cols)

    max_marks = np.maximum(active_counts, std_count) * 100
    max_marks = max_marks.replace(0, 1)  # avoid division by zero
    df["Percentage"] = (df["Total_Marks"] / max_marks * 100).round(2)
    return df


def assign_category(df):
    """Add VTU category column (FCD/FC/SC/Pass/F/A)."""

    def _cat(row):
        if row["Overall_Result"] == "A":
            return "Absent"
        if row["Overall_Result"] == "F":
            return "Fail"
        pct = row.get("Percentage", 0)
        if pct >= 70:
            return "FCD"
        if pct >= 60:
            return "FC"
        if pct >= 50:
            return "SC"
        return "Pass Class"

    df["Category"] = df.apply(_cat, axis=1)
    return df
