import pandas as pd
import numpy as np

def preprocess_excel(file_buffer):
    """
    Cleans multi-row Excel data and computes key metrics:
    - Handles multi-row headers and flattens them
    - Detects subject blocks (Total, Result)
    - Calculates per-student total marks and overall pass/fail
    - Computes key performance indicators (KPIs)
    - Adds class rank
    - Returns cleaned DataFrame, column list, and KPI dictionary
    """

    # --- Step 1: Read Excel file (supports multi-row headers) ---
    df_raw = pd.read_excel(file_buffer, header=[0, 1])

    # Flatten multi-level headers safely
    df_raw.columns = [
        "_".join([str(i) for i in col if str(i) != 'nan']).strip()
        for col in df_raw.columns
    ]

    # Drop fully empty rows
    df = df_raw.dropna(how='all').reset_index(drop=True)

    # --- Step 2: Detect student identifier columns ---
    id_cols = [c for c in df.columns if any(x in c.lower() for x in ['name', 'usn', 'roll', 'register'])]

    # --- Step 3: Identify subject columns ---
    total_cols = [c for c in df.columns if c.endswith('_Total')]
    result_cols = [c for c in df.columns if c.endswith('_Result')]
    subject_prefixes = sorted(set(c.split('_')[0] for c in total_cols + result_cols))

    total_marks_list = []
    overall_result_list = []

    # --- Step 4: Compute total marks and results per student ---
    for _, row in df.iterrows():
        total_marks = 0
        subject_results = []

        for sub in subject_prefixes:
            total_col = f"{sub}_Total"
            result_col = f"{sub}_Result"

            if total_col not in df.columns and result_col not in df.columns:
                continue  # skip missing subjects

            total_val = row.get(total_col, np.nan)
            result_val = str(row.get(result_col, "")).strip().upper()

            # Normalize result values
            if result_val.startswith("P"):
                result_val = "P"
            elif result_val.startswith("F"):
                result_val = "F"
            else:
                result_val = "P"  # default to pass if empty

            # Convert total to numeric safely
            if pd.notna(total_val):
                try:
                    total_marks += float(total_val)
                except ValueError:
                    pass

            subject_results.append(result_val)

        # Overall Result → Fail if any subject is failed
        overall_result = "F" if "F" in subject_results else "P"

        total_marks_list.append(total_marks)
        overall_result_list.append(overall_result)

    # --- Step 5: Append computed columns ---
    df["Total_Marks"] = total_marks_list
    df["Overall_Result"] = overall_result_list

    # --- Step 6: KPI Calculations ---
    total_students = len(df)
    present_students = df.shape[0]
    passed_students = (df["Overall_Result"] == "P").sum()
    result_percent = round((passed_students / total_students * 100), 2) if total_students > 0 else 0

    kpi_data = {
        "Total Students": int(total_students),
        "Present Students": int(present_students),
        "Passed Students": int(passed_students),
        "Result %": f"{result_percent}%"
    }

    # --- Step 7: Add Class Rank ---
    df["Class_Rank"] = df["Total_Marks"].rank(ascending=False, method="dense").astype(int)

    # --- Step 8: Final cleanup ---
    df_final = df.reset_index(drop=True)

    return df_final, list(df_final.columns), kpi_data
