"""
Multi-branch file loader.
Handles loading, validating, and combining multiple branch Excel files
into a unified DataFrame for cross-branch analysis.
"""

import pandas as pd
from logging_config import get_logger
from branch_processor import (
    parse_branch_excel,
    normalize_student_id,
    extract_subject_codes,
    compute_overall_result,
    compute_percentage,
    assign_category,
)

logger = get_logger("multi_branch_loader")


def load_branches(file_contents_list, branch_names_list):
    """
    Load multiple branch Excel files and combine into a single DataFrame.

    Parameters
    ----------
    file_contents_list : list of str
        Base64-encoded file contents for each branch.
    branch_names_list : list of str
        Branch name labels corresponding to each file.

    Returns
    -------
    combined_df : pd.DataFrame
        Unified DataFrame with all branches, containing:
        Student_ID, Name, Branch, Overall_Result, Total_Marks, Percentage, Category,
        and all subject columns.
    errors : list of str
        Error messages for files that failed to load.
    """
    all_frames = []
    errors = []

    for idx, (contents, branch_name) in enumerate(zip(file_contents_list, branch_names_list)):
        branch_name = str(branch_name).strip() if branch_name else f"Branch {idx + 1}"

        if not contents:
            errors.append(f"{branch_name}: No file uploaded.")
            continue

        df = parse_branch_excel(contents)
        if df.empty:
            errors.append(f"{branch_name}: Failed to parse Excel file.")
            continue

        # Normalize
        df = normalize_student_id(df)
        if "Name" not in df.columns:
            df["Name"] = ""

        subject_codes = extract_subject_codes(df.columns)
        if not subject_codes:
            errors.append(f"{branch_name}: No valid VTU subject codes found.")
            continue

        df = compute_overall_result(df, subject_codes)
        df = compute_percentage(df, subject_codes)
        df = assign_category(df)
        df["Branch"] = branch_name

        all_frames.append(df)
        logger.info("Loaded branch '%s': %d students, %d subjects", branch_name, len(df), len(subject_codes))

    if not all_frames:
        logger.warning("No branches loaded successfully.")
        return pd.DataFrame(), errors

    combined = pd.concat(all_frames, ignore_index=True)
    logger.info("Combined %d branches: %d total students", len(all_frames), len(combined))
    return combined, errors


def to_long_format(df, subject_codes=None):
    """
    Convert wide-format branch data to long format (one row per student-subject).
    Useful for branch_intelligence analytics.

    Returns DataFrame with columns:
    Student_ID, Name, Branch, Subject, Internal, External, Total, Result
    """
    if df is None or df.empty:
        return pd.DataFrame()

    if subject_codes is None:
        subject_codes = extract_subject_codes(df.columns)

    records = []
    for _, row in df.iterrows():
        for sub in subject_codes:
            int_col = f"{sub}_Internal"
            ext_col = f"{sub}_External"
            tot_col = f"{sub}_Total"
            res_col = f"{sub}_Result"

            internal = row.get(int_col)
            external = row.get(ext_col)
            total = row.get(tot_col)
            result = row.get(res_col)

            # Skip if all blank (elective not taken)
            if all(pd.isna(v) or str(v).strip() == "" for v in [internal, external, total, result]):
                continue

            records.append({
                "Student_ID": row.get("Student_ID", ""),
                "Name": row.get("Name", ""),
                "Branch": row.get("Branch", ""),
                "Subject": sub,
                "Internal": pd.to_numeric(internal, errors="coerce"),
                "External": pd.to_numeric(external, errors="coerce"),
                "Total": pd.to_numeric(total, errors="coerce"),
                "Result": str(result).strip() if pd.notna(result) else "",
            })

    return pd.DataFrame(records)
