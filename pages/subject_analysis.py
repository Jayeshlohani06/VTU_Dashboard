# pages/subject_analysis.py
# Final stable version — Fixed DuplicateCallback error with 'initial_duplicate'
# Updated: Custom Graph Tooltip + StringIO Fix

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash.exceptions import PreventUpdate
from io import StringIO  # <--- Added for stability

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

/* Dropdown Styling for Visibility */
.VirtualizedSelectOption {
  color: #1f2937 !important;
  background-color: #ffffff !important;
  padding: 10px !important;
}

.VirtualizedSelectOption:hover {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
}

.VirtualizedSelectOption.isSelected {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
}

/* Dash Dropdown */
.Select--multi .Select-value {
  background-color: #3b82f6 !important;
  border-color: #3b82f6 !important;
  color: #ffffff !important;
}

.Select {
  position: relative !important;
  z-index: 100 !important;
}

.Select-control {
  background-color: #ffffff !important;
  border-color: #d1d5db !important;
  border-width: 1px !important;
  border-radius: 6px !important;
  position: relative !important;
  z-index: 100 !important;
}

.Select-control.is-focused {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

.Select-menu-outer {
  background-color: #ffffff !important;
  border-color: #d1d5db !important;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3) !important;
  display: block !important;
  z-index: 10000 !important;
  position: absolute !important;
  top: 100% !important;
  left: 0 !important;
  right: 0 !important;
  width: 100% !important;
  border-top: none !important;
  pointer-events: auto !important;
  visibility: visible !important;
  opacity: 1 !important;
  max-height: 400px !important;
  overflow-y: auto !important;
}

.Select-menu {
  max-height: 300px !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  display: block !important;
  visibility: visible !important;
}

.Select-option {
  color: #1f2937 !important;
  background-color: #ffffff !important;
  padding: 12px 15px !important;
  font-size: 14px !important;
  cursor: pointer !important;
  border: none !important;
  pointer-events: auto !important;
  display: block !important;
  visibility: visible !important;
}

.Select-option:hover {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
}

.Select-option.is-focused {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
}

.Select-option.is-selected {
  background-color: #3b82f6 !important;
  color: #ffffff !important;
}

.Select-input input {
  color: #1f2937 !important;
  font-weight: 500 !important;
}

/* Make sure dropdown container doesn't clip menu */
.Dropdown {
  position: relative !important;
  z-index: 100 !important;
}

#subject-checklist, #result-filter {
  position: relative !important;
}

/* Ensure dropdown components are always visible and clickable */
.Select-wrapper {
  overflow: visible !important;
  z-index: 100 !important;
}

.react-select__menu-portal {
  z-index: 10001 !important;
  position: fixed !important;
}

/* Override any Bootstrap container overflow */
.pb-4 {
  overflow: visible !important;
}

/* Additional selectors for dropdown menu in case of different Dash versions */
.Select-menu,
.Select-options,
[class*="Select"] [class*="menu"] {
  z-index: 10000 !important;
  display: block !important;
  visibility: visible !important;
}

/* Force dropdown to be visible even if hidden by default */
div[class*="Select-menu"] {
  display: block !important;
  visibility: visible !important;
  pointer-events: auto !important;
  z-index: 10000 !important;
}

/* React-Select compatibility */
.react-select__menu {
  z-index: 10000 !important;
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
                    html.Div([
                        dcc.Dropdown(
                            id="subject-checklist",
                            options=[], value=[], multi=True,
                            placeholder="Select subjects to analyze...",
                            className="shadow-sm custom-dropdown",
                            searchable=True,
                            clearable=True,
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "color": "#1f2937", 
                                "fontWeight": "500", 
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"overflow": "visible", "position": "relative", "zIndex": "1000"}),
                    html.Div(style={"height": "15px"}),
                ], md=5),

                dbc.Col([
                    html.H6("Filter by Result", className="fw-bold text-muted mb-1"),
                    html.Div([
                        dcc.Dropdown(
                            id="result-filter",
                            options=[
                                {"label": "All Students", "value": "ALL"},
                                {"label": "Passed Only", "value": "PASS"},
                                {"label": "Failed Only", "value": "FAIL"},
                                {"label": "Absent Only", "value": "ABSENT"},
                            ],
                            value="ALL", clearable=False, className="shadow-sm custom-dropdown",
                            searchable=True,
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "color": "#1f2937", 
                                "fontWeight": "500", 
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"overflow": "visible", "position": "relative", "zIndex": "1000"}),
                    html.Div(style={"height": "15px"}),
                ], md=3),

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
        ], style={"overflow": "visible", "position": "relative"}), className="sa-card", style={"overflow": "visible", "position": "relative"}),
        className="mb-4", style={"overflow": "visible", "position": "relative", "zIndex": "100"}
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
                    {"if": {"filter_query": "{Overall_Result} = 'Fail'"}, "backgroundColor": "#fee2e2", "color": "#991b1b", "fontWeight": "600"},
                    {"if": {"filter_query": "{Overall_Result} = 'Pass'"}, "backgroundColor": "#dcfce7", "color": "#065f46", "fontWeight": "600"},
                    {"if": {"filter_query": "{Overall_Result} = 'Absent'"}, "backgroundColor": "#fed7aa", "color": "#92400e", "fontWeight": "700"},
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

    # Use session stores to match global app.py stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True, className="pb-4")

