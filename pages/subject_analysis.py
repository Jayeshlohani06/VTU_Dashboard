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

/* UNIVERSAL BOX SIZING FIX FOR DROPDOWN */
.Select, .Select div, .Select input, .Select span {
  box-sizing: border-box !important;
}

/* Dropdown Styling for Visibility */
.VirtualizedSelectOption {
  color: #1f2937 !important;
  background-color: #ffffff !important;
  padding: 10px !important;
  white-space: nowrap !important; /* Prevent line breaks violating bounds */
  text-overflow: ellipsis !important; /* Handle long text gracefully */
  overflow: hidden !important;
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

/* Force Select wrapper to fill container */
.Select {
  position: relative !important;
  z-index: 100 !important;
  width: 100% !important; /* Ensure the anchor is full width */
  box-sizing: border-box !important;
}

.Select-control, .Select-multi-value-wrapper, div[class*="-control"] {
  background-color: #ffffff !important;
  border-color: #d1d5db !important;
  border-width: 1px !important;
  border-radius: 6px !important;
  position: relative !important;
  z-index: 100 !important;
  width: 100% !important; /* Ensure control matches anchor */
  box-sizing: border-box !important;
  height: auto !important; /* Allow wrapping */
  min-height: 45px !important;
  display: flex !important;
  align-items: center !important;
  flex-wrap: wrap !important;
}

.Select-control.is-focused {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
}

.Select-menu-outer {
  background-color: #ffffff !important;
  border: 1px solid #d1d5db !important;
  border-top: none !important;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
  display: block !important;
  z-index: 9999 !important;
  position: absolute !important;
  
  /* STRICT ALIGNMENT FIX */
  top: 100% !important;
  left: 0 !important;
  right: 0 !important;
  width: auto !important; /* Let left/right dictate width */
  margin: 0 !important; /* Reset margins that push it out */
  margin-top: -1px !important; /* Overlap border */
  
  box-sizing: border-box !important;
  border-bottom-left-radius: 6px !important;
  border-bottom-right-radius: 6px !important;
  max-height: 300px !important;
  min-width: 0 !important; /* Prevent content-based expansion */
  max-width: 100% !important; /* Strictly enforce parent boundary */
  overflow-y: auto !important;
  overflow-x: hidden !important;
}

/* Fix rounding when open to make it look attached */
.Select.is-open > .Select-control {
  border-bottom-left-radius: 0 !important;
  border-bottom-right-radius: 0 !important;
  border-color: #d1d5db !important;
}

.Select-menu {
  /* Disable inner scroll to prevent double scrollbars */
  max-height: none !important; 
  overflow-y: visible !important;
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
                    ], style={"position": "relative", "zIndex": "1000"}),
                    html.Div(style={"height": "15px"}),
                ], md=4, style={"position": "relative", "zIndex": "1060", "overflow": "visible"}), # Added explicit calc props

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
                    ], style={"position": "relative", "zIndex": "1000"}),
                    html.Div(style={"height": "15px"}),
                ], md=3, style={"position": "relative", "zIndex": "1050", "overflow": "visible"}),

                dbc.Col([
                    html.H6("Actions", className="fw-bold text-muted mb-1"),
                    dbc.ButtonGroup([
                        dbc.Button("CSV", id="sa-export-csv", color="primary", outline=True, className="me-1"),
                        dbc.Button("Excel", id="sa-export-xlsx", color="success", outline=True, className="me-1"),
                        dbc.Button("ℹ️", id="sa-open-legend", color="info", outline=True),
                    ], className="w-100"),
                ], md=3), 
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
        className="mb-4", style={"overflow": "visible", "position": "relative", "zIndex": "1050"}
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
                style_table={
                    "overflowX": "auto", 
                    "borderRadius": "8px", 
                    "border": "1px solid #d1d5db",
                    "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
                },
                style_cell={
                    "textAlign": "center", 
                    "padding": "12px",
                    "fontFamily": "Inter, Segoe UI, system-ui, -apple-system, Arial",
                    "fontSize": "13px",
                    "color": "#1f2937",
                    "border": "1px solid #e5e7eb"
                },
                style_header={
                    "backgroundColor": "#1f2937", 
                    "color": "#ffffff",
                    "fontWeight": "700",
                    "textTransform": "uppercase",
                    "fontSize": "12px",
                    "letterSpacing": "0.5px",
                    "borderBottom": "2px solid #111827"
                },
                style_data={
                    "whiteSpace": "normal",
                    "height": "auto",
                    "backgroundColor": "#ffffff"
                },
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f3f4f6'},
                    {"if": {"state": "selected"}, "backgroundColor": "rgba(59, 130, 246, 0.1)", "border": "1px solid #3b82f6"},
                    
                    # Result coloring
                    {"if": {"filter_query": "{Overall_Result} = 'Fail'"}, "backgroundColor": "#fef2f2", "color": "#dc2626", "fontWeight": "700"},
                    {"if": {"filter_query": "{Overall_Result} = 'Pass'"}, "backgroundColor": "#ecfdf5", "color": "#059669", "fontWeight": "700"},
                    {"if": {"filter_query": "{Overall_Result} = 'Absent'"}, "backgroundColor": "#fff7ed", "color": "#d97706", "fontWeight": "700"},
                ],
                page_size=10,
                sort_action="native",
                filter_action="native",
            ),
        ]), className="sa-card mb-4"),
    ]),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("📊 Analysis Logic & Legends")),
        dbc.ModalBody(
            html.Div([
                html.H6("📝 Student Status Logic", className="text-primary fw-bold"),
                html.Ul([
                    html.Li([html.Strong("Pass:"), " Student has passed in ALL selected subjects."]),
                    html.Li([html.Strong("Fail:"), " Student has failed or is absent in AT LEAST ONE selected subject."]),
                    html.Li([html.Strong("Absent:"), " Student is absent in ALL selected subjects."]),
                ]),
                html.Hr(),
                html.H6("📚 Subject Status Logic", className="text-primary fw-bold"),
                html.Ul([
                    html.Li([html.Strong("Based on Result Column:"), " The dashboard uses the 'Result' column (P/F/A) from the uploaded data."]),
                    html.Li([html.Strong("P / Pass:"), " Considered as Passed."]),
                    html.Li([html.Strong("F / Fail:"), " Considered as Failed."]),
                    html.Li([html.Strong("A / Absent:"), " Considered as Absent."]), 
                ]),
                html.Div(
                    dbc.Alert("Note: This page focuses on subject-wise performance. For SGPA/ranks and Class Categories (FCD, FC, etc.), please visit the Ranking page.", color="info", className="mt-3 small")
                )
            ])
        ),
        dbc.ModalFooter(dbc.Button("Got it!", id="sa-close-legend", className="ms-auto", color="primary"))
    ], id="sa-legend-modal", is_open=False, size="lg", style={"zIndex": 10000}),

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
        # Logic: 
        # - Fail if ANY 'F'
        # - Fail if 'A' exists but not ALL are 'A' (Absent in 1 = Fail)
        # - Absent only if ALL are 'A'
        # - Pass otherwise
        def determine_result(x):
            vals = [str(v).strip().upper() for v in x if pd.notna(v) and str(v).strip() != ""]
            
            # If student has NO data for any selected subject, mark as NA (to filter out)
            if not vals:
                return "NA"

            has_fail = any(v in ["F", "FAIL"] for v in vals)
            has_absent = any(v in ["A", "ABSENT"] for v in vals)
            all_absent = all(v in ["A", "ABSENT"] for v in vals)

            if has_fail:
                return "Fail"
            elif has_absent:
                # If absent in all, then Absent. If absent in some (and passed others), then Fail.
                return "Absent" if all_absent else "Fail"
            else:
                return "Pass"
        
        df_sel["Overall_Result"] = df_sel[result_cols].apply(determine_result, axis=1)
        
        # Filter out students who aren't taking ANY of the selected subjects (Result = NA)
        df_sel = df_sel[df_sel["Overall_Result"] != "NA"]
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
            {"id": "total", "label": "Total Students", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "appeared", "label": "Appeared", "value": appeared, "color": "#10b981", "bg": "#ecfdf5", "icon": "bi-person-circle"},
            {"id": "absent", "label": "Absent", "value": absent, "color": "#f59e0b", "bg": "#fffbeb", "icon": "bi-person-slash"},
            {"id": "pass", "label": "Passed", "value": passed, "color": "#0ea5e9", "bg": "#f0f9ff", "icon": "bi-check-lg"},
            {"id": "fail", "label": "Failed", "value": failed, "color": "#ef4444", "bg": "#fef2f2", "icon": "bi-x-lg"},
            {"id": "rate", "label": "Pass % (Appeared)", "value": f"{pass_pct_appeared}%", "color": "#8b5cf6", "bg": "#f5f3ff", "icon": "bi-percent"},
        ]
        col_class = "row-cols-2 row-cols-md-3 row-cols-lg-6 g-3"
    elif result_filter == "PASS":
        kpis = [
            {"id": "total", "label": "Total (in view)", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "pass", "label": "Passed", "value": passed_filtered, "color": "#10b981", "bg": "#ecfdf5", "icon": "bi-check-lg"},
        ]
        col_class = "row-cols-2 row-cols-md-6 g-3"
    elif result_filter == "FAIL":
        kpis = [
            {"id": "total", "label": "Total (in view)", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "fail", "label": "Failed", "value": failed_filtered, "color": "#ef4444", "bg": "#fef2f2", "icon": "bi-x-lg"},
        ]
        col_class = "row-cols-2 row-cols-md-6 g-3"
    else:  # ABSENT
        kpis = [
            {"id": "total", "label": "Total (in view)", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "absent", "label": "Absent", "value": absent_filtered, "color": "#f59e0b", "bg": "#fffbeb", "icon": "bi-person-slash"},
        ]
        col_class = "row-cols-2 row-cols-md-6 g-3"

    # =========================================================================
    # SUBJECT-WISE BREAKDOWN (Handle Absent Logic Correctly)
    # =========================================================================
    
    # 1. Subject-wise Analysis Data Structure
    subject_stats = []
    
    for subj in selected_subjects:
        # Robust column lookup: Find the actual column names in df_sel
        # This prevents issues where 'BNSK559 Result' (constructed) doesn't match 'BNSK559  Result' (actual with double space)
        # resulting in fallback or missing data. Use df_sel to ensure consistency with KPIs.
        subj_cols = [c for c in df_sel.columns if c.startswith(subj)]
        
        res_col = next((c for c in subj_cols if "Result" in c), None)
        int_col = next((c for c in subj_cols if "Internal" in c), None)
        ext_col = next((c for c in subj_cols if "External" in c), None)
        tot_col = next((c for c in subj_cols if "Total" in c), None)

        if not res_col:
            continue
            
        cols_to_fetch = [first_col, "Name", res_col]
        if int_col: cols_to_fetch.append(int_col)
        if ext_col: cols_to_fetch.append(ext_col)
        if tot_col: cols_to_fetch.append(tot_col)
        
        # Use filtered dataset
        subj_df = df_sel[cols_to_fetch].copy()

        # --- LOGIC: Validate entries for this subject ---
        # Ensure we only count students who have a valid entry for this subject
        # Drop rows where Result is NaN/None/Empty (Student didn't take this subject)
        subj_df = subj_df[subj_df[res_col].notna()]
        subj_df = subj_df[subj_df[res_col].astype(str).str.strip() != ""]

        if subj_df.empty:
            subject_stats.append({
                "Subject": subj,
                "Total Students": 0, "Appeared": 0, "Absent": 0, "Passed": 0, "Failed": 0, "Pass %": 0
            })
            continue

        # Standardize Result
        subj_df[res_col] = subj_df[res_col].astype(str).str.strip().str.upper()
        
        # Identify Status
        def get_subj_status(row):
            r = row[res_col]
            e = row[ext_col] if ext_col else 0 
            
            try:
                e_val = float(e)
            except:
                e_val = 0
            
            if r in ['A', 'ABSENT'] and e_val == 0:
                return 'Absent'
            elif r in ['F', 'FAIL']:
                return 'Fail'
            elif r in ['P', 'PASS']:
                return 'Pass'
            else:
                if r in ['A', 'ABSENT']: return 'Absent'
                return 'Ignore' 
        
        if ext_col:
            subj_df[ext_col] = pd.to_numeric(subj_df[ext_col], errors='coerce').fillna(0)
        
        subj_df['Status'] = subj_df.apply(get_subj_status, axis=1)
        
        # Filter invalid statuses
        subj_df = subj_df[subj_df['Status'] != 'Ignore']

        # Stats
        s_total = len(subj_df)
        s_absent = (subj_df['Status'] == 'Absent').sum()
        s_appeared = s_total - s_absent
        s_passed = (subj_df['Status'] == 'Pass').sum()
        s_failed = (subj_df['Status'] == 'Fail').sum()
        s_pass_pct = round((s_passed / s_appeared) * 100, 2) if s_appeared > 0 else 0
        
        subject_stats.append({
            "Subject": subj,
            "Total Students": s_total,
            "Appeared": s_appeared,
            "Absent": s_absent,
            "Passed": s_passed,
            "Failed": s_failed,
            "Pass %": s_pass_pct
        })
        
    subject_summary_df = pd.DataFrame(subject_stats)
    
    # If no subjects selected or found
    if subject_summary_df.empty:
        summary_card = html.Div(html.P("No subject data found.", className="text-muted"))
    else:
        # Create a Summary Table for Subject-wise stats
        summary_card = dbc.Card(dbc.CardBody([
            html.H5("📚 Subject Level Performance", className="fw-bold mb-3 text-primary"),
            dash_table.DataTable(
                data=subject_summary_df.to_dict('records'),
                columns=[{"name": i, "id": i} for i in subject_summary_df.columns],
                style_table={"overflowX": "auto", "borderRadius": "8px", "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)"},
                style_header={
                    "backgroundColor": "#1f2937",
                    "fontWeight": "700",
                    "color": "#ffffff",
                    "borderBottom": "2px solid #111827",
                    "padding": "12px",
                    "textTransform": "uppercase",
                    "fontSize": "12px",
                    "letterSpacing": "0.5px"
                },
                style_cell={
                    "textAlign": "center", 
                    "padding": "12px", 
                    "fontFamily": "Inter, sans-serif",
                    "fontSize": "14px",
                    "border": "1px solid #e2e8f0",
                    "color": "#1e293b"
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f3f4f6'
                    },
                    {
                        "if": {"state": "selected"},
                        "backgroundColor": "rgba(59, 130, 246, 0.1)",
                        "border": "1px solid #3b82f6"
                    },
                    # Add simple conditional formatting for Pass %
                    {
                        "if": {
                            "filter_query": "{Pass %} >= 50",
                            "column_id": "Pass %"
                        },
                        "color": "#059669",
                        "fontWeight": "bold"
                    },
                    {
                        "if": {
                            "filter_query": "{Pass %} < 50",
                            "column_id": "Pass %"
                        },
                        "color": "#dc2626",
                        "fontWeight": "bold"
                    }
                ],
                sort_action="native"
            )
        ]), className="sa-card mb-4")

    cards = html.Div([
        dbc.Row([
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([
                        html.Div([
                            html.Div(
                                html.I(className=f"bi {k['icon']}", style={"color": k["color"], "fontSize": "1.4rem"}),
                                className="d-flex align-items-center justify-content-center",
                                style={"minWidth": "42px", "width": "42px", "height": "42px", "borderRadius": "10px", "backgroundColor": k["bg"]}
                            ),
                            html.Div([
                                html.H6(k["label"], className="text-muted text-uppercase fw-bold mb-0", style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                                html.H3(str(k["value"]), className="fw-bold mb-0", style={"color": k["color"], "fontSize": "1.6rem"})
                            ], className="ms-3")
                        ], className="d-flex align-items-center h-100")
                    ], className="p-3"),
                    className="kpi-card shadow-sm h-100 border-0",
                    style={"borderLeft": f"4px solid {k['color']}", "transition": "transform 0.2s ease-in-out"}
                )
            )
            for k in kpis
        ], className=col_class),
        
        # INSERT SUMMARY CARD HERE
        summary_card
    ])


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

@callback(
    Output("sa-legend-modal", "is_open"),
    [Input("sa-open-legend", "n_clicks"), Input("sa-close-legend", "n_clicks")],
    [State("sa-legend-modal", "is_open")],
)
def sa_toggle_legend(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open
