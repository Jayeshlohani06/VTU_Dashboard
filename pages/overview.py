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

# ---------- PAGE LAYOUT ----------
layout = dbc.Container([
    html.H4("📊 Class Overview", className="text-center mb-4"),

    # File Upload Section
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            '📁 Drag and Drop or ',
            html.A('Select Excel File')
        ]),
        style={
            'width': '100%', 'height': '60px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '10px', 'textAlign': 'center',
            'margin-bottom': '20px'
        },
        multiple=False
    ),

    # KPI Cards Row
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

    html.H5("📋 Uploaded Data Preview", className="text-center"),
    html.Div(id='data-preview', className="mt-3"),

    dcc.Store(id='stored-data')
], fluid=True)


# ---------- CALLBACK ----------
@callback(
    [Output('total-students', 'children'),
     Output('present-students', 'children'),
     Output('passed-students', 'children'),
     Output('result-percent', 'children'),
     Output('data-preview', 'children'),
     Output('stored-data', 'data')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def update_dashboard(contents, filename):
    if contents is None:
        return ("—", "—", "—", "—",
                html.P("Please upload an Excel file to begin analysis.", className="text-muted text-center"),
                None)

    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        # Process Excel using data_processing.py
        df_processed, total_cols, kpi_data = preprocess_excel(io.BytesIO(decoded))
    except Exception as e:
        return ("—", "—", "—", "—",
                html.P(f"Error processing file: {e}", className="text-danger text-center"),
                None)

    if df_processed is None or kpi_data is None:
        return ("—", "—", "—", "—",
                html.P("Invalid or empty file. Please check format.", className="text-danger text-center"),
                None)

    # Ensure Result % is float to prevent formatting error
    try:
        result_percent = float(kpi_data.get("Result %", 0.0))
    except ValueError:
        result_percent = 0.0

    # Data preview table
    preview_table = dbc.Table.from_dataframe(
        df_processed.head(10),
        striped=True,
        bordered=True,
        hover=True,
        className="shadow-sm"
    )

    return (
        kpi_data.get("Total Students", 0),
        kpi_data.get("Total Students", 0),  # Present Students = Total Students
        kpi_data.get("Passed Students", 0),
        f"{result_percent:.2f}%",
        preview_table,
        df_processed.to_json(date_format='iso', orient='split')
    )