# ==================== CALLBACKS ====================

# 1️⃣ Dropdown Control
@callback(
    Output("subject-checklist", "options", allow_duplicate=True),
    Output("subject-checklist", "value", allow_duplicate=True),
    Input("overview-selected-subjects", "data"),
    Input("subject-checklist", "value"),
    prevent_initial_call='initial_duplicate'
)
def update_subject_dropdown(overview_subjects, current_value):
    if not overview_subjects:
        return [], []
    
    # Add "Select All" and "Remove All" options at the top
    options = [
        {"label": "✓ Select All", "value": "__SELECT_ALL__"},
        {"label": "✕ Remove All", "value": "__REMOVE_ALL__"}
    ] + [{"label": s, "value": s} for s in overview_subjects]
    all_subject_values = [opt["value"] for opt in options[2:]]  # Exclude the special markers
    
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "INITIAL_LOAD"

    if trigger == "subject-checklist":
        # If "Select All" is clicked, select all subjects
        if current_value and "__SELECT_ALL__" in current_value:
            return options, all_subject_values
        # If "Remove All" is clicked, clear all
        elif current_value and "__REMOVE_ALL__" in current_value:
            return options, []
        # Remove special markers if user manually selects other subjects
        filtered_value = [v for v in (current_value or []) if not v.startswith("__")]
        return options, filtered_value
    
    return options, all_subject_values


