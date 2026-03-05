# pages/subject_analysis.py
# Final stable version — Fixed DuplicateCallback error with 'initial_duplicate'
# Updated: Custom Graph Tooltip + StringIO Fix

import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash.exceptions import PreventUpdate
from io import StringIO  # <--- Added for stability
from cache_config import cache
import json
import re  # Added for section extraction

dash.register_page(__name__, path="/subject_analysis", name="Subject Analysis")

# ---------- Helper Functions ----------
def extract_numeric(roll):
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def sa_assign_section(roll_no, section_ranges=None, usn_mapping=None):
    roll_str = str(roll_no).strip().upper()
    if usn_mapping and roll_str in usn_mapping:
         return usn_mapping[roll_str]

    roll_num = extract_numeric(roll_no)
    if section_ranges:
        for sec_name, (start, end) in section_ranges.items():
            start_num = extract_numeric(start)
            end_num = extract_numeric(end)
            if start_num <= roll_num <= end_num:
                return sec_name
    return "Not Assigned"

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
  /* Inherit from overview.css or basic styles */
  background: #ffffff;
  border-radius: 12px;
  /* border-left is handled inline */
}

/* Remove hover scale transformation that conflicts with overview style */
/* .kpi-card:hover { transform: scale(1.03); } */  <-- Removed to match overview behavior (translateY)
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

/* Print-friendly export */
/* 1. CRITICAL FIX: Place @page OUTSIDE @media print for Chrome/Edge to respect it */
@page {
    size: landscape;
    margin: 10mm;
}

@media print {
  /* Reset standard body styling for print */
  body, html {
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
    background-color: #ffffff !important;
    margin: 0 !important;
    padding: 0 !important;
  }
  
  /* Hide interactive elements like buttons and modals */
  button, .btn-group, .modal {
    display: none !important;
  }

  /* Remove screen-only padding and margins to push content up */
  .sa-wrap, .pb-4, .container-fluid, .p-3, .mb-4 {
    padding-top: 0 !important;
    margin-top: 0 !important;
    background: transparent !important;
  }

  /* Optimize cards for PDF flat layout */
  .sa-card {
    box-shadow: none !important;
    border: 1px solid #e5e7eb !important;
    page-break-inside: avoid !important;
    break-inside: avoid !important;
    margin-bottom: 20px !important;
  }
  
  /* Prevent Plotly charts from splitting */
  .js-plotly-plot, .plotly, .dash-graph {
    page-break-inside: avoid !important;
    break-inside: avoid !important;
    width: 100% !important;
  }
  
  /* Prevent tables from splitting rows */
  tr, td, th {
    page-break-inside: avoid !important;
    break-inside: avoid !important;
  }

  /* Force KPI grid to align properly on PDF */
  .row-cols-md-6 > * {
    flex: 0 0 16.666667% !important;
    max-width: 16.666667% !important;
  }
}

/* Modal Print Specifics (Only print the table list when popup is open) */
body.modal-open .pb-4 > *:not(.modal) { display: none !important; }
body.modal-open .modal {
    display: block !important; position: static !important;
    opacity: 1 !important; background: transparent !important;
}
body.modal-open .modal-dialog { max-width: 100% !important; width: 100% !important; margin: 0 !important; }
body.modal-open .modal-content { border: none !important; box-shadow: none !important; }
body.modal-open .modal-footer, body.modal-open .modal-header button { display: none !important; }

