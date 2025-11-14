# pages/subject_analysis.py
# Final stable version — Added individual spinners for each content block (KPIs, Table, Chart)

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash.exceptions import PreventUpdate

dash.register_page(__name__, path="/subject_analysis", name="Subject Analysis")

# ==================== Global Styles ====================
PAGE_CSS = """
:root {
  --bg: #f5f7fb;
  --card: #ffffff;
  --primary: #1f2937;
  --brand: #3b82f6;
  --success: #10b981;
  --danger: #ef4444;
  --warning: #f59e0b;
  --shadow: 0 8px 24px rgba(16,24,40,.08);
}

.sa-wrap {
  background: var(--bg);
  padding: 18px;
  border-radius: 14px;
}

.sa-card {
  background: var(--card);
  border-radius: 14px !important;
  box-shadow: var(--shadow);
  transition: transform .2s ease, box-shadow .2s ease;
}
.sa-card:hover { transform: translateY(-1px); box-shadow: 0 12px 28px rgba(16,24,40,.12); }

.kpi-card {
  border-left: 6px solid transparent;
  border-radius: 12px;
  transition: transform .25s ease;
}
.kpi-card:hover { transform: scale(1.03); }
.kpi-label { color: #6b7280; font-size: .9rem; }
.kpi-value { font-weight: 800; font-size: 1.8rem; }

.badge {
  font-weight: 600;
  font-size: .9rem;
}

.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td,
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th {
  border-color: #e5e7eb !important;
}

/* Make dbc.Spinner flow inline with text */
.spinner-border-sm {
  width: 0.8rem;
  height: 0.8rem;
  vertical-align: -0.1em;
}
"""

# ==================== Layout ====================
layout = dbc.Container([
    dcc.Markdown(f"<style>{PAGE_CSS}</style>", dangerously_allow_html=True),

    html.Div([
        html.H3("📊 Subject-wise Performance Analysis", 
                className="text-center fw-bold mb-2 sa-title"),
        html.P("Analyze class performance across multiple subjects with interactive visuals.", 
               className="text-center text-muted mb-4")
    ], className="sa-wrap sa-card p-3 mb-3"),

    # --- Controls (with Exports included) ---
    html.Div(
        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6("Select Subjects", className="fw-bold text-muted mb-1"),
                    dcc.Dropdown(
                        id="subject-checklist",
                        options=[], value=[], multi=True,
                        placeholder="Select subjects to analyze...",
                        className="shadow-sm"
                    ),
                ], md=5),

                dbc.Col([
                    html.H6("Filter by Result", className="fw-bold text-muted mb-1"),
                    dcc.Dropdown(
                        id="result-filter",
                        options=[
                            {"label": "All Students", "value": "ALL"},
                            {"label": "Passed Only", "value": "PASS"},
                            {"label": "Failed Only", "value": "FAIL"},
                        ],
                        value="ALL", clearable=False, className="shadow-sm"
                    )
                ], md=3),

                dbc.Col([
                    html.H6("Select", className="fw-bold text-muted mb-1"),
                    dbc.ButtonGroup([
                        dbc.Button("Select All", id="select-all-btn", color="success", outline=True, className="me-1"),
                        dbc.Button("Deselect All", id="deselect-all-btn", color="danger", outline=True),
                    ], className="w-100"),
                ], md=2),

                dbc.Col([
                    html.H6("Export", className="fw-bold text-muted mb-1"),
                    dbc.ButtonGroup([
                        dbc.Button("CSV", id="sa-export-csv", color="primary", outline=True, className="me-1"),
                        dbc.Button("Excel", id="sa-export-xlsx", color="success", outline=True),
                    ], className="w-100"),
                ], md=2),
            ], className="g-3"),
            dbc.Row([
                dbc.Col(
                    # Added a small spinner for the text update
                    dbc.Spinner(
                        html.Div(id="selected-count", className="mt-2 small text-muted"),
                        size="sm",
                        color="primary"
                    )
                )
            ], className="mt-1")
        ]), className="sa-card"),
        className="sticky-top mb-4", style={"top": "10px", "zIndex": "10"}
    ),

    # --- KPIs ---
    # Wrapped in its own Loading component
    dcc.Loading(type="default", children=[
        dbc.Card(dbc.CardBody(html.Div(id="kpi-cards")), className="sa-card mb-4")
    ]),

    # --- Table ---
    # Wrapped in its own Loading component
    dcc.Loading(type="default", children=[
        dbc.Card(dbc.CardBody([
            html.H5("📋 Detailed Subject Breakdown", className="fw-bold mb-3 text-center"),
            dash_table.DataTable(
                id="subject-table",
                columns=[], data=[],
                style_table={"overflowX": "auto", "borderRadius": "10px"},
                style_cell={
                    "textAlign": "center", "padding": "8px",
                    "fontFamily": "Inter, Segoe UI, system-ui, -apple-system, Arial",
                    "fontSize": 13
                },
                style_header={
                    "backgroundColor": "#1f2937", "color": "white", "fontWeight": "700"
                },
                style_data_conditional=[
                    {"if": {"filter_query": "{Overall_Result} = 'Fail'"}, "backgroundColor": "#fee2e2"},
                    {"if": {"filter_query": "{Overall_Result} = 'Pass'"}, "backgroundColor": "#dcfce7"},
                ],
                page_size=10,
                sort_action="native",
                filter_action="native",
            ),
        ]), className="sa-card mb-4"),
    ]),

    # --- Tabs for Charts ---
    # Wrapped in its own Loading component
    dcc.Loading(type="default", children=[
        dbc.Card(dbc.CardBody([
            dcc.Tabs(id="chart-tabs", value="pie", children=[
                dcc.Tab(label="🎯 Pass vs Fail Distribution", value="pie"),
                dcc.Tab(label="📈 Subject-wise Average Marks", value="bar"),
            ]),
            html.Div(id="subject-analysis-chart", className="mt-3"),
        ]), className="sa-card mb-4"),
    ]),


    # Hidden Download components
    dcc.Download(id="sa-download-csv"),
    dcc.Download(id="sa-download-xlsx"),

    # Hidden Stores
    dcc.Store(id="stored-data", storage_type="session"),
    dcc.Store(id="overview-selected-subjects", storage_type="session"),
], fluid=True, className="pb-4")

