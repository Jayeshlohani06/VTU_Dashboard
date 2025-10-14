# pages/overview.py

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io

dash.register_page(__name__, path='/', name="Overview")


# ---------- Helper Functions ----------
def process_uploaded_excel(contents):
    """Reads and cleans the uploaded Excel file."""
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded), header=[0, 1])  # Multi-level header
    # Flatten multi-index columns
    df.columns = [' '.join([str(i) for i in col if str(i) != 'nan']).strip() for col in df.columns.values]
    df = df.loc[:, df.columns.str.strip() != '']  # remove empty cols
    return df


def get_subject_codes(df):
    """Extract unique subject codes from columns."""
    cols = df.columns[1:]  # skip first metadata column
    cols = [c for c in cols if c.strip() != '']
    subject_codes = sorted(list(set([c.split()[0] for c in cols])))
    return subject_codes


# ---------- PAGE LAYOUT ----------
layout = dbc.Container([
    html.H4("📊 Class Overview", className="text-center mb-4"),

    # Upload Section
    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Drag and Drop or ', html.A('Select Excel File')]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '10px', 'textAlign': 'center',
            'margin-bottom': '20px'
        },
        multiple=False
    ),

    # Subject Dropdown
    dbc.Card(dbc.CardBody([
        html.H6("Select Subject(s):"),
        dcc.Dropdown(
            id='subject-selector',
            options=[], value=[],
            multi=True,
            placeholder="Upload file to select subjects",
            style={'maxHeight': '150px', 'overflowY': 'auto'}
        )
    ]), className="shadow-sm p-3 mb-4"),

    # KPI Row
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Students", className="text-muted"),
            html.H3(id="total-students", className="fw-bold")
        ]), color="primary", inverse=True), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Present Students", className="text-muted"),
            html.H3(id="present-students", className="fw-bold")
        ]), color="secondary", inverse=True), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Passed Students", className="text-muted"),
            html.H3(id="passed-students", className="fw-bold")
        ]), color="success", inverse=True), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Result %", className="text-muted"),
            html.H3(id="result-percent", className="fw-bold")
        ]), color="info", inverse=True), md=3),
    ], className="mb-4 text-center"),

    html.Hr(),
    html.H5("📋 Uploaded Data Preview", className="text-center mb-3"),
    html.Div(id='data-preview', className="mt-3"),

    # Persistent Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session')
], fluid=True)


# ---------- Callback 1: Populate dropdown with session persistence ----------
@callback(
    Output('subject-selector', 'options'),
    Output('subject-selector', 'value'),
    Output('stored-data', 'data'),
    Output('overview-selected-subjects', 'data'),
    Input('upload-data', 'contents'),
    State('stored-data', 'data'),
    State('overview-selected-subjects', 'data'),
    prevent_initial_call=False
)
def populate_subject_dropdown(contents, stored_data, stored_subjects):
    # --- If no new file uploaded, use session data ---
    if not contents:
        if stored_data and stored_subjects:
            options = [{'label': s, 'value': s} for s in stored_subjects]
            return options, stored_subjects, stored_data, stored_subjects
        return [], [], None, None

    # --- Process uploaded file ---
    df = process_uploaded_excel(contents)
    subjects = get_subject_codes(df)
    options = [{'label': s, 'value': s} for s in subjects]
    json_data = df.to_json(date_format='iso', orient='split')
    return options, subjects, json_data, subjects


# ---------- Callback 2: Update KPIs and Table ----------
@callback(
    [Output('total-students', 'children'),
     Output('present-students', 'children'),
     Output('passed-students', 'children'),
     Output('result-percent', 'children'),
     Output('data-preview', 'children')],
    Input('subject-selector', 'value'),
    State('stored-data', 'data'),
    State('overview-selected-subjects', 'data')
)
def update_dashboard(selected_subjects, json_data, stored_subjects):
    # Use session data if dropdown empty
    if (not selected_subjects) and stored_subjects:
        selected_subjects = stored_subjects

    if json_data is None or not selected_subjects:
        return "", "", "", "", html.Div(
            "⬆️ Please upload a file and select subjects.", 
            className="text-muted text-center mt-3"
        )

    df = pd.read_json(json_data, orient='split')
    meta_col = df.columns[0]

    # Filter columns for selected subjects
    selected_cols = [c for c in df.columns if any(c.startswith(s) for s in selected_subjects)]
    if not selected_cols:
        return "", "", "", "", html.Div("No matching columns found.", className="text-muted text-center")

    df_filtered = df[[meta_col] + selected_cols].copy()

    # Convert numeric columns
    for c in selected_cols:
        if any(k in c for k in ['Internal', 'External', 'Total']):
            df_filtered[c] = pd.to_numeric(df_filtered[c], errors='coerce').fillna(0)

    # Total marks
    total_cols = [c for c in selected_cols if 'Total' in c]
    df_filtered['Total_Marks'] = df_filtered[total_cols].sum(axis=1) if total_cols else 0

    # Overall Result
    result_cols = [c for c in selected_cols if 'Result' in c]
    if result_cols:
        df_filtered['Overall_Result'] = df_filtered[result_cols].apply(
            lambda row: 'P' if all(v == 'P' for v in row if pd.notna(v)) else 'F', axis=1
        )
    else:
        df_filtered['Overall_Result'] = 'P'

    # KPI metrics
    total_students = len(df_filtered)
    passed_students = (df_filtered['Overall_Result'] == 'P').sum()
    result_percent = round((passed_students / total_students) * 100, 2) if total_students > 0 else 0
    present_students = total_students

    # Preview table
    preview_table = html.Div([
        html.H6("Preview (first 10 rows):", className="fw-bold mb-2"),
        dbc.Table.from_dataframe(
            df_filtered.head(10),
            striped=True, bordered=True, hover=True,
            className="shadow-sm table-sm"
        )
    ])

    return total_students, present_students, passed_students, f"{result_percent}%", preview_table
