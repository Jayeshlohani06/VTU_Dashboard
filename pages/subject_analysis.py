# pages/subject_analysis.py

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import re

dash.register_page(__name__, path="/subject_analysis", name="Subject Analysis")

# ---------- Helper functions ----------
def extract_numeric(roll):
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges):
    roll_num = extract_numeric(roll_no)
    for sec_name, (start, end) in section_ranges.items():
        start_num = extract_numeric(start)
        end_num = extract_numeric(end)
        if start_num <= roll_num <= end_num:
            return sec_name
    return "Unassigned"

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("📊 Subject-wise Analysis", className="mb-4 text-center fw-bold"),

    # Collapsible Checklist Dropdown
    dbc.Row([
        dbc.Col([
            dbc.Button(
                "Select Subjects ▼",
                id="dropdown-toggle-btn",
                color="primary",
                n_clicks=0,
                className="mb-2 shadow-sm"
            ),
            dbc.Collapse(
                html.Div([
                    dcc.Checklist(
                        id='subject-checklist',
                        options=[],
                        value=[],
                        inputStyle={"margin-right": "10px", "margin-left": "5px"},
                        labelStyle={"display": "block"}
                    )
                ], id='subject-checklist-container', className="p-2 border rounded"),
                id="dropdown-collapse",
                is_open=False
            )
        ], md=6, xs=12)
    ], justify="center", className="mb-3"),

    # Select All / Deselect All Buttons
    dbc.Row([
        dbc.Col(
            dbc.ButtonGroup([
                dbc.Button("Select All", id="select-all-btn", color="success", className="shadow-sm"),
                dbc.Button("Deselect All", id="deselect-all-btn", color="danger", className="shadow-sm")
            ]),
            md=6, xs=12
        )
    ], justify="center", className="mb-2"),

    # Selected subjects count
    html.Div(id='selected-count', className="mb-4 text-center fw-bold text-primary"),

    # Analysis output area
    html.Div(id='subject-analysis-content'),

    # Data Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True)

# ---------- COLLAPSE TOGGLE ----------
@callback(
    Output("dropdown-collapse", "is_open"),
    Input("dropdown-toggle-btn", "n_clicks"),
    State("dropdown-collapse", "is_open")
)
def toggle_collapse(n, is_open):
    if n:
        return not is_open
    return is_open

# ---------- POPULATE CHECKLIST & SELECT ALL/DESELECT ALL ----------
@callback(
    Output('subject-checklist', 'options'),
    Output('subject-checklist', 'value'),
    Input('overview-selected-subjects', 'data'),
    Input('select-all-btn', 'n_clicks'),
    Input('deselect-all-btn', 'n_clicks'),
    State('subject-checklist', 'options')
)
def update_checklist(overview_subjects, select_all, deselect_all, current_options):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    options = [{'label': s, 'value': s} for s in overview_subjects] if overview_subjects else []
    all_subjects = [opt['value'] for opt in options]
    selected = all_subjects if overview_subjects else []
    if trigger_id == 'select-all-btn':
        selected = all_subjects
    elif trigger_id == 'deselect-all-btn':
        selected = []
    return options, selected

