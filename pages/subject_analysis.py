# pages/subject_analysis.py

import dash
from dash import html, dcc, Input, Output, callback
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

    # KPI Cards + Charts
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
    # ---------------- Handle No Data ----------------
    if json_data is None:
        return [], html.P(
            "Please upload data first on the Overview page.",
            className="text-muted text-center"
        )

    # Load DataFrame
    df = pd.read_json(json_data, orient='split')

    if 'Name' not in df.columns:
        df['Name'] = df.index.astype(str)

    # Exclude non-subject columns
    exclude_cols = [
        'Student ID', 'Name', 'Section', 'Attendance',
        'Total_Marks', 'Class_Rank', 'Section_Rank', 'Overall_Result'
    ]
    subjects = [col for col in df.columns if col not in exclude_cols]
    dropdown_options = [{'label': s, 'value': s} for s in subjects]

    # ---------------- If No Subject Selected ----------------
    if selected_subject is None or selected_subject not in df.columns:
        return dropdown_options, html.P(
            "Select a subject to see analysis.",
            className="text-center text-muted"
        )

    # ---------------- Detect Subject Type ----------------
    col = df[selected_subject].astype(str).str.strip()

    # Check if subject column contains result-like values (P/F/Pass/Fail)
    if col.str.upper().isin(['P', 'F', 'PASS', 'FAIL']).any():
        df['Result'] = col.str.upper().replace({'PASS': 'P', 'FAIL': 'F'})
        df['Result'] = df['Result'].apply(lambda x: 'Pass' if x == 'P' else 'Fail')
        df['Marks'] = None
        is_result_based = True
    else:
        # Numeric marks column
        df[selected_subject] = col.str.replace(',', '', regex=False)
        numeric_col = pd.to_numeric(df[selected_subject], errors='coerce').fillna(0)
        pass_marks = 18  # Define pass marks threshold
        df['Marks'] = numeric_col
        df['Result'] = df['Marks'].apply(lambda x: 'Pass' if x >= pass_marks else 'Fail')
        is_result_based = False

    # ---------------- KPI Calculations ----------------
    total_students = len(df)
    pass_count = (df['Result'] == 'Pass').sum()
    fail_count = (df['Result'] == 'Fail').sum()
    pass_percent = round((pass_count / total_students) * 100, 2) if total_students > 0 else 0
    fail_percent = round((fail_count / total_students) * 100, 2) if total_students > 0 else 0

    # ---------------- KPI Cards ----------------
    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Pass Students", className="text-white-50"),
            html.H3(pass_count)
        ]), color="success", inverse=True), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Fail Students", className="text-white-50"),
            html.H3(fail_count)
        ]), color="danger", inverse=True), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Pass %", className="text-white-50"),
            html.H3(f"{pass_percent}%")
        ]), color="info", inverse=True), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Fail %", className="text-white-50"),
            html.H3(f"{fail_percent}%")
        ]), color="warning", inverse=True), md=3),
    ], className="g-3 mb-4")

    # ---------------- Charts Section ----------------
    charts_row = []

    # Bar Chart (only for marks-based subjects)
    if not is_result_based and df['Marks'].notna().any():
        fig_bar = px.bar(
            df.sort_values(by='Marks', ascending=False),
            x='Name',
            y='Marks',
            color='Result',
            title=f"{selected_subject} Marks Distribution",
            text='Marks',
            color_discrete_map={'Pass': 'green', 'Fail': 'red'}
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            xaxis_title="Student",
            yaxis_title="Marks",
            title_x=0.5,
            height=500
        )
        charts_row.append(
            dbc.Col(dcc.Graph(figure=fig_bar), md=8)
        )

    # Pie Chart (Pass vs Fail)
    pie_fig = px.pie(
        names=['Pass', 'Fail'],
        values=[pass_count, fail_count],
        title=f"{selected_subject} Result Breakdown",
        color=['Pass', 'Fail'],
        color_discrete_map={'Pass': 'green', 'Fail': 'red'}
    )
    pie_fig.update_layout(title_x=0.5, height=500)
    charts_row.append(
        dbc.Col(dcc.Graph(figure=pie_fig), md=4)
    )

    charts_layout = dbc.Row(charts_row, className="g-3")

    # ---------------- Combine Layout ----------------
    content = dbc.Container([
        kpi_cards,
        charts_layout
    ], fluid=True)

    return dropdown_options, content
