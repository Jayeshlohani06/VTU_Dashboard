import pandas as pd
import numpy as np
import re


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


# =====================================================
# AT-RISK STUDENT DETECTION
# =====================================================

def _extract_subject_codes(columns):
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


def identify_at_risk_students(df, selected_subjects=None):
    """
    Identify students at risk of academic failure.

    Returns a dict with:
    - at_risk_students: DataFrame of at-risk students with reasons
    - risk_summary: dict with counts by risk category
    - borderline_students: students within 2 marks of failing in any subject
    - internal_external_gap: students with large gap between IA and EA
    """
    if df is None or df.empty:
        return {"at_risk_students": pd.DataFrame(), "risk_summary": {},
                "borderline_students": pd.DataFrame(), "internal_external_gap": pd.DataFrame()}

    subject_codes = selected_subjects or _extract_subject_codes(df.columns)

    risk_records = []
    borderline_records = []
    gap_records = []

    id_col = "Student ID" if "Student ID" in df.columns else "Student_ID"

    for _, row in df.iterrows():
        student_id = row.get(id_col, "")
        name = row.get("Name", "")
        fail_count = 0
        fail_subjects = []
        borderline_subjects = []
        gap_subjects = []

        for sub in subject_codes:
            res_col = f"{sub}_Result"
            int_col = f"{sub}_Internal"
            ext_col = f"{sub}_External"
            tot_col = f"{sub}_Total"

            # Skip electives
            if all(pd.isna(row.get(c)) or str(row.get(c)).strip() == "" for c in [int_col, ext_col, tot_col, res_col] if c in df.columns):
                continue

            result = str(row.get(res_col, "")).strip().upper() if res_col in df.columns else ""

            if result in ("F", "FAIL"):
                fail_count += 1
                fail_subjects.append(sub)

            # Borderline check: external marks close to passing (within 2 marks of 18 or 21)
            ext_val = pd.to_numeric(row.get(ext_col), errors="coerce") if ext_col in df.columns else None
            if ext_val is not None and not pd.isna(ext_val):
                if 16 <= ext_val <= 20 and result not in ("P",):
                    borderline_subjects.append(sub)

            # Internal vs External gap analysis
            int_val = pd.to_numeric(row.get(int_col), errors="coerce") if int_col in df.columns else None
            if int_val is not None and ext_val is not None and not pd.isna(int_val) and not pd.isna(ext_val):
                # Normalize to percentage for fair comparison
                int_pct = (int_val / 50) * 100 if int_val <= 50 else (int_val / 100) * 100
                ext_pct = (ext_val / 60) * 100 if ext_val <= 60 else (ext_val / 100) * 100
                gap = int_pct - ext_pct
                if gap > 30:  # >30 percentage point gap
                    gap_subjects.append({"subject": sub, "internal_pct": round(int_pct, 1),
                                         "external_pct": round(ext_pct, 1), "gap": round(gap, 1)})

        # Categorize risk level
        if fail_count >= 3:
            risk_level = "Critical"
            reason = f"Failed in {fail_count} subjects: {', '.join(fail_subjects)}"
        elif fail_count == 2:
            risk_level = "High"
            reason = f"Failed in 2 subjects: {', '.join(fail_subjects)}"
        elif fail_count == 1:
            risk_level = "Moderate"
            reason = f"Failed in {fail_subjects[0]}"
        else:
            risk_level = None
            reason = ""

        if risk_level:
            risk_records.append({
                "Student_ID": student_id, "Name": name,
                "Risk_Level": risk_level, "Failed_Subjects": fail_count,
                "Reason": reason
            })

        if borderline_subjects:
            for sub in borderline_subjects:
                borderline_records.append({
                    "Student_ID": student_id, "Name": name,
                    "Subject": sub,
                    "External_Marks": row.get(f"{sub}_External", ""),
                    "Remark": "Within 2 marks of passing"
                })

        if gap_subjects:
            for g in gap_subjects:
                gap_records.append({
                    "Student_ID": student_id, "Name": name,
                    "Subject": g["subject"],
                    "Internal_%": g["internal_pct"],
                    "External_%": g["external_pct"],
                    "Gap": g["gap"],
                })

    at_risk_df = pd.DataFrame(risk_records)
    borderline_df = pd.DataFrame(borderline_records)
    gap_df = pd.DataFrame(gap_records)

    risk_summary = {}
    if not at_risk_df.empty:
        risk_summary = at_risk_df["Risk_Level"].value_counts().to_dict()

    return {
        "at_risk_students": at_risk_df,
        "risk_summary": risk_summary,
        "borderline_students": borderline_df,
        "internal_external_gap": gap_df,
    }