# ---------- MAIN CALLBACK ----------
@callback(
    [Output('selected-count', 'children'),
     Output('subject-analysis-content', 'children')],
    Input('subject-checklist', 'value'),
    State('stored-data', 'data'),
    State('section-data', 'data')
)
def update_subject_analysis(selected_subjects, json_data, section_ranges):
    if json_data is None or not selected_subjects:
        return "", html.P(
            "Please upload data and select subjects on Overview page first.",
            className="text-muted text-center"
        )

    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]

    if section_ranges and isinstance(section_ranges, dict) and len(section_ranges) > 0:
        df['Section'] = df[first_col].apply(lambda x: assign_section(str(x), section_ranges))
    else:
        df['Section'] = "Not Assigned"

    # Filter subject columns
    subject_columns = {subj: [c for c in df.columns if c.startswith(subj) and c.strip() != ''] for subj in selected_subjects}
    if not any(subject_columns.values()):
        return f"{len(selected_subjects)} subject(s) selected", html.P(
            "No columns found for selected subjects.", className="text-muted text-center"
        )

    # Prepare table
    table_cols = [first_col, 'Section'] + [col for cols in subject_columns.values() for col in cols]
    df_table = df[table_cols].copy()
    df_table[first_col] = df_table[first_col].astype(str)
    df_table = df_table.sort_values(
        by=['Section', first_col],
        key=lambda x: x.map(extract_numeric)
    ).reset_index(drop=True)

    numeric_cols = [c for c in df_table.columns if any(k in c for k in ['Internal', 'External', 'Total'])]
    for col in numeric_cols:
        df_table[col] = pd.to_numeric(df_table[col], errors='coerce')

    result_cols = [c for c in df_table.columns if 'Result' in c]
    df_table['Overall_Result'] = df_table.apply(lambda row: 'Pass' if result_cols and all(row[c] == 'P' for c in result_cols if pd.notna(row[c])) else 'Fail', axis=1)

    # KPI Metrics
    total_students = len(df_table)
    pass_count = (df_table['Overall_Result'] == 'Pass').sum()
    fail_count = (df_table['Overall_Result'] == 'Fail').sum()
    pass_percent = round((pass_count / total_students) * 100, 2) if total_students else 0
    fail_percent = round((fail_count / total_students) * 100, 2) if total_students else 0

    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Pass Students", className="text-white-50"), html.H3(pass_count)]),
                         color="success", inverse=True, className="shadow-sm p-3 rounded"), md=3, xs=6),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Fail Students", className="text-white-50"), html.H3(fail_count)]),
                         color="danger", inverse=True, className="shadow-sm p-3 rounded"), md=3, xs=6),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Pass %", className="text-white-50"), html.H3(f"{pass_percent}%")]),
                         color="info", inverse=True, className="shadow-sm p-3 rounded"), md=3, xs=6),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Fail %", className="text-white-50"), html.H3(f"{fail_percent}%")]),
                         color="warning", inverse=True, className="shadow-sm p-3 rounded"), md=3, xs=6),
    ], className="g-3 mb-4")

    # DataTable
    columns = [{"name": first_col, "id": first_col}, {"name": "Section", "id": "Section"}]
    for subj, cols in subject_columns.items():
        for col in cols:
            columns.append({"name": [subj, col.replace(subj + " ", "")], "id": col})
    columns.append({"name": ["Overall", "Result"], "id": "Overall_Result"})

    style_data_conditional = []
    for col in numeric_cols:
        style_data_conditional.append({
            'if': {'column_id': col, 'filter_query': f'{{{col}}} < 18'},
            'color': 'red', 'fontWeight': 'bold'
        })
    style_data_conditional.append({
        'if': {'column_id': 'Overall_Result', 'filter_query': '{Overall_Result} = "Fail"'},
        'color': 'red', 'fontWeight': 'bold'
    })

    table = dash_table.DataTable(
        id='subject-table',
        columns=columns,
        data=df_table.to_dict('records'),
        style_data_conditional=style_data_conditional,
        style_table={'overflowX': 'auto', 'margin': '0 auto', 'width': '95%'},
        style_cell={'textAlign': 'center', 'font-family': 'Arial', 'padding': '8px'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'},
        merge_duplicate_headers=True,
        page_size=10,
        sort_action="native",
        filter_action="native",
        style_as_list_view=False
    )

    # Pie Chart
    pie_fig = px.pie(
        names=['Pass', 'Fail'],
        values=[pass_count, fail_count],
        title="Overall Result for Selected Subjects",
        color_discrete_map={'Pass': 'green', 'Fail': 'red'}
    )
    pie_fig.update_layout(title_x=0.5, height=400)

    content = dbc.Container([
        kpi_cards,
        html.H5("📋 Subject-wise Detailed Table", className="mb-3 text-center fw-bold"),
        table,
        html.Br(),
        dbc.Row([dbc.Col(dcc.Graph(figure=pie_fig), md=6, xs=12, className="mx-auto")])
    ], fluid=True)

    return f"{len(selected_subjects)} subject(s) selected", content
