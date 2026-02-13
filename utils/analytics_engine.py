import pandas as pd


def branch_kpis(df):
    """
    Returns branch-level intelligence insights
    """

    if df is None or df.empty:
        return {}

    # student level normalization
    students = df.groupby(["Branch", "Student_ID"]).agg(
        Passed=("Result", lambda x: (x == "P").all()),
        Fail_Count=("Result", lambda x: (x == "F").sum())
    ).reset_index()

    branch_summary = students.groupby("Branch").agg(
        Students=("Student_ID", "nunique"),
        Passed=("Passed", lambda x: x.sum()),
        Failed=("Passed", lambda x: (~x).sum())
    ).reset_index()

    branch_summary["Pass_Percent"] = (
        branch_summary["Passed"] / branch_summary["Students"] * 100
    )

    best_branch = branch_summary.sort_values("Pass_Percent", ascending=False).iloc[0]["Branch"]
    weak_branch = branch_summary.sort_values("Pass_Percent").iloc[0]["Branch"]

    return {
        "best_branch": best_branch,
        "weak_branch": weak_branch,
        "branch_summary": branch_summary
    }


def subject_difficulty(df):
    """
    Detect hardest & easiest subjects
    """

    subject_stats = df.groupby("Subject").agg(
        Students=("Student_ID", "nunique"),
        Fail=("Result", lambda x: (x == "F").sum()),
        Pass=("Result", lambda x: (x == "P").sum())
    ).reset_index()

    subject_stats["Fail_Rate"] = subject_stats["Fail"] / subject_stats["Students"]

    hardest = subject_stats.sort_values("Fail_Rate", ascending=False).iloc[0]["Subject"]
    easiest = subject_stats.sort_values("Fail_Rate").iloc[0]["Subject"]

    return {
        "hardest_subject": hardest,
        "easiest_subject": easiest,
        "subject_table": subject_stats
    }
