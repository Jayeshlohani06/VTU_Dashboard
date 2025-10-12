# pages/subject_analysis.py

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px

dash.register_page(__name__, path="/subject_analysis", name="Subject Analysis")

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("📊 Subject-wise Analysis", className="mb-4 text-center"),

    # Dropdown to select subject
    dbc.Row([
        dbc.Col(dcc.Dropdown(id='subject-dropdown', placeholder="Select a subject"), md=6)
    ], justify="center", className="mb-4"),

    # Content area for KPI cards and chart
    html.Div(id='subject-analysis-content')
], fluid=True)


# ---------- Callback ----------
@callback(
    [Output('subject-dropdown', 'options'),
     Output('subject-analysis-content', 'children')],
    [Input('stored-data', 'data'),
     Input('subject-dropdown', 'value')]
)
def update_subject_analysis(json_data, selected_subject):
    # ---------------- No data uploaded ----------------
    if json_data is None:
        return [], html.P(
            "Please upload data first on the Overview page.",
            className="text-muted text-center"
        )

    # Load DataFrame from stored JSON
    df = pd.read_json(json_data, orient='split')

    # Ensure 'Name' column exists
    if 'Name' not in df.columns:
        df['Name'] = df.index.astype(str)

    # Detect subjects dynamically
    exclude_cols = ['Student ID', 'Name', 'Section', 'Attendance',
                    'Total_Marks', 'Class_Rank', 'Section_Rank', 'Overall_Result']
    subjects = [col for col in df.columns if col not in exclude_cols]
    dropdown_options = [{'label': s, 'value': s} for s in subjects]

    # ---------------- If no subject selected ----------------
    if selected_subject is None or selected_subject not in df.columns:
        return dropdown_options, html.P(
            "Select a subject to see analysis.", className="text-center text-muted"
        )

    # ------------------ Subject Analysis ------------------
    pass_marks = 40  # define pass marks

    # Safely convert subject column to numeric
    df[selected_subject] = df[selected_subject].astype(str).str.strip().str.replace(',', '', regex=False)
    df[selected_subject] = pd.to_numeric(df[selected_subject], errors='coerce').fillna(0)

    # Compute pass/fail
    df['Result'] = df[selected_subject].apply(lambda x: 'Pass' if x >= pass_marks else 'Fail')
    pass_count = len(df[df['Result'] == 'Pass'])
    fail_count = len(df[df['Result'] == 'Fail'])
    total_students = len(df)
    pass_percent = round((pass_count / total_students) * 100, 2) if total_students > 0 else 0
    fail_percent = round((fail_count / total_students) * 100, 2) if total_students > 0 else 0

    # ---------------- KPI Cards ----------------
    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("Pass Students"), html.H2(pass_count)]), color="success", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("Fail Students"), html.H2(fail_count)]), color="danger", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("Pass %"), html.H2(f"{pass_percent}%")]), color="info", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H5("Fail %"), html.H2(f"{fail_percent}%")]), color="warning", inverse=True), md=3)
    ], className="g-3 mb-4")

    # ---------------- Bar Chart ----------------
    fig = px.bar(
        df.sort_values(by=selected_subject, ascending=False),
        x='Name',
        y=selected_subject,
        color='Result',
        title=f"{selected_subject} Marks Distribution",
        text=selected_subject
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="Student",
        yaxis_title="Marks",
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )

    return dropdown_options, dbc.Container([kpi_cards, dcc.Graph(figure=fig)], fluid=True)