# =====================================================
# SMART NOTIFICATIONS / INSIGHTS
# =====================================================

def generate_insights(df, selected_subjects=None):
    """
    Auto-generate smart insights/alerts based on the data.
    Returns a list of dicts: {type: 'warning'|'success'|'info', icon, message}
    """
    if df is None or df.empty:
        return []

    insights = []
    subject_codes = selected_subjects or _extract_subject_codes(df.columns)
    id_col = "Student ID" if "Student ID" in df.columns else "Student_ID"
    total_students = len(df)

    # 1. Overall pass rate insight
    if "Overall_Result" in df.columns:
        pass_count = (df["Overall_Result"] == "P").sum()
        pass_pct = pass_count / max(total_students, 1) * 100

        if pass_pct >= 90:
            insights.append({
                "type": "success", "icon": "bi-trophy-fill",
                "message": f"Excellent! {pass_pct:.1f}% pass rate — outstanding batch performance."
            })
        elif pass_pct < 50:
            insights.append({
                "type": "danger", "icon": "bi-exclamation-triangle-fill",
                "message": f"Critical: Only {pass_pct:.1f}% pass rate. Immediate academic intervention recommended."
            })

    # 2. Subject-level alerts
    for sub in subject_codes:
        res_col = f"{sub}_Result"
        if res_col not in df.columns:
            continue
        results = df[res_col].dropna().astype(str).str.strip().str.upper()
        results = results[results != ""]
        if len(results) == 0:
            continue

        fail_count = results.str.startswith("F").sum()
        fail_rate = fail_count / len(results) * 100

        if fail_rate >= 50:
            insights.append({
                "type": "danger", "icon": "bi-exclamation-octagon-fill",
                "message": f"Subject {sub} has {fail_rate:.0f}% fail rate ({fail_count}/{len(results)} students failed)."
            })
        elif fail_rate >= 30:
            insights.append({
                "type": "warning", "icon": "bi-exclamation-triangle",
                "message": f"Subject {sub}: {fail_rate:.0f}% fail rate — above normal threshold."
            })

    # 3. Borderline students count
    borderline_count = 0
    for sub in subject_codes:
        ext_col = f"{sub}_External"
        if ext_col in df.columns:
            ext_vals = pd.to_numeric(df[ext_col], errors="coerce")
            borderline_count += ((ext_vals >= 16) & (ext_vals <= 20)).sum()

    if borderline_count > 0:
        insights.append({
            "type": "info", "icon": "bi-info-circle-fill",
            "message": f"{borderline_count} borderline cases detected (students within 2 marks of passing)."
        })

    # 4. Best performing section (if sections exist)
    if "Section" in df.columns and df["Section"].nunique() > 1 and "Overall_Result" in df.columns:
        sec_stats = df.groupby("Section").agg(
            total=(id_col, "count"),
            passed=("Overall_Result", lambda x: (x == "P").sum())
        ).reset_index()
        sec_stats["pass_pct"] = sec_stats["passed"] / sec_stats["total"] * 100
        best_sec = sec_stats.sort_values("pass_pct", ascending=False).iloc[0]
        worst_sec = sec_stats.sort_values("pass_pct").iloc[0]

        insights.append({
            "type": "success", "icon": "bi-star-fill",
            "message": f"Best section: {best_sec['Section']} ({best_sec['pass_pct']:.1f}% pass rate)."
        })

        if best_sec["pass_pct"] - worst_sec["pass_pct"] > 20:
            insights.append({
                "type": "warning", "icon": "bi-arrow-left-right",
                "message": f"Large gap between sections: {best_sec['Section']} ({best_sec['pass_pct']:.1f}%) vs {worst_sec['Section']} ({worst_sec['pass_pct']:.1f}%)."
            })

    # Limit to top 6 most important insights
    priority = {"danger": 0, "warning": 1, "info": 2, "success": 3}
    insights.sort(key=lambda x: priority.get(x["type"], 4))
    return insights[:6]