/* Make KPI Cards Clickable */
.subject-kpi-card { cursor: pointer; transition: transform 0.2s ease, box-shadow 0.2s ease; }
.subject-kpi-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(59,130,246,0.2) !important; }
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
                            id="sa-subject-checklist",
                            options=[], value=[], multi=True,
                            placeholder="Select subjects to analyze...",
                            className="custom-dropdown",
                            searchable=True,
                            clearable=True,
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"position": "relative", "zIndex": "1000"}),
                ], xs=12, lg=4, style={"position": "relative", "zIndex": "1060", "overflow": "visible"}),
                
                dbc.Col([
                    html.H6("Select Section", className="fw-bold text-muted mb-1"),
                    html.Div([
                        dcc.Dropdown(
                            id="sa-section-filter",
                            options=[{"label": "All Sections", "value": "ALL"}],
                            value="ALL", clearable=False, className="custom-dropdown",
                            searchable=True,
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"position": "relative", "zIndex": "1000"}),
                ], xs=12, lg=2, style={"position": "relative", "zIndex": "1050", "overflow": "visible"}),

                dbc.Col([
                    html.H6("Filter by Result", className="fw-bold text-muted mb-1"),
                    html.Div([
                        dcc.Dropdown(
                            id="sa-result-filter",
                            options=[
                                {"label": "All Students", "value": "ALL"},
                                {"label": "Passed Only", "value": "PASS"},
                                {"label": "Failed Only", "value": "FAIL"},
                                {"label": "Absent Only", "value": "ABSENT"},
                            ],
                            value="ALL", clearable=False, className="custom-dropdown",
                            searchable=True,
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"position": "relative", "zIndex": "1000"}),
                ], xs=12, lg=3, style={"position": "relative", "zIndex": "1050", "overflow": "visible"}),

                dbc.Col([
                    html.H6("Actions", className="fw-bold text-muted mb-1"),
                    dbc.ButtonGroup([
                        dbc.Button("CSV", id="sa-export-csv", color="primary", outline=True, className="me-1"),
                        dbc.Button("Excel", id="sa-export-xlsx", color="success", outline=True, className="me-1"),
                        dbc.Button("PDF", id="sa-export-pdf", color="danger", outline=True, className="me-1"),
                        dbc.Button("ℹ️", id="sa-open-legend", color="info", outline=True),
                    ], className="w-100", style={"height": "45px"}),
                ], xs=12, lg=3), 
            ], className="g-3 align-items-start"),
            dbc.Row([
                dbc.Col(
                    dbc.Spinner(
                        html.Div(id="sa-selected-count", className="mt-2 small text-muted"),
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
        dbc.Card(dbc.CardBody(html.Div(id="sa-kpi-cards")), className="sa-card mb-4")
    ]),

    # --- Table ---
    # Wrapped in its own Loading component
    dcc.Loading(type="default", children=[
        dbc.Card(dbc.CardBody([
            html.H5("📋 Detailed Subject Breakdown", className="fw-bold mb-3 text-center"),
            dash_table.DataTable(
                id="sa-subject-table",
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
                merge_duplicate_headers=True,
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

    # --- KPI Popup Modal ---
    dbc.Modal([
        dbc.ModalHeader([
            dbc.ModalTitle(id="sa-kpi-modal-title", className="fw-bold text-primary"),
            html.Div([
                dbc.Button("Download List PDF", id="sa-kpi-modal-pdf-top", color="danger", outline=True, size="sm", className="me-2"),
                dbc.Button("Close", id="sa-kpi-modal-close-top", color="secondary", size="sm")
            ], className="ms-auto d-flex")
        ], close_button=False),
        dbc.ModalBody([
            dash_table.DataTable(
                id="sa-kpi-modal-table",
                columns=[], data=[],
                style_table={"overflowX": "auto", "borderRadius": "8px", "border": "1px solid #d1d5db"},
                style_cell={"textAlign": "center", "padding": "12px", "fontSize": "13px"},
                style_header={"backgroundColor": "#1f2937", "color": "#ffffff", "fontWeight": "700"},
                page_action='none',
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f3f4f6'}],
            )
        ]),
        dbc.ModalFooter([
            dbc.Button("Download List PDF", id="sa-kpi-modal-pdf", color="danger", outline=True),
            dbc.Button("Close", id="sa-kpi-modal-close", className="ms-auto", color="secondary")
        ])
    ], id="sa-kpi-modal", is_open=False, size="xl", style={"zIndex": 10000}),
    
    html.Div(id="sa-kpi-pdf-trigger-hidden", style={"display": "none"}),

    # --- Tabs for Charts ---
    # Wrapped in its own Loading component
    dcc.Loading(type="default", children=[
        dbc.Card(dbc.CardBody([
            dcc.Tabs(id="sa-chart-tabs", value="pie", children=[
                dcc.Tab(label="🎯 Pass vs Fail Distribution", value="pie"),
                dcc.Tab(label="📈 Subject-wise Average Marks", value="bar"),
            ]),
            html.Div(id="sa-subject-analysis-chart", className="mt-3"),
        ]), className="sa-card mb-4"),
    ]),


    # Hidden Download components
    dcc.Download(id="sa-download-csv"),
    dcc.Download(id="sa-download-xlsx"),
    html.Div(id="sa-pdf-download-trigger", style={"display": "none"}),

    # Use session stores to match global app.py stores
], fluid=True, className="pb-4")

# ==================== CALLBACKS ====================

# 1️⃣ Dropdown Control
@callback(
    Output("sa-section-filter", "options"),
    Input("section-data", "data"),
    Input("usn-mapping-store", "data")  # <-- Add this input
)
def update_section_dropdown(section_data, usn_mapping):
    options = [{"label": "All Sections", "value": "ALL"}]
    sections = set()
    
    # Add sections from Range Config
    if section_data:
        for sec in section_data.keys():
            sections.add(sec)
            
    # Add sections from Excel Mapping Config
    if usn_mapping:
        for sec in usn_mapping.values():
            sections.add(sec)
            
    # Sort and append unique sections
    for sec in sorted(list(sections)):
        options.append({"label": sec, "value": sec})
        
    # ONLY show "Not Assigned" if no sections are mapped at all
    if not sections:
        options.append({"label": "Not Assigned", "value": "Not Assigned"})
        
    return options

@callback(
    Output("sa-subject-checklist", "options"),
    Output("sa-subject-checklist", "value"),
    Input("overview-selected-subjects", "data"),
    Input("sa-subject-checklist", "value"),
    State("stored-data", "data"),
    prevent_initial_call=False
)
def update_subject_dropdown(overview_subjects, current_value, session_id):
    if not overview_subjects:
        return [], []
        
    name_mapping = {}
    if session_id:
        df = cache.get(session_id)
        if df is not None:
            for subj in overview_subjects:
                display_name = subj
                subj_cols = [c for c in df.columns if c.startswith(subj)]
                for col in subj_cols:
                    if " - " in col:
                        try:
                            rest = col.split(" - ", 1)[1]
                            for suffix in ["Result", "Total", "Internal", "External"]:
                                if rest.strip().endswith(suffix):
                                    possible_name = rest.rsplit(suffix, 1)[0].strip()
                                    if possible_name:
                                        display_name = f"{subj} - {possible_name}"
                                    break
                            if display_name != subj:
                                break
                        except: pass
                name_mapping[subj] = display_name

    # Add "Select All" and "Remove All" options at the top
    options = [
        {"label": "✓ Select All", "value": "__SELECT_ALL__"},
        {"label": "✕ Remove All", "value": "__REMOVE_ALL__"}
    ] 
    
    for s in overview_subjects:
        full_name = name_mapping.get(s, s)
        
        # Extract code part to display
        if " - " in full_name:
            c_part = full_name.split(" - ", 1)[0]
        else:
            c_part = full_name
            
        options.append({
            "label": html.Span(c_part, className="fw-bold"),
            "value": s,
            "title": full_name  # Keeps full name for standard HTML tooltips
        })

    all_subject_values = [opt["value"] for opt in options[2:]]  # Exclude the special markers
    
    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else "INITIAL_LOAD"

    if trigger == "sa-subject-checklist":
        # If "Select All" is clicked, select all subjects
        if current_value and "__SELECT_ALL__" in current_value:
            return options, all_subject_values
        # If "Remove All" is clicked, clear all
        elif current_value and "__REMOVE_ALL__" in current_value:
            return options, []
        # Remove special markers if user manually selects other subjects
        filtered_value = [v for v in (current_value or []) if not v.startswith("__")]
        return options, filtered_value
    
    # Return ALL values on initial load so that the charts and tables populate immediately
    return options, all_subject_values


# 2️⃣ Main Analysis
@callback(
    Output("sa-selected-count", "children"),
    Output("sa-kpi-cards", "children"),
    Output("sa-subject-table", "columns"),
    Output("sa-subject-table", "data"),
    Output("sa-subject-analysis-chart", "children"),
    Input("sa-subject-checklist", "value"),
    Input("sa-result-filter", "value"),
    Input("sa-section-filter", "value"),
    Input("sa-chart-tabs", "value"),
    State("stored-data", "data"),
    State("section-data", "data"),
    State("usn-mapping-store", "data"),
    prevent_initial_call=False
)
def update_analysis(selected_subjects, result_filter, section_filter, chart_tab, session_id, section_ranges, usn_mapping):
    if not session_id:
        raise PreventUpdate
    
    # Retrieve from Server Cache
    df = cache.get(session_id)
    if df is None:
        return "Session expired", html.P("Please return to Overview and upload data.", className="text-danger"), [], [], html.Div()

    # Remove the special markers if present
    selected_subjects = [s for s in (selected_subjects or []) if not s.startswith("__")]
    
    if not selected_subjects:
        return "0 subjects selected", html.P("Please select at least one subject.", className="text-muted text-center"), [], [], html.Div()

    first_col = df.columns[0]

    if "Name" not in df.columns:
        df["Name"] = ""

    selected_cols = []
    for subj in selected_subjects:
        selected_cols.extend([c for c in df.columns if c.startswith(f"{subj} ")])
    selected_cols = list(dict.fromkeys(selected_cols))

    df_sel = df[[first_col, "Name"] + selected_cols].copy()
    
    # Apply Section Assignment and Filtering
    df_sel['Section'] = df_sel[first_col].apply(lambda x: sa_assign_section(x, section_ranges, usn_mapping))
    if section_filter and section_filter != "ALL":
        df_sel = df_sel[df_sel['Section'] == section_filter]
        if df_sel.empty:
            return f"0 students in section {section_filter}", html.P(f"No data for section {section_filter}."), [], [], html.Div()

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
            {"id": "total", "label": "TOTAL", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "appeared", "label": "APPEARED", "value": appeared, "color": "#10b981", "bg": "#ecfdf5", "icon": "bi-person-check-fill"},
            {"id": "pass", "label": "PASSED", "value": passed, "color": "#0ea5e9", "bg": "#f0f9ff", "icon": "bi-check-circle-fill"},
            {"id": "fail", "label": "FAILED", "value": failed, "color": "#ef4444", "bg": "#fef2f2", "icon": "bi-x-circle-fill"},
            {"id": "absent", "label": "ABSENT", "value": absent, "color": "#f59e0b", "bg": "#fffbeb", "icon": "bi-person-x-fill"},
            {"id": "rate", "label": "PASS %", "value": f"{pass_pct_appeared}%", "color": "#8b5cf6", "bg": "#f5f3ff", "icon": "bi-graph-up"},
        ]
        col_class = "row-cols-2 row-cols-md-3 row-cols-lg-6 g-3"
    elif result_filter == "PASS":
        kpis = [
            {"id": "total", "label": "TOTAL", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "pass", "label": "PASSED", "value": passed_filtered, "color": "#10b981", "bg": "#ecfdf5", "icon": "bi-check-circle-fill"},
        ]
        col_class = "row-cols-2 row-cols-md-6 g-3"
    elif result_filter == "FAIL":
        kpis = [
            {"id": "total", "label": "TOTAL", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "fail", "label": "FAILED", "value": failed_filtered, "color": "#ef4444", "bg": "#fef2f2", "icon": "bi-x-circle-fill"},
        ]
        col_class = "row-cols-2 row-cols-md-6 g-3"
    else:  # ABSENT
        kpis = [
            {"id": "total", "label": "TOTAL", "value": total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"id": "absent", "label": "ABSENT", "value": absent_filtered, "color": "#f59e0b", "bg": "#fffbeb", "icon": "bi-person-x-fill"},
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
        
        # Try to extract full subject name if available in columns
        display_name = subj
        for col in subj_cols:
            if " - " in col:
                # Expected format: "Code - Name Component"
                # e.g. "18CS51 - DATA STRUCTURES Total"
                try:
                    # Split by " - " to get "Name Component" part
                    rest = col.split(" - ", 1)[1]
                    # Remove the component suffix
                    for suffix in ["Result", "Total", "Internal", "External"]:
                        if rest.strip().endswith(suffix):
                            possible_name = rest.rsplit(suffix, 1)[0].strip()
                            if possible_name:
                                display_name = f"{subj} - {possible_name}"
                            break
                    if display_name != subj:
                        break
                except:
                    continue

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
                "Subject": display_name,
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
            "Subject": display_name,
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

    # Updated KPI Card style to match Overview page exactly

    cards = html.Div([
        dbc.Row([
            dbc.Col(
                # Changed from dbc.Card to html.Div to natively support n_clicks
                html.Div(
                    dbc.CardBody([
                        html.Div([
                            # Icon on the Left
                            html.Div(
                                html.I(className=f"bi {k['icon']} subject-kpi-icon", style={"color": k["color"]}),
                                className="subject-kpi-icon-box",
                                style={"backgroundColor": k["bg"]}
                            ),
                            
                            # Text on the Right
                            html.Div([
                                html.H6(k["label"], className="subject-kpi-label"),
                                html.H3(str(k["value"]), className="subject-kpi-value", style={"color": k["color"]})
                            ], className="subject-kpi-text-box"),
                        ], className="subject-kpi-content-wrapper"),
                        
                    ], className="subject-kpi-body"),
                    className="card subject-kpi-card box-shadow-sm",
                    id={"type": "sa-kpi-card", "index": k["id"]},
                    n_clicks=0,
                    style={"--kpi-color": k['color'], "border": "none"}
                )
            )
            for k in kpis
        ], className=col_class + " mb-4"),  # added margin bottom to separate from summary table
        
        # INSERT SUMMARY CARD HERE
        summary_card
    ])



    # Table
    columns_for_table = []
    
    # Add Identity Columns first
    columns_for_table.append({"name": ["Student", "ID"], "id": first_col})
    columns_for_table.append({"name": ["Student", "Name"], "id": "Name"})
    columns_for_table.append({"name": ["Student", "Section"], "id": "Section"})

    # robust column grouping logic
    # Group columns by subject to ensure they appear together in the table
    # Sort columns by subject code/name first, then bu component order (Int, Ext, Tot, Res)
    
    def get_col_sort_key(col_name):
        # Extract subject prefix and component
        for s in ["Internal", "External", "Total", "Result"]:
            if col_name.endswith(f" {s}"):
                base = col_name[:-len(s)].strip()
                # Order: Internal=0, External=1, Total=2, Result=3
                order = {"Internal": 0, "External": 1, "Total": 2, "Result": 3}.get(s, 9)
                return (base, order)
        return (col_name, 99)

    selected_cols.sort(key=get_col_sort_key)

    for c in selected_cols:
        col_header = ["", c] # Default fallback
        
        for s in ["Internal", "External", "Total", "Result"]:
            if c.endswith(f" {s}"):
                base = c[:-len(s)].strip() # This extracts the full Subject Name e.g. "18CS51 - MATH"
                col_header = [base, s]
                break
            
        columns_for_table.append({"name": col_header, "id": c})

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
            # Build data for the bar chart with Full Names
            avg_marks_data = []
            
            for subj in selected_subjects:
                # 1. Identify Full Name (Same logic as tables)
                display_name = subj
                subj_cols = [c for c in df_sel.columns if c.startswith(subj)]
                for col in subj_cols:
                    if " - " in col:
                        try:
                            rest = col.split(" - ", 1)[1]
                            for suffix in ["Result", "Total", "Internal", "External"]:
                                if rest.strip().endswith(suffix):
                                    possible_name = rest.rsplit(suffix, 1)[0].strip()
                                    if possible_name:
                                        display_name = f"{subj} - {possible_name}"
                                    break
                            if display_name != subj: break
                        except: continue

                # 2. Calculate Average
                # Filter related Total columns
                total_cols = [c for c in selected_cols if subj in c and "Total" in c]
                if not total_cols:
                    continue
                
                # Calculate mean of totals for this subject across all students
                # Note: This averages the student's average if multiple totals exist (rare), or just the single total
                val = df_for_avg[total_cols].mean(axis=1).mean()
                
                avg_marks_data.append({"Subject_Code": subj, "Full_Name": display_name, "Average": val})

            if not avg_marks_data:
                 chart = html.P("No data available for chart.", className="text-muted text-center")
            else:
                df_chart = pd.DataFrame(avg_marks_data)
                
                bar_fig = px.bar(
                    df_chart, 
                    x="Subject_Code", 
                    y="Average",
                    text=df_chart["Average"].apply(lambda x: f"{x:.1f}"),
                    color="Subject_Code", 
                    color_discrete_sequence=px.colors.qualitative.Plotly,
                    custom_data=["Full_Name"] # Store full name for tooltip
                )
                
                # --- CUSTOM TOOLTIP & LAYOUT FIXES ---
                bar_fig.update_traces(
                    textposition="outside",
                    hovertemplate="<b>%{customdata[0]}</b><br>Avg Marks: %{y:.2f}<extra></extra>"
                )
                
                bar_fig.update_layout(
                    title="Average Total Marks per Subject", 
                    title_x=0.5, 
                    template="plotly_white",
                    yaxis_title="Average Marks", 
                    xaxis_title="Subject Code",
                    showlegend=False      # Hide legend as x-axis shows codes
                )
                chart = dcc.Graph(figure=bar_fig)

    return f"{len(selected_subjects)} subjects selected", cards, columns_for_table, data, chart


# 3️⃣ Export Callbacks
@callback(
    Output("sa-download-csv", "data"),
    Input("sa-export-csv", "n_clicks"),
    State('sa-subject-table', 'data'),
    State('sa-subject-table', 'columns'),
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
    State('sa-subject-table', 'data'),
    State('sa-subject-table', 'columns'),
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

dash.clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) {
            return window.dash_clientside.no_update;
        }
        setTimeout(function () { window.print(); }, 150);
        return "";
    }
    """,
    Output("sa-pdf-download-trigger", "children"),
    Input("sa-export-pdf", "n_clicks"),
    prevent_initial_call=True
)

# 4️⃣ KPI Target Click Callback
@callback(
    Output("sa-kpi-modal", "is_open"),
    Output("sa-kpi-modal-title", "children"),
    Output("sa-kpi-modal-table", "data"),
    Output("sa-kpi-modal-table", "columns"),
    Input({"type": "sa-kpi-card", "index": ALL}, "n_clicks"),
    Input("sa-kpi-modal-close", "n_clicks"),
    Input("sa-kpi-modal-close-top", "n_clicks"),
    State("sa-subject-table", "data"),
    State("sa-subject-table", "columns"),
    prevent_initial_call=True
)
def handle_kpi_click(kpi_clicks, close_click, close_click_top, table_data, table_cols):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    trigger_id = ctx.triggered[0]["prop_id"]
    
    # Check if close button triggered (top or bottom)
    if "sa-kpi-modal-close" in trigger_id:
        return False, dash.no_update, dash.no_update, dash.no_update
        
    # Ignore initial setup triggers where all clicks might be 0/None
    if all(c == 0 or c is None for c in kpi_clicks):
        raise PreventUpdate
        
    # Extract which specific card was clicked
    try:
        prop_dict = json.loads(trigger_id.split(".")[0])
        kpi_type = prop_dict["index"]
    except Exception:
        raise PreventUpdate
        
    if not table_data:
        return True, f"Student List: {kpi_type.upper()}", [], table_cols
        
    # Filter the exact data subset for the clicked KPI
    filtered_data = []
    if kpi_type == "total":
        filtered_data = table_data
    elif kpi_type == "appeared":
        filtered_data = [row for row in table_data if row.get("Overall_Result") != "Absent"]
    elif kpi_type == "pass":
        filtered_data = [row for row in table_data if row.get("Overall_Result") == "Pass"]
    elif kpi_type == "fail":
        filtered_data = [row for row in table_data if row.get("Overall_Result") == "Fail"]
    elif kpi_type == "absent":
        filtered_data = [row for row in table_data if row.get("Overall_Result") == "Absent"]
    elif kpi_type == "rate":
        # Treating Rate % click as looking at passed students
        filtered_data = [row for row in table_data if row.get("Overall_Result") == "Pass"]
        kpi_type = "pass"
        
    title = f"📃 Detail List: {kpi_type.upper()} ({len(filtered_data)} Students)"
    
    return True, title, filtered_data, table_cols

# PDF Download directly inside Modal
dash.clientside_callback(
    """
    function(n_clicks_bottom, n_clicks_top) {
        // Prevent trigger if both are empty/initial loading
        if (!n_clicks_bottom && !n_clicks_top) return window.dash_clientside.no_update;
        setTimeout(function () { window.print(); }, 150);
        return "";
    }
    """,
    Output("sa-kpi-pdf-trigger-hidden", "children"),
    Input("sa-kpi-modal-pdf", "n_clicks"),
    Input("sa-kpi-modal-pdf-top", "n_clicks"),
    prevent_initial_call=True
)