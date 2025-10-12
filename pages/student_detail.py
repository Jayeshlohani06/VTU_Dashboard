import dash
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

dash.register_page(__name__, path="/student_detail", name="Student Detail")

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("🎓 Student Detail Lookup", className="mb-4 text-center"),

    # Input box for Student ID or Name
    dbc.Row([
        dbc.Col(dcc.Input(
            id='student-search',
            type='text',
            placeholder='Enter Student ID or Name...',
            debounce=True,  # triggers callback when user stops typing
            className="form-control"
        ), md=6),
        dbc.Col(dbc.Button("Search", id='search-btn', color="primary", className="ms-2"), md=2)
    ], justify="center", className="mb-4"),

    # Div to show student info
    html.Div(id='student-detail-content')
], fluid=True)


# ---------- Callback ----------
@dash.callback(
    Output('student-detail-content', 'children'),
    Input('search-btn', 'n_clicks'),
    State('student-search', 'value'),
    State('stored-data', 'data')
)
def display_student_detail(n_clicks, search_value, json_data):
    # ---------------- No data uploaded ----------------
    if not json_data:
        return html.P("Please upload data first on the Overview page.", className="text-muted text-center")

    # ---------------- No search input ----------------
    if not search_value:
        return html.P("Enter Student ID or Name to search.", className="text-muted text-center")

    # Load DataFrame from stored JSON
    df = pd.read_json(json_data, orient='split')

    # ---------- Detect and Fix Student ID Column ----------
    if 'Student ID' not in df.columns:
        possible_id_col = df.columns[0]
        df.rename(columns={possible_id_col: 'Student ID'}, inplace=True)

    if 'Name' not in df.columns:
        df['Name'] = ""

    # ---------- Filter by Student ID or Name (case-insensitive) ----------
    mask = df.apply(
        lambda row: search_value.lower() in str(row.get('Student ID', '')).lower()
                    or search_value.lower() in str(row.get('Name', '')).lower(),
        axis=1
    )
    student_df = df[mask]

    # ---------------- No matching student ----------------
    if student_df.empty:
        return html.P("No student found with this ID or Name.", className="text-danger text-center")

    student_df = student_df.reset_index(drop=True)

    # ---------- Identify subject columns dynamically ----------
    exclude_cols = [
        'Student ID', 'Name', 'Section', 'Attendance', 'Total_Marks',
        'Class_Rank', 'Section_Rank', 'Overall_Result'
    ]
    subjects = [col for col in student_df.columns if col not in exclude_cols]

    # ---------- Helper function to safely fetch column ----------
    def safe_get(col):
        return student_df.at[0, col] if col in student_df.columns else "N/A"

    # ---------- Student Basic Info ----------
    student_info = dbc.Card([
        dbc.CardBody([
            html.H5(f"Student ID: {safe_get('Student ID')}"),
            html.H5(f"Name: {safe_get('Name')}"),
            html.H5(f"Section: {safe_get('Section')}"),
            html.H5(f"Total Marks: {safe_get('Total_Marks')}"),
            html.H5(f"Class Rank: {safe_get('Class_Rank')}"),
            html.H5(f"Section Rank: {safe_get('Section_Rank')}"),
            html.H5(f"Overall Result: {safe_get('Overall_Result')}"),
        ])
    ], className="mb-4 shadow-sm")

    # ---------- Subject-wise Marks Table with Pass/Fail ----------
    if subjects:
        marks_data = []

        for subject in subjects:
            mark = student_df.at[0, subject]
            try:
                mark_value = float(mark)
                status = "Pass" if mark_value >= 18 else "Fail"
            except:
                status = "N/A"
                mark_value = mark

            marks_data.append({"Subject": subject, "Marks": mark_value, "Status": status})

        subject_table = dash_table.DataTable(
            data=marks_data,
            columns=[
                {"name": 'Subject', "id": 'Subject'},
                {"name": 'Marks', "id": 'Marks'},
                {"name": 'Status', "id": 'Status'}
            ],
            style_header={'backgroundColor': '#f0f0f0', 'fontWeight': 'bold'},
            style_data_conditional=[
                {'if': {'filter_query': '{Status} = "Fail"'}, 'backgroundColor': '#ffcccc'},
                {'if': {'filter_query': '{Status} = "Pass"'}, 'backgroundColor': '#ccffcc'}
            ],
            style_cell={'textAlign': 'center', 'fontSize': 15},
            style_table={'width': '60%', 'margin': 'auto'}
        )

        return html.Div([student_info, subject_table])

    else:
        return html.Div([
            student_info,
            html.P("No subject data available.", className="text-muted text-center")
        ])
