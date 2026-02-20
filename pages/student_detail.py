import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import re
from cache_config import cache
from dash.exceptions import PreventUpdate

dash.register_page(__name__, path="/student_detail", name="Student Detail")

# ---------- Helper Functions ----------
def get_grade_point(percentage_score):
    score = pd.to_numeric(percentage_score, errors='coerce')
    if pd.isna(score): return 0
    if 90 <= score <= 100: return 10
    elif 80 <= score < 90: return 9
    elif 70 <= score < 80: return 8
    elif 60 <= score < 70: return 7
    elif 55 <= score < 60: return 6
    elif 50 <= score < 55: return 5
    elif 40 <= score < 50: return 4
    else: return 0

def extract_numeric(roll):
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges=None, usn_mapping=None):
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

# ---------- Layout ----------
layout = dbc.Container([
    # Hero Header with Gradient
    html.Div([
        html.Div([
            html.I(className="bi bi-mortarboard-fill me-3", style={"fontSize": "2.5rem", "color": "white"}),
            html.H2("Student Performance Dashboard", className="mb-1 fw-bold d-inline-block", style={"color": "white"})
        ], className="d-flex align-items-center justify-content-center mb-2"),
        html.P("Comprehensive SGPA Analysis & Performance Tracking", 
               className="text-center mb-0", 
               style={"color": "rgba(255,255,255,0.9)", "fontSize": "1.1rem"}),
        html.Div([
            dbc.Badge("📊 Analytics", color="light", className="me-2", style={"padding": "0.5rem 1rem"}),
            dbc.Badge("🎯 SGPA Calculator", color="light", className="me-2", style={"padding": "0.5rem 1rem"}),
            dbc.Badge("📈 Live Updates", color="light", style={"padding": "0.5rem 1rem"})
        ], className="text-center mt-3")
    ], style={
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "padding": "3rem 1rem",
        "borderRadius": "0 0 20px 20px",
        "marginBottom": "2rem",
        "boxShadow": "0 10px 40px rgba(102, 126, 234, 0.3)"
    }),

    # Search Card with Enhanced Design
    dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-search me-2"),
            html.Span("Search Student", className="fw-bold")
        ], className="bg-white border-0", style={"fontSize": "1.1rem", "overflow": "visible"}),

        dbc.CardBody([
            dbc.Row([
                # Student ID/Name Search
                dbc.Col([
                    html.Label([
                        html.I(className="bi bi-person-badge me-2", style={"color": "#667eea"}),
                        "Student ID / Name"
                    ], className="form-label fw-semibold", style={"color": "#2c3e50"}),
                    dbc.InputGroup([
                        dbc.InputGroupText(html.I(className="bi bi-search"), style={"background": "#f8f9fa"}),
                        dcc.Input(
                            id='student-search',
                            type='text',
                            placeholder='🔍 Enter USN or Name (e.g., 1XX20CS001)',
                            debounce=True,
                            className="form-control",
                            style={"border": "2px solid #e0e0e0"}
                        )
                    ], className="shadow-sm")
                ], md=12, lg=4, className="mb-3"),
                
                # Subject Dropdown
                dbc.Col([
                    html.Label([
                        html.I(className="bi bi-book me-2", style={"color": "#667eea"}),
                        "Subject Codes"
                    ], className="form-label fw-semibold", style={"color": "#2c3e50"}),
                    html.Div([
                        dcc.Dropdown(
                            id='student-subject-dropdown',
                            placeholder="📚 Select Subject Code(s) or leave All",
                            multi=True,
                            className="custom-dropdown",
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"overflow": "visible", "position": "relative", "zIndex": "1000"})
                ], md=12, lg=5, className="mb-3"),
                
                # Search Button
                dbc.Col([
                    html.Label(" ", className="form-label", style={"visibility": "hidden"}),
                    dbc.Button([
                        html.I(className="bi bi-search me-2"),
                        "Search Student"
                    ], id='search-btn', color="primary", className="w-100 shadow", n_clicks=0,
                    style={"height": "45px", "fontSize": "1rem", "fontWeight": "600"})
                ], md=12, lg=3, className="mb-3")
            ], className="g-2"),
            
            html.Hr(style={"margin": "1.5rem 0", "opacity": "0.3"}),
            
            # Analysis Type Section
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.I(className="bi bi-sliders me-2", style={"color": "#667eea", "fontSize": "1.3rem"}),
                        html.H6("Analysis Type", className="mb-0 fw-bold d-inline", style={"color": "#2c3e50"})
                    ], className="mb-3"),
                    dbc.ButtonGroup([
                        dbc.RadioItems(
                            id='analysis-type-radio',
                            options=[
                                {'label': ' 📝 Internal Marks', 'value': 'Internal'},
                                {'label': ' 📄 External Marks', 'value': 'External'},
                                {'label': ' 📊 Total Marks', 'value': 'Total'},
                            ],
                            value='Total',
                            inline=True,
                            className="btn-group",
                            labelClassName="btn btn-outline-primary",
                            inputClassName="btn-check"
                        )
                    ])
                ], className="text-center")
            ])
        ], style={"padding": "2rem", "overflow": "visible", "position": "relative"})
    ], className="shadow-custom mb-4", style={"borderRadius": "15px", "overflow": "visible"}),
    
    # Results Sections
    dbc.Row([
        dbc.Col([
            html.Div(id='credit-input-container', className="fade-in", style={"overflow": "visible", "position": "relative"})
        ], width=12)
    ], style={"overflow": "visible"}),
    
    dbc.Row([
        dbc.Col([
            html.Div(id='student-detail-content', className="fade-in")
        ], width=12)
    ]),
    
], fluid=True, className="py-4", style={"background": "#f8f9fa", "minHeight": "100vh"})