# 2️⃣ Main Analysis
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
    prevent_initial_call='initial_duplicate'  # <-- FIX IS HERE
)
def update_analysis(selected_subjects, result_filter, chart_tab, json_data):
    if not json_data:
        raise PreventUpdate
    
    # Remove the special markers if present
    selected_subjects = [s for s in (selected_subjects or []) if not s.startswith("__")]
    
    if not selected_subjects:
        return "0 subjects selected", html.P("Please select at least one subject.", className="text-muted text-center"), [], [], html.Div()

    # FIX: Use StringIO for safe reading
    df = pd.read_json(StringIO(json_data), orient="split")
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
        df_sel[c] = pd.to_numeric(df_sel[c], errors="coerce")

    result_cols = [c for c in df_sel.columns if "Result" in c]
    if result_cols:
        # Detect Absent ("A"), Pass ("P"), and Fail ("F")
        def determine_result(x):
            vals = [str(v).strip().upper() for v in x if pd.notna(v)]
            if "A" in vals:
                return "Absent"
            elif all(v == "P" for v in vals):
                return "Pass"
            else:
                return "Fail"
        
        df_sel["Overall_Result"] = df_sel[result_cols].apply(determine_result, axis=1)
    else:
        df_sel["Overall_Result"] = "Pass"

    # Count Absent, Appeared, Passed, Failed (before filtering)
    total_students = len(df_sel)
    absent = (df_sel["Overall_Result"] == "Absent").sum()
    appeared = total_students - absent
    passed = (df_sel["Overall_Result"] == "Pass").sum()
    failed = (df_sel["Overall_Result"] == "Fail").sum()
    pass_pct_appeared = round((passed / appeared) * 100, 2) if appeared > 0 else 0

    # Apply result filter
    if result_filter == "PASS":
        df_sel = df_sel[df_sel["Overall_Result"] == "Pass"]
    elif result_filter == "FAIL":
        df_sel = df_sel[df_sel["Overall_Result"] == "Fail"]
    elif result_filter == "ABSENT":
        df_sel = df_sel[df_sel["Overall_Result"] == "Absent"]
    # For "ALL" filter, keep all rows including Absent

    total = len(df_sel)
    passed_filtered = (df_sel["Overall_Result"] == "Pass").sum()
    failed_filtered = (df_sel["Overall_Result"] == "Fail").sum()
    absent_filtered = (df_sel["Overall_Result"] == "Absent").sum()

    # Dynamically build KPI list based on filter
    if result_filter == "ALL":
        kpis = [
            {"label": "Total Students", "icon": "bi-people-fill", "value": total, "color": "#3b82f6"},
            {"label": "Appeared", "icon": "bi-person-check-fill", "value": appeared, "color": "#10b981"},
            {"label": "Absent", "icon": "bi-person-x-fill", "value": absent, "color": "#f59e0b"},
            {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed, "color": "#06b6d4"},
            {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed, "color": "#ef4444"},
            {"label": "Pass % (Appeared)", "icon": "bi-graph-up", "value": f"{pass_pct_appeared}%", "color": "#8b5cf6"},
        ]
        col_md = 2  # 6 cards
    elif result_filter == "PASS":
        kpis = [
            {"label": "Total (in view)", "icon": "bi-people-fill", "value": total, "color": "#3b82f6"},
            {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed_filtered, "color": "#10b981"},
        ]
        col_md = 6  # 2 cards
    elif result_filter == "FAIL":
        kpis = [
            {"label": "Total (in view)", "icon": "bi-people-fill", "value": total, "color": "#3b82f6"},
            {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed_filtered, "color": "#ef4444"},
        ]
        col_md = 6  # 2 cards
    else:  # result_filter == "ABSENT"
        kpis = [
            {"label": "Total (in view)", "icon": "bi-people-fill", "value": total, "color": "#3b82f6"},
            {"label": "Absent", "icon": "bi-person-x-fill", "value": absent_filtered, "color": "#f59e0b"},
        ]
        col_md = 6  # 2 cards

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
        # Use df_sel for pie counts (already filtered)
        pie_pass = (df_sel["Overall_Result"] == "Pass").sum()
        pie_fail = (df_sel["Overall_Result"] == "Fail").sum()
        pie_absent = (df_sel["Overall_Result"] == "Absent").sum()
        
        # Include Absent in pie chart when showing ALL filter
        if result_filter == "ALL":
            chart_values = [pie_pass, pie_fail, pie_absent]
            chart_labels = ["Pass", "Fail", "Absent"]
            chart_colors = ["#10b981", "#ef4444", "#f59e0b"]
        elif result_filter == "ABSENT":
            # When filtering for Absent only, show a pie with just absent count
            chart_values = [pie_absent]
            chart_labels = ["Absent"]
            chart_colors = ["#f59e0b"]
        else:
            chart_values = [pie_pass, pie_fail] if result_filter == "PASS" else [pie_fail] if result_filter == "FAIL" else [pie_pass]
            chart_labels = ["Pass", "Fail"] if result_filter == "PASS" else ["Fail"] if result_filter == "FAIL" else ["Pass"]
            chart_colors = ["#10b981", "#ef4444"] if result_filter == "PASS" else ["#ef4444"] if result_filter == "FAIL" else ["#10b981"]
        
        fig = px.pie(
            values=chart_values,
            names=chart_labels,
            color=chart_labels,
            color_discrete_map={label: color for label, color in zip(chart_labels, chart_colors)},
            hole=0.4
        )
        # Fix pie chart tooltip (clean style, no label=value=color)
        fig.update_traces(
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>"
        )
        fig.update_layout(title="Pass vs Fail Distribution", title_x=0.5, template="plotly_white")
        chart = dcc.Graph(figure=fig)
    else:
        # Exclude Absent students from bar averages
        df_for_avg = df_sel[df_sel["Overall_Result"] != "Absent"].copy()
        
        # If all students are absent, show a message
        if df_for_avg.empty:
            chart = html.P("No students with marks to display. All selected students are absent.", className="text-muted text-center")
        else:
            avg_marks = {subj: df_for_avg[[c for c in selected_cols if subj in c and "Total" in c]].mean(axis=1).mean()
                         for subj in selected_subjects}
            bar_fig = px.bar(x=list(avg_marks.keys()), y=list(avg_marks.values()),
                             text=[f"{v:.1f}" for v in avg_marks.values()],
                             color=list(avg_marks.keys()), color_discrete_sequence=px.colors.qualitative.Plotly)
            
            # --- CUSTOM TOOLTIP (clean style) ---
            bar_fig.update_traces(
                textposition="outside",
                hovertemplate="<b>Subject:</b> %{x}<br><b>Avg Marks:</b> %{y:.2f}<extra></extra>"
            )
            # -----------------------------------
            
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