# ==================== CALLBACKS ====================

# 1️⃣ Dropdown Control
@callback(
    Output("subject-checklist", "options", allow_duplicate=True),
    Output("subject-checklist", "value", allow_duplicate=True),
    Input("overview-selected-subjects", "data"),
    Input("select-all-btn", "n_clicks"),
    Input("deselect-all-btn", "n_clicks"),
    prevent_initial_call=True
)
def update_subject_dropdown(overview_subjects, select_all, deselect_all):
    if not overview_subjects:
        return [], []
    options = [{"label": s, "value": s} for s in overview_subjects]
    all_values = [opt["value"] for opt in options]
    ctx = dash.callback_context
    if not ctx.triggered:
        return options, all_values
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    if trigger == "select-all-btn":
        return options, all_values
    elif trigger == "deselect-all-btn":
        return options, []
    return options, all_values


# 2️⃣ Main Analysis
# This one callback updates all the components. Because each component
# is now in its own Loading wrapper, they will all get spinners.
@callback(
    Output("selected-count", "children", allow_duplicate=True),
    Output("kpi-cards", "children", allow_duplicate=True),
    Output("subject-table", "columns", allow_duplicate=True),
    Output("subject-table", "data", allow_duplicate=True),
    Output("subject-analysis-chart", "children", allow_duplicate=True),
    Input("subject-checklist", "value"),
    Input("result-filter", "value"),
    Input("chart-tabs", "value"),
    State("stored-data", "data"),
    prevent_initial_call=True
)
def update_analysis(selected_subjects, result_filter, chart_tab, json_data):
    if not json_data:
        raise PreventUpdate
    if not selected_subjects:
        return "0 subjects selected", html.P("Please select at least one subject.", className="text-muted text-center"), [], [], html.Div()

    df = pd.read_json(json_data, orient="split")
    first_col = df.columns[0]
    if "Name" not in df.columns:
        df["Name"] = ""

    selected_cols = []
    for subj in selected_subjects:
        selected_cols.extend([c for c in df.columns if c.startswith(f"{subj} ")])
    selected_cols = list(dict.fromkeys(selected_cols))

    df_sel = df[[first_col, "Name"] + selected_cols].copy()
    num_cols = [c for c in df_sel.columns if any(k in c for k in ["Internal", "External", "Total"])]
    for c in num_cols:
        df_sel[c] = pd.to_numeric(df_sel[c], errors="coerce").fillna(0)

    result_cols = [c for c in df_sel.columns if "Result" in c]
    if result_cols:
        df_sel["Overall_Result"] = df_sel[result_cols].apply(
            lambda x: "Pass" if all(str(v).strip().upper() == "P" for v in x if pd.notna(v)) else "Fail", axis=1
        )
    else:
        df_sel["Overall_Result"] = "Pass"

    if result_filter == "PASS":
        df_sel = df_sel[df_sel["Overall_Result"] == "Pass"]
    elif result_filter == "FAIL":
        df_sel = df_sel[df_sel["Overall_Result"] == "Fail"]

    total = len(df_sel)
    passed = (df_sel["Overall_Result"] == "Pass").sum()
    failed = (df_sel["Overall_Result"] == "Fail").sum()
    pass_pct = round((passed / total) * 100, 2) if total else 0

    # Dynamically build KPI list based on filter
    if result_filter == "ALL":
        kpis = [
            {"label": "Total Students", "icon": "bi-people-fill", "value": total, "color": "#3b82f6"},
            {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed, "color": "#10b981"},
            {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed, "color": "#ef4444"},
            {"label": "Pass %", "icon": "bi-graph-up", "value": f"{pass_pct}%", "color": "#f59e0b"},
        ]
        col_md = 3 # 4 cards
    elif result_filter == "PASS":
        kpis = [
            {"label": "Total (in view)", "icon": "bi-people-fill", "value": total, "color": "#3b82f6"},
            {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed, "color": "#10b981"},
        ]
        col_md = 6 # 2 cards
    else:  # result_filter == "FAIL"
        kpis = [
            {"label": "Total (in view)", "icon": "bi-people-fill", "value": total, "color": "#3b82f6"},
            {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed, "color": "#ef4444"},
        ]
        col_md = 6 # 2 cards

    cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.I(className=f"bi {k['icon']} me-2", style={"color": k["color"], "fontSize": "1.4rem"}),
            html.Span(k["label"], className="kpi-label"),
            html.Div(str(k["value"]), className="kpi-value text-center", style={"color": k["color"]})
        ]), className="kpi-card", style={"borderLeftColor": k["color"], "backgroundColor": "#fff"}), 
        md=col_md, xs=6)
        for k in kpis
    ], className="g-3")

    # Table
    columns_for_table = [{"name": [c.split(" ")[0], " ".join(c.split(" ")[1:])], "id": c} for c in selected_cols]
    columns_for_table.insert(0, {"name": ["Student", "Name"], "id": "Name"})
    columns_for_table.insert(0, {"name": ["Student", "ID"], "id": first_col})
    columns_for_table.append({"name": ["Overall", "Result"], "id": "Overall_Result"})
    data = df_sel.to_dict("records")

    # Charts
    if chart_tab == "pie":
        fig = px.pie(
            values=[passed, failed],
            names=["Pass", "Fail"],
            color=["Pass", "Fail"],
            color_discrete_map={"Pass": "#10b981", "Fail": "#ef4444"},
            hole=0.4
        )
        fig.update_layout(title="Pass vs Fail Distribution", title_x=0.5, template="plotly_white")
        chart = dcc.Graph(figure=fig)
    else:
        avg_marks = {subj: df_sel[[c for c in selected_cols if subj in c and "Total" in c]].mean(axis=1).mean()
                     for subj in selected_subjects}
        bar_fig = px.bar(x=list(avg_marks.keys()), y=list(avg_marks.values()),
                         text=[f"{v:.1f}" for v in avg_marks.values()],
                         color=list(avg_marks.keys()), color_discrete_sequence=px.colors.qualitative.Plotly)
        bar_fig.update_traces(textposition="outside")
        bar_fig.update_layout(title="Average Total Marks per Subject", title_x=0.5, template="plotly_white",
                              yaxis_title="Average Marks", xaxis_title="Subject")
        chart = dcc.Graph(figure=bar_fig)

    return f"{len(selected_subjects)} subjects selected", cards, columns_for_table, data, chart


