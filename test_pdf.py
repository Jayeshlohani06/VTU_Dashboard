import pandas as pd
import traceback

try:
    from services.pdf_service import generate_complete_report_pdf
    print("Import OK")

    kpi_data = {"Total Students": 60, "Appeared": 55, "Passed": 40, "Failed": 10, "Absent": 5, "Pass %": "72.7%"}
    overview_df = pd.DataFrame({"Student_ID": ["S1","S2"], "Name": ["A","B"], "Overall_Result": ["P","F"]})
    ranking_df = pd.DataFrame({"Student_ID": ["S1","S2"], "Name": ["A","B"], "Total_Marks": [500,300], "Percentage": [80.0,50.0], "Overall_Result": ["P","F"], "Class_Rank": pd.array([1, pd.NA], dtype="Int64")})
    subject_df = pd.DataFrame({"Subject": ["MATH"], "Total": [60], "Appeared": [55], "Absent": [5], "Passed": [40], "Failed": [15], "Pass %": [72.7]})
    category_df = pd.DataFrame({"Student_ID": ["S1"], "Name": ["A"], "Total_Marks": [500], "Percentage": [80.0], "Category": ["FCD (First Class Distinction)"]})
    breakdown = {
        "Passed": pd.DataFrame({"Student_ID": ["S1"], "Name": ["A"], "Total_Marks": [500], "percentage": [80.0]}),
        "Failed": pd.DataFrame({"Student_ID": ["S2"], "Name": ["B"], "Total_Marks": [300], "percentage": [50.0]}),
    }

    pdf_bytes = generate_complete_report_pdf(
        kpi_data=kpi_data,
        overview_df=overview_df,
        ranking_df=ranking_df,
        subject_df=subject_df,
        category_df=category_df,
        kpi_breakdown_dfs=breakdown,
    )
    print(f"PDF generated: {len(pdf_bytes)} bytes - SUCCESS")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    traceback.print_exc()
