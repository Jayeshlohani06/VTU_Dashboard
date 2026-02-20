import pandas as pd
import numpy as np
import re

# =====================================================
# SUBJECT EXTRACTION (STRICT VTU ONLY)
# =====================================================
def extract_valid_subjects(columns):
    """
    Extract ONLY valid VTU subject codes.
    Name / Seat Number / Rank / etc will NEVER appear.
    """
    subjects = set()

    for col in columns:
        if "_" not in col:
            continue

        prefix, suffix = col.rsplit("_", 1)

        if suffix not in {"Internal", "External", "Total", "Result"}:
            continue

        # STRICT VTU FORMAT
        if not re.fullmatch(r"[A-Z]{2,}\d{3}[A-Z]?", prefix):
            continue

        subjects.add(prefix)

    return sorted(subjects)


# =====================================================
# MAIN PREPROCESS FUNCTION
# =====================================================
def preprocess_excel(file_buffer):
    """
    ✔ Handles multi-row Excel headers
    ✔ PRESERVES Name column
    ✔ Detects subjects STRICTLY
    ✔ Calculates total marks
    ✔ Calculates overall pass/fail
    ✔ Computes KPIs
    ✔ Adds class rank
    """

    # -------------------------------------------------
    # STEP 1: READ EXCEL (SMART HEADER DETECTION)
    # -------------------------------------------------
    # First, read a small chunk to detect header depth
    # We look for the row containing "Internal", "External", etc.
    df_preview = pd.read_excel(file_buffer, header=None, nrows=10)
    file_buffer.seek(0)
    
    header_row_index = -1
    for i, row in df_preview.iterrows():
        row_str = row.astype(str).str.lower().tolist()
        if any("internal" in x for x in row_str) and any("external" in x for x in row_str):
            header_row_index = i
            break
            
    # Default to 2-row header if detection fails (standard VTU)
    # If detected at index 2 (row 3), it means we have 3 header rows (0, 1, 2)
    header_config = [0, 1]
    if header_row_index == 2:
        header_config = [0, 1, 2]
        
    df_raw = pd.read_excel(file_buffer, header=header_config)
    
    fixed_cols = []
    last_valid_code = None
    
    # Iterate through columns
    if len(header_config) == 3:
        # 3-Row Header: Code -> Name -> Component
        for c1, c2, c3 in df_raw.columns:
            h1 = str(c1).strip() # Subject Code
            h2 = str(c2).strip() # Subject Name
            h3 = str(c3).strip() # Component (Internal/External...)
            
            # Helper to check for empty/unnamed
            def is_empty(h): return h.lower() == "nan" or h.startswith("Unnamed:")

            # Handle Merged Subject Code (Row 0)
            if not is_empty(h1):
                last_valid_code = h1
            elif last_valid_code:
                h1 = last_valid_code
                
            # If component row is empty, it's likely a metadata column (Name, USN)
            if is_empty(h3):
                # Use the top-most non-empty value
                col_name = h1 if not is_empty(h1) else (h2 if not is_empty(h2) else "Unknown")
            else:
                # Subject Column: "Code_Component"
                # We ignore h2 (Subject Name) for the column key to keep logic consistent
                col_name = f"{h1}_{h3}"
            
            fixed_cols.append(col_name)
            
    else:
        # 2-Row Header: Code -> Component (Old Format)
        for c1, c2 in df_raw.columns:
            h1 = str(c1).strip()
            h2 = str(c2).strip()
            
            def is_empty(h): return h.lower() == "nan" or h.startswith("Unnamed:")

            if not is_empty(h1):
                last_valid_code = h1
            elif last_valid_code:
                h1 = last_valid_code
                
            if is_empty(h2):
                col_name = h1
            else:
                col_name = f"{h1}_{h2}"
            
            fixed_cols.append(col_name)

    df_raw.columns = fixed_cols
    df = df_raw.dropna(how="all").reset_index(drop=True)

    # -------------------------------------------------
    # STEP 2: NORMALIZE STUDENT ID & NAME
    # -------------------------------------------------
    student_id_col = None

    for c in df.columns:
        cl = c.lower()
        if any(k in cl for k in ["usn", "seat", "roll", "register"]):
            student_id_col = c
            break

    if student_id_col is None:
        student_id_col = df.columns[0]

    df.rename(columns={student_id_col: "Student ID"}, inplace=True)

    # 🔥 GUARANTEE Name EXISTS 🔥
    if "Name" not in df.columns:
        df["Name"] = ""

    # -------------------------------------------------
    # STEP 3: SUBJECT DETECTION (FIXED)
    # -------------------------------------------------
    subject_codes = extract_valid_subjects(df.columns)

    # -------------------------------------------------
    # STEP 4: TOTAL MARKS & RESULT
    # -------------------------------------------------
    total_marks_list = []
    overall_result_list = []

    for _, row in df.iterrows():
        total_marks = 0
        failed = False

        for sub in subject_codes:
            total_col = f"{sub}_Total"
            result_col = f"{sub}_Result"

            marks = pd.to_numeric(row.get(total_col), errors="coerce")
            result = str(row.get(result_col, "")).strip().upper()

            if pd.notna(marks):
                total_marks += marks

            if result.startswith("F"):
                failed = True

        total_marks_list.append(total_marks)
        overall_result_list.append("F" if failed else "P")

    df["Total_Marks"] = total_marks_list
    df["Overall_Result"] = overall_result_list

    # -------------------------------------------------
    # STEP 5: KPIs
    # -------------------------------------------------
    total_students = len(df)
    passed_students = (df["Overall_Result"] == "P").sum()
    result_percent = round(
        (passed_students / total_students) * 100, 2
    ) if total_students else 0

    kpi_data = {
        "Total Students": total_students,
        "Present Students": total_students,
        "Passed Students": passed_students,
        "Result %": f"{result_percent}%"
    }

    # -------------------------------------------------
    # STEP 6: CLASS RANK
    # -------------------------------------------------
    df["Class_Rank"] = (
        df["Total_Marks"]
        .rank(ascending=False, method="dense")
        .astype(int)
    )

    # -------------------------------------------------
    # FINAL OUTPUT
    # -------------------------------------------------
    df_final = df.reset_index(drop=True)

    return df_final, list(df_final.columns), kpi_data