# =====================================================
# BACKLOG / ARREAR TRACKER
# =====================================================

def compute_backlogs(df, selected_subjects=None):
    """
    Compute backlog statistics for each student.

    Returns a dict with:
    - backlog_df: DataFrame with Student_ID, Name, Backlog_Count, Backlog_Subjects
    - subject_backlog_stats: DataFrame with Subject, Backlog_Count (sorted desc)
    - summary: dict with total_backlogs, avg_backlogs_per_failed, most_common_backlog
    """
    if df is None or df.empty:
        return {"backlog_df": pd.DataFrame(), "subject_backlog_stats": pd.DataFrame(), "summary": {}}

    subject_codes = selected_subjects or _extract_subject_codes(df.columns)
    id_col = "Student ID" if "Student ID" in df.columns else "Student_ID"

    student_backlogs = []
    subject_fail_counts = {}

    for _, row in df.iterrows():
        student_id = row.get(id_col, "")
        name = row.get("Name", "")
        backlogs = []

        for sub in subject_codes:
            res_col = f"{sub}_Result"
            ext_col = f"{sub}_External"

            # Skip electives
            if all(pd.isna(row.get(c)) or str(row.get(c)).strip() == "" for c in [f"{sub}_Internal", ext_col, f"{sub}_Total", res_col] if c in df.columns):
                continue

            result = str(row.get(res_col, "")).strip().upper() if res_col in df.columns else ""
            ext_val = pd.to_numeric(row.get(ext_col), errors="coerce") if ext_col in df.columns else None

            is_fail = result in ("F", "FAIL")
            is_absent = (ext_val == 0 or pd.isna(ext_val)) and result in ("A", "ABSENT", "")

            if is_fail or is_absent:
                backlogs.append(sub)
                subject_fail_counts[sub] = subject_fail_counts.get(sub, 0) + 1

        if backlogs:
            student_backlogs.append({
                "Student_ID": student_id,
                "Name": name,
                "Backlog_Count": len(backlogs),
                "Backlog_Subjects": ", ".join(backlogs),
            })

    backlog_df = pd.DataFrame(student_backlogs)
    subject_stats = pd.DataFrame([
        {"Subject": sub, "Backlog_Count": count}
        for sub, count in subject_fail_counts.items()
    ]).sort_values("Backlog_Count", ascending=False) if subject_fail_counts else pd.DataFrame()

    summary = {}
    if not backlog_df.empty:
        summary["total_students_with_backlogs"] = len(backlog_df)
        summary["total_backlog_instances"] = int(backlog_df["Backlog_Count"].sum())
        summary["avg_backlogs_per_student"] = round(backlog_df["Backlog_Count"].mean(), 1)
        summary["max_backlogs"] = int(backlog_df["Backlog_Count"].max())
        if not subject_stats.empty:
            summary["most_common_backlog"] = subject_stats.iloc[0]["Subject"]

    return {
        "backlog_df": backlog_df,
        "subject_backlog_stats": subject_stats,
        "summary": summary,
    }
