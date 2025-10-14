# pages/overview.py

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io

# Import your data_processing.py
from data_processing import preprocess_excel

dash.register_page(__name__, path='/', name="Overview")

# ---------- Helper Functions ----------
def process_uploaded_excel(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    df = pd.read_excel(io.BytesIO(decoded), header=[0, 1])  # MultiIndex header
    # Flatten multi-level header
    df.columns = [' '.join([str(i) for i in col if str(i) != 'nan']).strip() for col in df.columns.values]
    return df

def get_subject_codes(df):
    # Extract all columns excluding first metadata column
    cols = df.columns[1:]
    subject_codes = sorted(list(set([c.split()[0] for c in cols])))
    return subject_codes

# ---------- PAGE LAYOUT ----------
layout = dbc.Container([
    html.H4("📊 Class Overview", className="text-center mb-4"),

    # File Upload Section
    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Drag and Drop or ', html.A('Select Excel File')]),
        style={'width': '100%', 'height': '60px', 'lineHeight': '60px',
               'borderWidth': '2px', 'borderStyle': 'dashed',
               'borderRadius': '10px', 'textAlign': 'center',
               'margin-bottom': '20px'},
        multiple=False
    ),

    # Subject Dropdown Section
    html.Div(id='subject-dropdown-container', className="mb-4"),

    # KPI Cards
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Students", className="text-muted"),
                                       html.H3(id="total-students", className="fw-bold")]),
                         color="primary", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Present Students", className="text-muted"),
                                       html.H3(id="present-students", className="fw-bold")]),
                         color="secondary", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Passed Students", className="text-muted"),
                                       html.H3(id="passed-students", className="fw-bold")]),
                         color="success", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Result %", className="text-muted"),
                                       html.H3(id="result-percent", className="fw-bold")]),
                         color="info", inverse=True), md=3),
    ], className="mb-4 text-center"),

    html.Hr(),

    html.H5("📋 Uploaded Data Preview", className="text-center"),
    html.Div(id='data-preview', className="mt-3"),

    # Stores to share data across pages
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session')  # <-- New
], fluid=True)


# ---------- Callback: Show Subject Dropdown ----------
@callback(
    Output('subject-dropdown-container', 'children'),
    Input('upload-data', 'contents')
)
def show_subject_dropdown(contents):
    if contents is None:
        return None

    df = process_uploaded_excel(contents)
    subject_codes = get_subject_codes(df)

    dropdown = dcc.Dropdown(
        id='subject-selector',
        options=[{'label': s, 'value': s} for s in subject_codes],
        value=subject_codes,  # default all selected
        multi=True,
        placeholder="Select Subject(s)"
    )

    return dbc.Card(dbc.CardBody([
        html.H6("Select Subject(s):"),
        dropdown
    ]), className="shadow-sm p-3")


# ---------- Callback: Update KPIs and Store Selected Subjects ----------
@callback(
    [Output('total-students', 'children'),
     Output('present-students', 'children'),
     Output('passed-students', 'children'),
     Output('result-percent', 'children'),
     Output('data-preview', 'children'),
     Output('stored-data', 'data'),
     Output('overview-selected-subjects', 'data')],  # <-- output selected subjects
    [Input('subject-selector', 'value')],
    [State('upload-data', 'contents')]
)
def update_dashboard(selected_subjects, contents):
    if contents is None or not selected_subjects:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    df = process_uploaded_excel(contents)
    meta_col = df.columns[0]

    # Build list of all columns to use for selected subjects
    cols_to_use = []
    for subj in selected_subjects:
        cols_to_use.extend([c for c in df.columns if c.startswith(subj)])

    df_filtered = df[[meta_col] + cols_to_use].copy()

    # Calculate Total Marks for selected subjects
    total_cols = [c for c in cols_to_use if 'Total' in c]
    df_filtered['Total_Marks'] = df_filtered[total_cols].sum(axis=1)

    # Overall Result: Pass if all Result columns = 'P'
    result_cols = [c for c in cols_to_use if 'Result' in c]
    df_filtered['Overall_Result'] = df_filtered[result_cols].apply(
        lambda row: 'P' if all(v == 'P' for v in row) else 'F', axis=1
    )

    total_students = len(df_filtered)
    passed_students = (df_filtered['Overall_Result'] == 'P').sum()
    result_percent = round(passed_students / total_students * 100, 2) if total_students > 0 else 0.0
    present_students = total_students  # Modify if you have attendance info

    # Data preview table
    preview_table = dbc.Table.from_dataframe(df_filtered.head(10),
                                             striped=True, bordered=True, hover=True,
                                             className="shadow-sm")

    return (
        total_students,
        present_students,
        passed_students,
        f"{result_percent:.2f}%",
        preview_table,
        df_filtered.to_json(date_format='iso', orient='split'),
        selected_subjects  # <-- store selected subjects for other pages
    )