# 3️⃣ Export Callbacks
@callback(
    Output("sa-download-csv", "data"),
    Input("sa-export-csv", "n_clicks"),
    State('subject-table', 'data'),
    State('subject-table', 'columns'),
    prevent_initial_call=True
)
def export_csv(n, table_data, table_columns):
    """Export the visible table to CSV."""
    if not table_data:
        return no_update
    
    df = pd.DataFrame(table_data)
    
    # Create simple, single-row headers for CSV
    flat_headers = []
    for col in table_columns:
        if isinstance(col['name'], list):
            flat_headers.append(" ".join(col['name']))
        else:
            flat_headers.append(col['name'])
    
    df.columns = flat_headers
    
    return dcc.send_data_frame(df.to_csv, "subject_analysis.csv", index=False)

@callback(
    Output("sa-download-xlsx", "data"),
    Input("sa-export-xlsx", "n_clicks"),
    State('subject-table', 'data'),
    State('subject-table', 'columns'),
    prevent_initial_call=True
)
def export_xlsx(n, table_data, table_columns):
    """Export the visible table to Excel."""
    if not table_data:
        return no_update
        
    df = pd.DataFrame(table_data)
    
    flat_headers = []
    for col in table_columns:
        if isinstance(col['name'], list):
            flat_headers.append(" ".join(col['name']))
        else:
            flat_headers.append(col['name'])
            
    df.columns = flat_headers

    return dcc.send_data_frame(df.to_excel, "subject_analysis.xlsx", sheet_name="Subject Analysis", index=False)