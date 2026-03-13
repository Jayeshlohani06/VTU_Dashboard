"""
Branch service — business logic for branch-level analytics.
Provides aggregated metrics, comparisons, and insights across branches.
"""

import pandas as pd
import numpy as np
from logging_config import get_logger

logger = get_logger("branch_service")


def get_branch_summary(df):
    """
    Compute summary KPIs per branch from a normalized DataFrame.
    Expects columns: Branch, Student_ID, Overall_Result, Percentage, Total_Marks.
    Returns a summary DataFrame.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    summary = df.groupby("Branch").agg(
        Total=("Student_ID", "nunique"),
        Passed=("Overall_Result", lambda x: (x == "P").sum()),
        Failed=("Overall_Result", lambda x: (x.isin(["F"])).sum()),
        Absent=("Overall_Result", lambda x: (x == "A").sum()),
        Avg_Percentage=("Percentage", "mean"),
        Max_Percentage=("Percentage", "max"),
        Avg_Total=("Total_Marks", "mean"),
    ).reset_index()

    summary["Appeared"] = summary["Total"] - summary["Absent"]
    summary["Pass_Percent"] = (
        summary["Passed"] / summary["Appeared"].replace(0, 1) * 100
    ).round(2)

    logger.info("Branch summary computed for %d branches", len(summary))
    return summary


def get_branch_rankings(summary_df):
    """
    Rank branches by pass percentage.
    Returns dict with best_branch, weak_branch, and ranked list.
    """
    if summary_df.empty:
        return {"best_branch": "N/A", "weak_branch": "N/A", "rankings": []}

    ranked = summary_df.sort_values("Pass_Percent", ascending=False).reset_index(drop=True)
    ranked["Rank"] = range(1, len(ranked) + 1)

    return {
        "best_branch": ranked.iloc[0]["Branch"],
        "weak_branch": ranked.iloc[-1]["Branch"],
        "rankings": ranked.to_dict("records"),
    }


def get_subject_comparison(df, subject_codes):
    """
    Compare subject performance across branches.
    Returns a pivot-style DataFrame with branches as rows and subjects as columns.
    Values represent pass percentage per subject per branch.
    """
    if df is None or df.empty or not subject_codes:
        return pd.DataFrame()

    records = []
    for branch in df["Branch"].unique():
        branch_df = df[df["Branch"] == branch]
        row = {"Branch": branch}
        for sub in subject_codes:
            res_col = f"{sub}_Result"
            if res_col in branch_df.columns:
                valid = branch_df[res_col].dropna()
                valid = valid[valid.astype(str).str.strip() != ""]
                if len(valid) > 0:
                    passed = valid.astype(str).str.upper().str.startswith("P").sum()
                    row[sub] = round(passed / len(valid) * 100, 1)
                else:
                    row[sub] = None
            else:
                row[sub] = None
        records.append(row)

    return pd.DataFrame(records)


def get_category_distribution(df):
    """
    Get category (FCD/FC/SC/Pass/Fail/Absent) count per branch.
    Returns a DataFrame suitable for stacked bar charts.
    """
    if df is None or df.empty or "Category" not in df.columns:
        return pd.DataFrame()

    cat_order = ["FCD", "FC", "SC", "Pass Class", "Fail", "Absent"]
    dist = df.groupby(["Branch", "Category"]).size().reset_index(name="Count")
    dist["Category"] = pd.Categorical(dist["Category"], categories=cat_order, ordered=True)
    return dist.sort_values(["Branch", "Category"])