# ---------- Populate Subject Dropdown ----------
@callback(
    Output('student-subject-dropdown', 'options'),
    Output('student-subject-dropdown', 'value'),
    Input('stored-data', 'data')
)
def populate_subject_dropdown(session_id):
    if not session_id:
        return [], []
    df = cache.get(session_id)
    if df is None: return [], []
    
    if 'Name' not in df.columns:
        df['Name'] = ""
    exclude_cols = ['Student ID', 'Name', 'Section', df.columns[0]]
    subject_components = [
        c for c in df.columns
        if c not in exclude_cols and 'Rank' not in c and 'Result' not in c and 'Total_Marks' not in c
    ]
    filtered_components = [c for c in subject_components if 'Result' not in c]
    
    # Robust extraction of subject identifiers (supporting "Code - Name" format)
    subject_identifiers = set()
    for c in filtered_components:
        # We need the part BEFORE " Internal", " External", " Total"
        # Since we filtered out 'Result', we look for other suffixes
        for suffix in [' Internal', ' External', ' Total']:
            if c.endswith(suffix):
                subject_identifiers.add(c[:-len(suffix)])
                break
    
    subject_codes = sorted(list(subject_identifiers))
    options = [{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in subject_codes]
    return options, ['ALL']

# ---------- Generate Credit Inputs ----------
@callback(
    Output('credit-input-container', 'children'),
    Input('search-btn', 'n_clicks'),
    State('student-search', 'value'),
    State('stored-data', 'data'),
    State('student-subject-dropdown', 'value'),
    State('analysis-type-radio', 'value'),
    prevent_initial_call=True
)
def generate_credit_inputs(n_clicks, search_value, session_id, selected_subject_codes, analysis_type):
    if not session_id or not search_value:
        return ""
    df = cache.get(session_id)
    if df is None: return ""
    
    if 'Name' not in df.columns:
        df['Name'] = ""
    # robust search (avoid AttributeError by ensuring Series)
    meta_col = df.columns[0]
    norm_search = str(search_value).strip().lower()
    mask = (
        df[meta_col].astype(str).str.strip().str.lower() == norm_search
    ) | (
        df['Name'].astype(str).str.strip().str.lower() == norm_search
    )
    student_df = df[mask]
    if student_df.empty:
        return dbc.Alert("No student found with this ID or Name.", color="warning", className="text-center mt-3")
    student_series = student_df.iloc[0]

    # Identify available subject identifier strings (e.g. "18Cs51" OR "18CS51 - MATHS")
    subject_identifiers = set()
    for col in df.columns:
        if 'Result' not in col:
            for suffix in [' Internal', ' External', ' Total']:
                if col.endswith(suffix):
                    subject_identifiers.add(col[:-len(suffix)])
                    break
    
    available_subjects = sorted(list(subject_identifiers))

    if not selected_subject_codes or 'ALL' in selected_subject_codes:
        codes_selected = available_subjects
    else:
        codes_selected = [s for s in selected_subject_codes if s != 'ALL']

    subject_codes_for_credits = sorted([
        code for code in codes_selected
        if pd.to_numeric(student_series.get(f"{code} {analysis_type}"), errors='coerce') > 0
    ])

    if not subject_codes_for_credits:
        return dbc.Alert(
            "This student has no score data for the selected subjects.",
            color="info",
            className="text-center mt-3"
        )

    credit_inputs = []
    for idx, raw_code in enumerate(subject_codes_for_credits):
        # Clean display: Extract just the code if name is present
        # Format: "Code - Name" -> display "Code (Name truncated?)" or full
        if " - " in raw_code:
            parts = raw_code.split(" - ", 1)
            display_text = html.Div([
                html.Span(parts[0], className="fw-bold d-block"),
                html.Small(parts[1], className="text-muted d-block text-truncate", style={"maxWidth": "250px"})
            ])
            code_val = raw_code # keep full key for ID
        else:
            display_text = html.Span(raw_code, className="fw-bold")
            code_val = raw_code

        z_index = 1000 - (idx * 5)  # Decreasing z-index for each card
        credit_inputs.append(
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.I(className="bi bi-journal-code me-2", style={"color": "#667eea", "fontSize": "1.2rem"}),
                                display_text
                            ])
                        ], width=8, className="text-start align-self-center"),
                        dbc.Col([
                            dcc.Dropdown(
                                id={'type': 'credit-input-student', 'index': code_val},
                                options=[{'label': f'{i} Credit{"s" if i != 1 else ""}', 'value': i} for i in range(0, 5)],
                                value=3,
                                clearable=False,
                                className="custom-dropdown",
                                style={"zIndex": str(z_index + 1)}
                            )
                        ], width=4, style={"position": "relative", "zIndex": str(z_index + 1)})
                    ], align="center")
                ], className="py-2 px-3", style={"overflow": "visible"})
            ], className="shadow-sm mb-2", style={"border": "1px solid #e0e0e0", "borderRadius": "10px", "overflow": "visible", "position": "relative", "zIndex": str(z_index)})
        )

    card = dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className="bi bi-calculator me-2", style={"color": "#667eea", "fontSize": "1.5rem"}),
                html.H5("Step 2: Enter Subject Credits", className="fw-bold d-inline mb-0")
            ], className="text-center mb-2", style={"color": "#2c3e50"}),
            html.P([
                html.I(className="bi bi-info-circle me-2", style={"color": "#667eea"}),
                "Select credits (0–4) for subjects you want included in SGPA / KPI calculations."
            ], className="text-muted text-center mb-3", style={"fontSize": "0.9rem"}),
            html.Div(
                credit_inputs,
                style={"maxHeight": "400px", "overflowY": "auto", "overflowX": "visible", "padding": "0.5rem", "position": "relative"}
            ),
            dbc.Button([
                html.I(className="bi bi-calculator-fill me-2"),
                "Calculate & View Full Report"
            ], id='calculate-sgpa-btn', color="success", className="w-100 mt-3 shadow",
            style={"fontSize": "1.05rem", "fontWeight": "600", "height": "50px"})
        ], style={"padding": "2rem", "overflow": "visible"})
    ], className="shadow-custom mb-4", style={"borderRadius": "15px", "overflow": "visible"})

    return card

