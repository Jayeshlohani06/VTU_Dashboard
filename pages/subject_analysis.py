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

    # Dropdown to select subjects dynamically
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id='subject-dropdown',
                placeholder="Select a subject",
                multi=True  # allow multiple selection
            ),
            md=6
        )
    ], justify="center", className="mb-4"),

    # KPI Cards + Charts
    html.Div(id='subject-analysis-content'),

    # Hidden stores to access uploaded data and Overview selections
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session')
], fluid=True)


# ---------- Callback ----------
@callback(
    [Output('subject-dropdown', 'options'),
     Output('subject-dropdown', 'value'),
     Output('subject-analysis-content', 'children')],
    [Input('stored-data', 'data'),
     Input('overview-selected-subjects', 'data'),
     Input('subject-dropdown', 'value')]
)
def update_subject_analysis(json_data, selected_overview_subjects, selected_subjects):
    # ---------------- Handle No Data ----------------
    if json_data is None or not selected_overview_subjects:
        return [], [], html.P(
            "Please upload data and select subjects on the Overview page first.",
            className="text-muted text-center"
        )

    # Load DataFrame
    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]  # assume first column is student name/id

    # Subjects from Overview page
    subjects = selected_overview_subjects

    # Dropdown options: Select All + subjects from Overview
    dropdown_options = [{'label': 'Select All', 'value': 'ALL'}] + \
                       [{'label': s, 'value': s} for s in subjects]

    # Default selection
    if not selected_subjects:
        selected_subjects = ['ALL']

    # Handle "Select All"
    if 'ALL' in selected_subjects:
        cols_to_use = subjects
        selected_subjects = ['ALL'] + subjects
    else:
        cols_to_use = selected_subjects

    # ---------------- Select all actual columns starting with subject codes ----------------
    cols_to_use_expanded = []
    for subj in cols_to_use:
        cols_to_use_expanded.extend([c for c in df.columns if c.startswith(subj)])

    if not cols_to_use_expanded:
        return dropdown_options, selected_subjects, html.P(
            "No columns found for the selected subjects in the uploaded data.",
            className="text-muted text-center"
        )

    df_subjects = df[cols_to_use_expanded].copy()

    # Ensure numeric conversion
    for col in df_subjects.columns:
        df_subjects[col] = pd.to_numeric(df_subjects[col], errors='coerce').fillna(0)

    # Compute total marks per student for selected subjects
    df_subjects['Total_Selected_Marks'] = df_subjects.sum(axis=1)

    # Pass/Fail evaluation: Pass if >=18 marks in all selected subjects
    pass_marks = 18
    df_subjects['Result'] = df_subjects.apply(
        lambda row: 'Pass' if (row[cols_to_use_expanded] >= pass_marks).all() else 'Fail', axis=1
    )

    total_students = len(df_subjects)
    pass_count = (df_subjects['Result'] == 'Pass').sum()
    fail_count = (df_subjects['Result'] == 'Fail').sum()
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

    # ---------------- Charts ----------------
    charts_row = []
    for subj in cols_to_use:
        # Select columns starting with this subject code
        subj_cols = [c for c in df.columns if c.startswith(subj)]
        if not subj_cols:
            continue
        # Take the first numeric column for plotting
        col_for_plot = subj_cols[0]
        fig_bar = px.bar(
            df.sort_values(by=col_for_plot, ascending=False),
            x=first_col,
            y=col_for_plot,
            title=f"{subj} Marks Distribution",
            text=col_for_plot
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            xaxis_title="Student",
            yaxis_title="Marks",
            title_x=0.5,
            height=400
        )
        charts_row.append(dbc.Col(dcc.Graph(figure=fig_bar), md=6))

    # Pie chart for overall pass/fail
    pie_fig = px.pie(
        names=['Pass', 'Fail'],
        values=[pass_count, fail_count],
        title=f"Overall Result for Selected Subjects",
        color_discrete_map={'Pass': 'green', 'Fail': 'red'}
    )
    pie_fig.update_layout(title_x=0.5, height=400)
    charts_row.append(dbc.Col(dcc.Graph(figure=pie_fig), md=6))

    charts_layout = dbc.Row(charts_row, className="g-3")

    content = dbc.Container([kpi_cards, charts_layout], fluid=True)

    return dropdown_options, selected_subjects, content
