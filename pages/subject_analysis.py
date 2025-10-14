# pages/subject_analysis.py

import dash
from dash import html, dcc, Input, Output, callback, dash_table
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
                multi=True
            ),
            md=6
        )
    ], justify="center", className="mb-4"),

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
    if json_data is None or not selected_overview_subjects:
        return [], [], html.P(
            "Please upload data and select subjects on the Overview page first.",
            className="text-muted text-center"
        )

    # Load DataFrame
    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]

    subjects = selected_overview_subjects

    dropdown_options = [{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in subjects]

    if not selected_subjects:
        selected_subjects = ['ALL']

    if 'ALL' in selected_subjects:
        cols_to_use = subjects
        selected_subjects = ['ALL'] + subjects
    else:
        cols_to_use = selected_subjects

    # ---------------- Collect all subject columns ----------------
    subject_columns = {}
    for subj in cols_to_use:
        # Include all Internal, External, Total, Result columns
        subj_cols = [c for c in df.columns if c.startswith(subj)]
        if subj_cols:
            subject_columns[subj] = subj_cols

    if not subject_columns:
        return dropdown_options, selected_subjects, html.P(
            "No columns found for the selected subjects in the uploaded data.",
            className="text-muted text-center"
        )

    # Prepare table data
    table_cols = [first_col]  # student name/id
    for cols in subject_columns.values():
        table_cols.extend(cols)

    df_table = df[table_cols].copy()

    # Ensure numeric for Internal, External, Total
    numeric_cols = [c for c in df_table.columns if any(k in c for k in ['Internal', 'External', 'Total'])]
    for col in numeric_cols:
        df_table[col] = pd.to_numeric(df_table[col], errors='coerce')

    # ---------------- Compute Overall Result based on 'Result' columns ----------------
    result_cols = [c for c in df_table.columns if 'Result' in c]

    def overall_result(row):
        relevant_results = [v for v in row[result_cols] if pd.notna(v)]
        if not relevant_results:
            return 'N/A'
        return 'Pass' if all(v == 'P' for v in relevant_results) else 'Fail'

    df_table['Overall_Result'] = df_table.apply(overall_result, axis=1)

    total_students = len(df_table)
    pass_count = (df_table['Overall_Result'] == 'Pass').sum()
    fail_count = (df_table['Overall_Result'] == 'Fail').sum()
    pass_percent = round((pass_count / total_students) * 100, 2) if total_students else 0
    fail_percent = round((fail_count / total_students) * 100, 2) if total_students else 0

    # KPI Cards
    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Pass Students", className="text-white-50"), html.H3(pass_count)]), color="success", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Fail Students", className="text-white-50"), html.H3(fail_count)]), color="danger", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Pass %", className="text-white-50"), html.H3(f"{pass_percent}%")]), color="info", inverse=True), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Fail %", className="text-white-50"), html.H3(f"{fail_percent}%")]), color="warning", inverse=True), md=3),
    ], className="g-3 mb-4")

    # ---------------- Multi-level columns for table ----------------
    columns = [{"name": first_col, "id": first_col}]
    for subj, cols in subject_columns.items():
        for col in cols:
            columns.append({"name": [subj, col.replace(subj + " ", "")], "id": col})
    columns.append({"name": ["Overall", "Result"], "id": "Overall_Result"})

    # ---------------- Conditional styling ----------------
    style_data_conditional = []
    for col in numeric_cols:
        style_data_conditional.append({
            'if': {'column_id': col, 'filter_query': f'{{{col}}} < 18'},
            'color': 'red',
            'fontWeight': 'bold'
        })
    style_data_conditional.append({
        'if': {'column_id': 'Overall_Result', 'filter_query': '{Overall_Result} = "Fail"'},
        'color': 'red',
        'fontWeight': 'bold'
    })

    # ---------------- Dash DataTable ----------------
    table = dash_table.DataTable(
        id='subject-table',
        columns=columns,
        data=df_table.to_dict('records'),
        style_data_conditional=style_data_conditional,
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        page_size=10,
        sort_action="native",
        filter_action="native"
    )

    # ---------------- Pie chart ----------------
    pie_fig = px.pie(
        names=['Pass', 'Fail'],
        values=[pass_count, fail_count],
        title="Overall Result for Selected Subjects",
        color_discrete_map={'Pass': 'green', 'Fail': 'red'}
    )
    pie_fig.update_layout(title_x=0.5, height=400)

    # ---------------- Layout ----------------
    content = dbc.Container([
        kpi_cards,
        html.H5("📋 Subject-wise Detailed Table", className="mb-3"),
        table,
        dbc.Row([dbc.Col(dcc.Graph(figure=pie_fig), md=6)])
    ], fluid=True)

    return dropdown_options, selected_subjects, content
