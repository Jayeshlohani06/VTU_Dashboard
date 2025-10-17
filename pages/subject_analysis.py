import dash
from dash import html, dcc, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

dash.register_page(__name__, path="/subject_analysis", name="Subject Analysis")

# ---------- Layout ----------
layout = dbc.Container([
    html.H2("📊 Subject-wise Performance Analysis", className="text-center mb-4 fw-bold"),

    # --- Control Panel ---
    dbc.Card(
        dbc.CardBody([
            html.H5("Select Subjects for Analysis", className="card-title"),
            dcc.Dropdown(
                id='subject-checklist',
                options=[],
                value=[],
                multi=True,
                placeholder="Select subjects to analyze...",
                className="mb-3"
            ),
            dbc.ButtonGroup([
                dbc.Button("Select All", id="select-all-btn", color="success", outline=True, className="me-2"),
                dbc.Button("Deselect All", id="deselect-all-btn", color="danger", outline=True)
            ]),
            html.Div(id='selected-count', className="mt-3 text-muted small")
        ]),
        className="shadow-sm mb-4"
    ),

    # Analysis output area
    html.Div(id='subject-analysis-content'),

    # Data Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session')
], fluid=True, className="py-4")


# ---------- POPULATE DROPDOWN & SELECT ALL/DESELECT ALL ----------
@callback(
    Output('subject-checklist', 'options'),
    Output('subject-checklist', 'value'),
    Input('overview-selected-subjects', 'data'),
    Input('select-all-btn', 'n_clicks'),
    Input('deselect-all-btn', 'n_clicks'),
    prevent_initial_call=True
)
def update_checklist(overview_subjects, select_all_clicks, deselect_all_clicks):
    if not overview_subjects:
        return [], []

    options = [{'label': s, 'value': s} for s in overview_subjects]
    all_subjects = [opt['value'] for opt in options]

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'overview-selected-subjects'

    if trigger_id == 'select-all-btn':
        return options, all_subjects
    elif trigger_id == 'deselect-all-btn':
        return options, []
    
    # Default to selecting all when data first loads
    return options, all_subjects

# ---------- MAIN CALLBACK ----------
@callback(
    Output('selected-count', 'children'),
    Output('subject-analysis-content', 'children'),
    Input('subject-checklist', 'value'),
    State('stored-data', 'data')
)
def update_subject_analysis(selected_subjects, json_data):
    """Update KPIs, table, and chart based on subject selection."""
    if not json_data:
        return "", html.P("Please upload data on the Overview page first.", className="text-muted text-center mt-4")
    if not selected_subjects:
        return "0 subjects selected", html.P("Please select at least one subject to view the analysis.", className="text-muted text-center mt-4")

    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]
    if 'Name' not in df.columns: df['Name'] = ""

    # Filter subject columns based on selection
    all_selected_cols = []
    for subj_code in selected_subjects:
        # Ensure we only get columns starting with the exact subject code + a space
        all_selected_cols.extend([col for col in df.columns if col.startswith(f"{subj_code} ")])
    
    # Remove duplicates if any
    all_selected_cols = sorted(list(set(all_selected_cols)))
    
    df_filtered = df[[first_col, 'Name'] + all_selected_cols].copy()
    
    numeric_cols = [c for c in df_filtered.columns if any(k in c for k in ['Internal', 'External', 'Total'])]
    for col in numeric_cols:
        df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')

    # Compute Overall Result for the selection
    result_cols = [c for c in df_filtered.columns if 'Result' in c]
    if result_cols:
      df_filtered['Overall_Result'] = df_filtered.apply(lambda row: 'Pass' if all(row[c] == 'P' for c in result_cols if pd.notna(row[c])) else 'Fail', axis=1)
    else: # Fallback if no result columns are present
        total_cols = [c for c in df_filtered.columns if 'Total' in c]
        df_filtered['Overall_Result'] = df_filtered.apply(lambda row: 'Fail' if any(0 < row[c] < 35 for c in total_cols) else 'Pass', axis=1)

    # --- KPI Metrics ---
    total_students = len(df_filtered)
    pass_count = (df_filtered['Overall_Result'] == 'Pass').sum()
    fail_count = total_students - pass_count
    pass_percent = (pass_count / total_students * 100) if total_students > 0 else 0
    fail_percent = (fail_count / total_students * 100) if total_students > 0 else 0

    # --- KPI Cards ---
    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Passed Students", className="text-muted"), html.H2(f"✅ {pass_count}", className="fw-bold text-success")])), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Failed Students", className="text-muted"), html.H2(f"❌ {fail_count}", className="fw-bold text-danger")])), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Pass Percentage", className="text-muted"), html.H2(f"{pass_percent:.2f}%", className="fw-bold text-primary")])), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Fail Percentage", className="text-muted"), html.H2(f"{fail_percent:.2f}%", className="fw-bold text-warning")])), md=3),
    ], className="g-3 mb-4")

    # --- DataTable with improved styling ---
    columns = [{"name": [c.split(' ')[0], ' '.join(c.split(' ')[1:])], "id": c} for c in all_selected_cols]
    columns.insert(0, {"name": ["Student", "Name"], "id": "Name"})
    columns.insert(0, {"name": ["Student", "ID"], "id": first_col})
    columns.append({"name": ["Overall", "Result"], "id": "Overall_Result"})

    table = dash_table.DataTable(
        id='subject-table',
        columns=columns,
        data=df_filtered.to_dict('records'),
        style_table={'borderRadius': '8px', 'overflowX': 'auto'}, # CORRECTED HERE
        style_header={'backgroundColor': '#343a40', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'},
        style_cell={'textAlign': 'center', 'padding': '10px', 'fontFamily': 'sans-serif'},
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'},
            {'if': {'filter_query': '{Overall_Result} = "Fail"', 'column_id': 'Overall_Result'}, 'backgroundColor': '#f8d7da', 'color': '#721c24'},
            {'if': {'filter_query': '{Overall_Result} = "Pass"', 'column_id': 'Overall_Result'}, 'backgroundColor': '#d4edda', 'color': '#155724'},
        ],
        merge_duplicate_headers=True,
        page_size=10,
        sort_action="native",
        filter_action="native",
    )

    # --- Pie Chart ---
    pie_fig = go.Figure(data=[go.Pie(
        labels=['Pass', 'Fail'],
        values=[pass_count, fail_count],
        marker=dict(colors=['#28a745', '#dc3545']),
        hole=0.4,
        textinfo='percent+label'
    )])
    pie_fig.update_layout(
        title_text="Overall Result Distribution",
        title_x=0.5,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # --- Assemble final layout ---
    content = dbc.Card(
        dbc.CardBody([
            kpi_cards,
            html.Hr(),
            html.H5("📋 Detailed Subject Breakdown", className="mb-3 text-center"),
            table,
            html.Hr(className="my-4"),
            dbc.Row(dbc.Col(dcc.Graph(figure=pie_fig), md=8), justify="center")
        ]),
        className="shadow-sm mt-4"
    )

    return f"{len(selected_subjects)} subjects selected", content