# ---------- Display Full Report ----------
@callback(
    Output('student-detail-content', 'children'),
    Input('calculate-sgpa-btn', 'n_clicks'),
    [
        State('student-search', 'value'),
        State('stored-data', 'data'),
        State('section-data', 'data'),
        State('usn-mapping-store', 'data'),
        State('analysis-type-radio', 'value'),
        State({'type': 'credit-input-student', 'index': ALL}, 'id'),
        State({'type': 'credit-input-student', 'index': ALL}, 'value'),
    ],
    prevent_initial_call=True
)
def display_full_report(n_clicks, search_value, session_id, section_ranges, usn_mapping, analysis_type, credit_ids, credit_vals):
    if not all([session_id, search_value]):
        return ""

    # Load & normalize base columns
    df = cache.get(session_id)
    if df is None: return ""
    
    if 'Name' not in df.columns:
        df['Name'] = ""

    # Normalize identifier column to 'Student ID' (keep original too)
    first_col = df.columns[0]
    if 'Student ID' not in df.columns:
        df.rename(columns={first_col: 'Student ID'}, inplace=True)

    # ---------- ✅ SECTION ASSIGNMENT ----------
    df['Section'] = df['Student ID'].apply(lambda x: assign_section(x, section_ranges, usn_mapping))

    # ---------- ✅ RANKS (EXACTLY LIKE RANKING PAGE) ----------
    # 1) Total_Marks = sum of columns containing 'Total' or 'Marks' or 'Score'
    total_cols = [c for c in df.columns if ('Total' in c or 'Marks' in c or 'Score' in c) and 'Selected' not in c]
    if total_cols:
        df[total_cols] = df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        df['Total_Marks'] = df[total_cols].sum(axis=1)
    else:
        df['Total_Marks'] = 0

    # 2) Overall_Result: if Result cols exist -> P only if all P; else fallback with pass_mark=18 on total_cols
    result_cols = [c for c in df.columns if 'Result' in c]
    if result_cols:
        df['Overall_Result'] = df[result_cols].apply(
            lambda row: 'P' if all(str(v).strip().upper() == 'P' for v in row if pd.notna(v)) else 'F', axis=1)
    else:
        pass_mark = 18
        if total_cols:
            df['Overall_Result'] = df.apply(
                lambda row: 'F' if any(row[c] < pass_mark for c in total_cols) else 'P', axis=1
            )
        else:
            # No totals at all -> default pass
            df['Overall_Result'] = 'P'

    # 3) Class_Rank among passed only (descending), same as ranking page
    df['Class_Rank'] = df[df['Overall_Result'] == 'P']['Total_Marks'] \
        .rank(method='min', ascending=False).astype('Int64')

    # 4) Section_Rank within section (NO pass filter, matches ranking page)
    if 'Section' in df.columns:
        df['Section_Rank'] = df.groupby('Section')['Total_Marks'] \
            .rank(method='min', ascending=False).astype('Int64')
    else:
        df['Section_Rank'] = pd.Series([pd.NA] * len(df), dtype='Int64')

    # ---------- ✅ SUBJECT SELECTION / CREDITS FOR SGPA ----------
    credit_dict_all = {cid['index']: cval for cid, cval in zip(credit_ids, credit_vals) if cval is not None}
    credit_dict_positive = {k: v for k, v in credit_dict_all.items() if v > 0}
    all_subject_codes_selected = list(credit_dict_all.keys())
    if not all_subject_codes_selected:
        return dbc.Alert("Please enter credits for at least one subject.", color="warning")

    # KPI columns for selected subjects for chosen analysis_type
    kpi_cols_all = [f"{code} {analysis_type}" for code in all_subject_codes_selected]
    # make them numeric for totals
    for col in kpi_cols_all:
        if col not in df.columns:
            df[col] = 0
    df[kpi_cols_all] = df[kpi_cols_all].apply(pd.to_numeric, errors='coerce').fillna(0)
    df['Total_Marks_Selected'] = df[kpi_cols_all].sum(axis=1)

    # ---------- ✅ PASS/FAIL (DISPLAY) — IGNORE 0-CREDIT SUBJECTS ----------
    # ---------- ✅ PASS/FAIL (DISPLAY) — IGNORE 0-CREDIT SUBJECTS ----------
    if analysis_type == 'Total':
        total_results = []

        for _, row in df.iterrows():
            fail_flag = False

            for code, credit in credit_dict_all.items():
                if credit == 0:
                    continue

                internal = pd.to_numeric(
                    row.get(f"{code} Internal", 0), errors='coerce'
                ) or 0
                external = pd.to_numeric(
                    row.get(f"{code} External", 0), errors='coerce'
                ) or 0
                result_val = str(
                    row.get(f"{code} Result", "")
                ).strip().upper()

                # 🔑 SAME LOGIC AS RANKING PAGE
                if (internal < 18) or (external < 18):
                    # Result column overrides failure
                    if result_val != 'P':
                        fail_flag = True
                        break

            total_results.append("Fail" if fail_flag else "Pass")

        df['Result_Selected'] = total_results

    else:
        metric = analysis_type  # "Internal" or "External"
        pass_results = []

        for _, row in df.iterrows():
            statuses = []

            for code, credit in credit_dict_all.items():
                if credit == 0:
                    continue

                score = pd.to_numeric(
                    row.get(f"{code} {metric}", 0), errors='coerce'
                ) or 0

                statuses.append("Pass" if score >= 18 else "Fail")

            pass_results.append(
                "Pass" if statuses and all(s == "Pass" for s in statuses) else "Fail"
            )

        df['Result_Selected'] = pass_results

    # ---------- Pick the selected student ----------
    norm_search = str(search_value).strip().lower()
    student_mask = (
        df['Student ID'].astype(str).str.strip().str.lower() == norm_search
    ) | (
        df['Name'].astype(str).str.strip().str.lower() == norm_search
    )
    if df[student_mask].empty:
        return dbc.Alert("No student found with this ID or Name.", color="warning", className="text-center mt-3")
    student_series = df[student_mask].iloc[0]

    # ---------- SGPA using only positive-credit subjects ----------
    total_credit_points, total_credits = 0, 0
    for code, credit in credit_dict_positive.items():
        grade_point = get_grade_point(student_series.get(f"{code} {analysis_type}", 0))
        total_credit_points += grade_point * credit
        total_credits += credit
    sgpa = (total_credit_points / total_credits) if total_credits > 0 else 0.0

    # ---------- KPI Cards ----------
    total_marks_selected = student_series['Total_Marks_Selected']
    percentage = sgpa * 10
    result_selected = student_series['Result_Selected']

    # Ranks pulled from the global (ranking-page) logic above:
    class_rank_global = student_series.get('Class_Rank', pd.NA)
    section_rank_global = student_series.get('Section_Rank', pd.NA)

    kpi_items = [
        {"label": "Total Marks (Selected)", "icon": "bi-clipboard-data", "value": f"{total_marks_selected:.0f}", "color": "#3b82f6", "bg": "#eff6ff"},
        {"label": "Percentage", "icon": "bi-bar-chart-fill", "value": f"{percentage:.2f}%", "color": "#06b6d4", "bg": "#ecfeff"},
        {"label": "Result", "icon": "bi-patch-check-fill" if result_selected == "Pass" else "bi-x-octagon-fill", "value": result_selected, "color": "#22c55e" if result_selected == "Pass" else "#ef4444", "bg": "#ecfdf5" if result_selected == "Pass" else "#fef2f2"},
        # ✅ These ranks now mirror the Ranking page logic
        {"label": "Class Rank (Global)", "icon": "bi-trophy-fill", "value": class_rank_global if pd.notna(class_rank_global) else "—", "color": "#f59e0b", "bg": "#fffbeb"},
        {"label": "Section Rank (Global)", "icon": "bi-award-fill", "value": section_rank_global if pd.notna(section_rank_global) else "—", "color": "#8b5cf6", "bg": "#f5f3ff"},
        {"label": "Section", "icon": "bi-people-fill", "value": student_series.get('Section', 'Not Assigned'), "color": "#2563eb", "bg": "#eff6ff"},
    ]

    kpi_cards = []
    for item in kpi_items:
        card = dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.Div(
                        html.I(className=f"{item['icon']}", style={"color": item['color'], "fontSize": "1.5rem"}),
                        style={"minWidth": "48px", "width": "48px", "height": "48px", "borderRadius": "12px", "backgroundColor": f"{item['color']}15", "display": "flex", "alignItems": "center", "justifyContent": "center"}
                    ),
                    html.Div([
                        html.H6(item["label"], className="text-muted text-uppercase fw-bold mb-1", style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                        html.H4(item["value"], className="fw-bold mb-0", style={"color": item["color"]})
                    ], className="ms-3 text-start")
                ], className="d-flex align-items-center h-100")
            ], className="p-3"),
            className="kpi-card shadow-sm h-100 border-0",
            style={"borderLeft": f"4px solid {item['color']}", "transition": "transform 0.2s ease-in-out"}
        )
        kpi_cards.append(dbc.Col(card, md=2, sm=4, xs=6, className="mb-3"))

    kpi_cards_row = dbc.Row(kpi_cards, className="g-3 mb-4 justify-content-center")

    # ---------- Header ----------
    header_row = dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className="bi bi-person-circle me-2", style={"color": "#667eea", "fontSize": "2rem"}),
                    html.H4(student_series.get('Name', ''), className="mb-0 d-inline-block fw-bold", style={"color": "#2c3e50"}),
                ], className="text-center mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.I(className="bi bi-credit-card me-2", style={"color": "#667eea"}),
                            html.Span("Student ID", className="text-muted small")
                        ]),
                        html.H6(student_series.get('Student ID', ''), className="fw-bold mb-0", style={"color": "#2c3e50"})
                    ], className="text-center", width=6),
                    dbc.Col([
                        html.Div([
                            html.I(className="bi bi-people-fill me-2", style={"color": "#667eea"}),
                            html.Span("Section", className="text-muted small")
                        ]),
                        html.H6(student_series.get('Section', 'Not Assigned'), className="fw-bold mb-0", style={"color": "#2c3e50"})
                    ], className="text-center", width=6)
                ])
            ])
        ], className="mb-3 shadow-custom", style={"borderRadius": "15px", "background": "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)"}), md=7),
        
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className="bi bi-award-fill me-2", style={"color": "#ffd700", "fontSize": "2rem"}),
                    html.Span("SGPA Score", className="text-muted d-block small mb-2")
                ], className="text-center"),
                html.H1(f"{sgpa:.2f}", className="fw-bold text-center mb-0 text-gradient", 
                       style={"fontSize": "3rem", "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)", 
                              "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent"})
            ])
        ], className="mb-3 shadow-custom", style={"borderRadius": "15px", "background": "linear-gradient(135deg, #fff9e6 0%, #fffbf0 100%)"}), md=5)
    ], className="mb-4 justify-content-center align-items-stretch")

    # ---------- Charts ----------
    subject_scores = pd.Series({s: pd.to_numeric(student_series.get(s, 0), errors='coerce') for s in kpi_cols_all}).dropna()
    scores_above_zero = subject_scores[subject_scores > 0]

    if scores_above_zero.empty:
        return dbc.Card(
            dbc.CardBody([
                html.H4("Full Performance Report", className="text-center mb-3"),
                header_row,
                kpi_cards_row,
                dbc.Alert("No scores > 0 for the selected analysis/subjects.", color="info")
            ]),
            className="mt-3 shadow"
        )

    class_averages = df[kpi_cols_all].replace(0, pd.NA).mean()
    class_max = df[kpi_cols_all].replace(0, pd.NA).max()
    
    # Create full labels (Code - Name) and short labels (Code only)
    clean_labels = [idx.replace(f" {analysis_type}", "") for idx in scores_above_zero.index]
    short_labels = [label.split(' - ')[0] if ' - ' in label else label.split()[0] for label in clean_labels]

    bar_fig = go.Figure(data=[
        go.Bar(
            x=short_labels,
            y=scores_above_zero.values,
            text=[f"{v:.0f}" for v in scores_above_zero.values],
            textposition='auto',
            customdata=clean_labels,
            hovertemplate='<b>%{customdata}</b><br>Marks: %{y}<extra></extra>',
            marker=dict(
                color=scores_above_zero.values,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Marks")
            )
        )
    ])
    bar_fig.update_layout(
        title_text=f"📊 Subject-wise Performance ({analysis_type})",
        title_x=0.5,
        title_font=dict(size=16, color='#2c3e50', family='Arial, sans-serif'),
        plot_bgcolor='rgba(248,249,250,0.5)',
        paper_bgcolor='white',
        margin=dict(t=50, b=100, l=40, r=40), # Increased bottom margin
        xaxis=dict(
            title="Subjects", 
            titlefont=dict(size=13, color='#667eea'),
            tickangle=-45 # Rotate for long names
        ),
        yaxis=dict(title="Marks", titlefont=dict(size=13, color='#667eea'), gridcolor='#e0e0e0')
    )

    comp_fig = go.Figure(data=[
        go.Bar(x=short_labels, y=scores_above_zero.values, name="Student", 
               marker_color='#440154', text=[f"{v:.0f}" for v in scores_above_zero.values], textposition='auto',
               customdata=clean_labels,
               hovertemplate='<b>%{customdata}</b><br>Marks: %{y:.0f}<extra></extra>'),
        go.Bar(x=short_labels, y=class_averages.reindex(scores_above_zero.index).fillna(0).values, 
               name="Class Avg", marker_color='#21918c', text=[f"{v:.0f}" for v in class_averages.reindex(scores_above_zero.index).fillna(0).values], textposition='auto',
               customdata=clean_labels,
               hovertemplate='<b>%{customdata}</b><br>Avg: %{y:.0f}<extra></extra>'),
        go.Bar(x=short_labels, y=class_max.reindex(scores_above_zero.index).fillna(0).values, 
               name="Highest Marks", marker_color='#fde725', text=[f"{v:.0f}" for v in class_max.reindex(scores_above_zero.index).fillna(0).values], textposition='auto',
               customdata=clean_labels,
               hovertemplate='<b>%{customdata}</b><br>Max: %{y:.0f}<extra></extra>')
    ])
    comp_fig.update_layout(
        title_text="📈 Student vs Class Avg vs Highest",
        title_x=0.5,
        title_font=dict(size=16, color='#2c3e50', family='Arial, sans-serif'),
        barmode='group',
        plot_bgcolor='rgba(248,249,250,0.5)',
        paper_bgcolor='white',
        margin=dict(t=60, b=100, l=40, r=40), # Increased bottom margin
        xaxis=dict(
            title="Subjects", 
            titlefont=dict(size=13, color='#667eea'),
            tickangle=-45
        ),
        yaxis=dict(title="Marks", titlefont=dict(size=13, color='#667eea'), gridcolor='#e0e0e0'),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.3,
            xanchor="center",
            x=0.5
        )
    )

    pie_fig = go.Figure(data=[
        go.Pie(
            labels=["Strong (75+)", "Average (50-75)", "Weak (<50)"],
            values=[
                (scores_above_zero > 75).sum(),
                ((scores_above_zero >= 50) & (scores_above_zero <= 75)).sum(),
                (scores_above_zero < 50).sum()
            ],
            marker=dict(colors=['#22c55e', '#f59e0b', '#ef4444']),
            hole=0.4,
            textinfo='label+percent',
            textfont=dict(size=12, color='white', family='Arial, sans-serif'),
            pull=[0.05, 0, 0]
        )
    ])
    pie_fig.update_layout(
        title_text="📊 Performance Distribution", 
        title_x=0.5,
        title_font=dict(size=16, color='#2c3e50', family='Arial, sans-serif'),
        paper_bgcolor='white',
        margin=dict(t=50, b=20, l=20, r=20),
        annotations=[dict(text='Overall', x=0.5, y=0.5, font_size=14, showarrow=False, font_color='#667eea')]
    )

    top_subjects = scores_above_zero.nlargest(3)
    weak_subjects = scores_above_zero.nsmallest(3)
    
    strong_card = dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-trophy-fill me-2", style={"fontSize": "1.2rem", "color": "#000000"}),
            html.Span("Top Subjects", style={"fontSize": "1rem", "color": "#000000"})
        ], className="fw-bold", style={"background": "#16a34a", "borderRadius": "15px 15px 0 0", "padding": "0.75rem 1rem"}),
        dbc.CardBody([
            html.Ul([
                html.Li([
                    html.Div([
                        html.Span(f"{s}", className="fw-bold d-block", style={"color": "#1e293b", "fontSize": "1.05rem"}),
                        html.Span(f"{m:.0f} marks", className="fw-semibold", style={"color": "#000000", "fontSize": "0.95rem"})
                    ])
                ], className="mb-3 pb-2", style={"borderBottom": "1px solid #e0e0e0"}) for s, m in top_subjects.items()
            ], className="mb-0", style={"listStyle": "none", "paddingLeft": "0"})
        ], style={"background": "#86efac", "padding": "1.25rem"})
    ], className="shadow-sm h-100", style={"borderRadius": "15px", "border": "2px solid #22c55e"})
    
    weak_card = dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-exclamation-triangle-fill me-2", style={"fontSize": "1.2rem", "color": "#000000"}),
            html.Span("Bottom Subjects", style={"fontSize": "1rem", "color": "#000000"})
        ], className="fw-bold", style={"background": "#dc2626", "borderRadius": "15px 15px 0 0", "padding": "0.75rem 1rem"}),
        dbc.CardBody([
            html.Ul([
                html.Li([
                    html.Div([
                        html.Span(f"{s}", className="fw-bold d-block", style={"color": "#1e293b", "fontSize": "1.05rem"}),
                        html.Span(f"{m:.0f} marks", className="fw-semibold", style={"color": "#000000", "fontSize": "0.95rem"})
                    ])
                ], className="mb-3 pb-2", style={"borderBottom": "1px solid #e0e0e0"}) for s, m in weak_subjects.items()
            ], className="mb-0", style={"listStyle": "none", "paddingLeft": "0"})
        ], style={"background": "#fca5a5", "padding": "1.25rem"})
    ], className="shadow-sm h-100", style={"borderRadius": "15px", "border": "2px solid #ef4444"})

    # ---------- Result Table ----------
        # ---------- Result Table ----------
    def subject_pass_text(subject_col_name, mark):
        """
        Uses EXACT SAME LOGIC as Result_Selected / Ranking page
        """
        if mark == 0:
            return "N/A"

        # Extract the base subject code (key for credit_dict_all)
        # The col name is "Code Name AnalysisType" or "Code AnalysisType"
        # We need to strip the " AnalysisType" suffix to get the key used in credit dict
        suffix = f" {analysis_type}"
        code = subject_col_name[:-len(suffix)] if subject_col_name.endswith(suffix) else subject_col_name

        credit = credit_dict_all.get(code, 0)
        
        # If not found directly, try fuzzy match or fallback (e.g. if code was split by space before)
        if credit == 0 and ' ' in code:
             # Try first part as fallback (old behavior compatibility)
             short_code = code.split(' ')[0]
             credit = credit_dict_all.get(short_code, 0)

        if credit == 0:
            return "N/A"

        if analysis_type == 'Total':
            internal = pd.to_numeric(
                student_series.get(f"{code} Internal", 0),
                errors='coerce'
            ) or 0

            external = pd.to_numeric(
                student_series.get(f"{code} External", 0),
                errors='coerce'
            ) or 0
            
            # Use short code fallback for internal/external lookups if needed
            if internal == 0 and external == 0 and ' ' in code:
                 short_code = code.split(' ')[0]
                 internal = pd.to_numeric(student_series.get(f"{short_code} Internal", 0), errors='coerce') or 0
                 external = pd.to_numeric(student_series.get(f"{short_code} External", 0), errors='coerce') or 0
                 result_val = str(student_series.get(f"{short_code} Result", "")).strip().upper()
            else:
                 result_val = str(student_series.get(f"{code} Result", "")).strip().upper()

            # 🔑 SAME LOGIC AS RANKING PAGE
            if (internal < 18) or (external < 18):
                return "Pass" if result_val == "P" else "Fail"

            return "Pass"

        else:
            return "Pass" if mark >= 18 else "Fail"


    result_table_df = pd.DataFrame({
        "Subject": scores_above_zero.index,
        "Marks": scores_above_zero.values,
        "Result": [
            subject_pass_text(s, m)
            for s, m in zip(scores_above_zero.index, scores_above_zero.values)
        ],
        "Class Avg": [
            round(class_averages.get(s, 0), 2)
            for s in scores_above_zero.index
        ],
    })


    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in result_table_df.columns],
        style_cell={
            'textAlign': 'center',
            'padding': '12px',
            'font-family': 'Arial, sans-serif',
            'fontSize': 14,
            'whiteSpace': 'normal',
            'border': '1px solid #e0e0e0'
        },
        style_header={
            'backgroundColor': '#1e40af',
            'color': 'white',
            'fontWeight': 'bold',
            'fontSize': 15,
            'textAlign': 'center',
            'border': 'none',
            'padding': '12px'
        },
        style_data_conditional=[
            {'if': {'row_index': 'even'}, 'backgroundColor': '#f8f9fa'},
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#ffffff'},
            {
                'if': {'filter_query': '{Result} = "Pass"', 'column_id': 'Result'},
                'color': 'white',
                'fontWeight': 'bold',
                'backgroundColor': '#22c55e'
            },
            {
                'if': {'filter_query': '{Result} = "Fail"', 'column_id': 'Result'},
                'color': 'white',
                'fontWeight': 'bold',
                'backgroundColor': '#ef4444'
            },
        ],
        page_size=10,
        style_table={'overflowX': 'auto', 'maxHeight': '500px', 'borderRadius': '10px', 'overflow': 'hidden'},
        style_as_list_view=False,
    )

    # ---------- Final Layout ----------
    return dbc.Card(dbc.CardBody([
        # Hero Header
        html.Div([
            html.I(className="bi bi-file-earmark-bar-graph me-3", style={"fontSize": "2rem", "color": "#667eea"}),
            html.H3("Full Performance Report", className="d-inline fw-bold mb-0", style={"color": "#2c3e50"})
        ], className="text-center mb-4 pb-3", style={"borderBottom": "3px solid #667eea"}),
        
        # Student Info & SGPA
        header_row,
        
        # KPI Cards
        html.Div([
            html.H5([
                html.I(className="bi bi-speedometer2 me-2", style={"color": "#667eea"}),
                "Performance Metrics"
            ], className="text-center mb-3 fw-bold", style={"color": "#2c3e50"}),
            kpi_cards_row
        ]),
        
        html.Hr(style={"margin": "2rem 0", "opacity": "0.2"}),
        
        # Insights Section
        html.Div([
            html.H5([
                html.I(className="bi bi-lightbulb-fill me-2", style={"color": "#f59e0b"}),
                "Subject Insights"
            ], className="text-center mb-4 fw-bold", style={"color": "#2c3e50"}),
            dbc.Row([
                dbc.Col(strong_card, md=4, className="mb-3"),
                dbc.Col(weak_card, md=4, className="mb-3"),
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(figure=pie_fig, config={"displayModeBar": False})
                    ])
                ], className="h-100 shadow-custom", style={"borderRadius": "15px"}), md=4, className="mb-3")
            ], className="g-3 justify-content-center")
        ], className="mb-4"),
        
        html.Hr(style={"margin": "2rem 0", "opacity": "0.2"}),
        
        # Charts Section
        html.Div([
            html.H5([
                html.I(className="bi bi-graph-up me-2", style={"color": "#667eea"}),
                "Performance Analysis"
            ], className="text-center mb-4 fw-bold", style={"color": "#2c3e50"}),
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardBody([dcc.Graph(figure=bar_fig, config={"displayModeBar": False})])
                ], className="shadow-custom", style={"borderRadius": "15px"}), md=12, lg=6, className="mb-3"),
                dbc.Col(dbc.Card([
                    dbc.CardBody([dcc.Graph(figure=comp_fig, config={"displayModeBar": False})])
                ], className="shadow-custom", style={"borderRadius": "15px"}), md=12, lg=6, className="mb-3")
            ])
        ], className="mb-4"),
        
        html.Hr(style={"margin": "2rem 0", "opacity": "0.2"}),
        
        # Detailed Table
        html.Div([
            html.H5([
                html.I(className="bi bi-table me-2", style={"color": "#667eea"}),
                "Detailed Performance Table"
            ], className="text-center mb-4 fw-bold", style={"color": "#2c3e50"}),
            dbc.Card([
                dbc.CardBody([
                    result_table
                ], style={"padding": "1.5rem"})
            ], className="shadow-custom", style={"borderRadius": "15px"})
        ])
    ]), className="mt-4 p-4 shadow-custom fade-in", style={"borderRadius": "20px", "background": "white"})