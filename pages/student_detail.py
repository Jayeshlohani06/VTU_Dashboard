import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import re

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
    else: return 0

def extract_numeric(roll):
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges=None):
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
    dbc.Row([
        dbc.Col(html.H2("🎓 Student Detail & SGPA Dashboard", className="mb-1 fw-bold"), md=8),
        dbc.Col(html.Div([
            dbc.Badge("Version: 1.0", color="secondary", className="me-1"),
            dbc.Badge("Interactive", color="info")
        ], className="text-end"), md=4, className="align-self-center")
    ], className="mb-3 align-items-center"),

    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(html.Div([
                    html.Label("Student ID / Name", className="form-label small text-muted"),
                    dcc.Input(id='student-search', type='text', placeholder='USN: 1**YY**XXX', debounce=True, className="form-control")
                ]), md=4),
                dbc.Col(html.Div([
                    html.Label("Subject Codes (choose or leave All)", className="form-label small text-muted"),
                    dcc.Dropdown(id='student-subject-dropdown', placeholder="Select Subject Code(s)", multi=True)
                ]), md=5),
                dbc.Col(html.Div([
                    html.Label(" ", className="form-label small text-muted"),
                    dbc.Button("Search", id='search-btn', color="primary", className="w-100", n_clicks=0)
                ]), md=3)
            ], className="g-2"),
            html.Hr(className="my-3"),
            dbc.Row([
                dbc.Col(html.H6("Analysis Type", className="mb-1 fw-semibold"), width="auto"),
                dbc.Col(dcc.RadioItems(
                    id='analysis-type-radio',
                    options=[
                        {'label': 'Internal', 'value': 'Internal'},
                        {'label': 'External', 'value': 'External'},
                        {'label': 'Total', 'value': 'Total'},
                    ],
                    value='Total',
                    inline=True,
                    labelClassName="me-3",
                    inputClassName="me-1"
                ), md=8)
            ], align="center")
        ]),
        className="shadow-sm mb-4"
    ),
    html.Div(id='credit-input-container'),
    html.Div(id='student-detail-content'),
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True, className="py-3")

# ---------- Populate Subject Dropdown ----------
@callback(
    Output('student-subject-dropdown', 'options'),
    Output('student-subject-dropdown', 'value'),
    Input('stored-data', 'data')
)
def populate_subject_dropdown(json_data):
    if not json_data:
        return [], []
    df = pd.read_json(json_data, orient='split')
    if 'Name' not in df.columns:
        df['Name'] = ""
    exclude_cols = ['Student ID', 'Name', 'Section', df.columns[0]]
    subject_components = [
        c for c in df.columns
        if c not in exclude_cols and 'Rank' not in c and 'Result' not in c and 'Total_Marks' not in c
    ]
    filtered_components = [c for c in subject_components if 'Result' not in c]
    subject_codes = sorted(list(set([c.split(' ')[0] for c in filtered_components])))
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
def generate_credit_inputs(n_clicks, search_value, json_data, selected_subject_codes, analysis_type):
    if not json_data or not search_value:
        return ""
    df = pd.read_json(json_data, orient='split')
    if 'Name' not in df.columns:
        df['Name'] = ""
    # robust search (avoid AttributeError by ensuring Series)
    meta_col = df.columns[0]
    mask = (
        df[meta_col].astype(str).str.contains(search_value, case=False, na=False) |
        df['Name'].astype(str).str.contains(search_value, case=False, na=False)
    )
    student_df = df[mask]
    if student_df.empty:
        return dbc.Alert("No student found with this ID or Name.", color="warning", className="text-center mt-3")
    student_series = student_df.iloc[0]

    all_subject_components = [col for col in df.columns if ' ' in col and 'Result' not in col]
    if not selected_subject_codes or 'ALL' in selected_subject_codes:
        codes_selected = sorted(list(set([c.split(' ')[0] for c in all_subject_components])))
    else:
        codes_selected = [s for s in selected_subject_codes if s != 'ALL']

    subject_codes_for_credits = sorted([
        code for code in codes_selected
        if pd.to_numeric(student_series.get(f"{code} {analysis_type}"), errors='coerce') > 0
    ])
    if not subject_codes_for_credits:
        return dbc.Alert(
            "This student has no scores recorded for the selected subjects.",
            color="info",
            className="text-center mt-3"
        )

    credit_inputs = []
    for code in subject_codes_for_credits:
        credit_inputs.append(
            dbc.Row([
                dbc.Col(html.Label(code, className="fw-bold"), width=5, className="text-end"),
                dbc.Col(
                    dcc.Dropdown(
                        id={'type': 'credit-input-student', 'index': code},
                        options=[{'label': str(i), 'value': i} for i in range(0, 5)],
                        value=3,
                        clearable=False,
                        className="form-select"
                    ), width=4
                ),
                dbc.Col(html.Span("credits", className="text-muted small ms-2"), width=3, className="align-self-center")
            ], className="mb-2")
        )

    card = dbc.Card([
        dbc.CardBody([
            html.H5("Step 2: Enter Subject Credits", className="fw-bold text-center mb-2"),
            html.P("Select credits (0–4) for subjects you want included in SGPA / KPI calculations.",
                   className="text-muted small text-center mb-3"),
            dbc.Row(dbc.Col(credit_inputs), className="mb-2"),
            dbc.Button("Calculate & View Full Report", id='calculate-sgpa-btn', color="success", className="w-100 mt-2")
        ])
    ], className="shadow-sm mb-4 p-2")

    return card

# ---------- Display Full Report ----------
@callback(
    Output('student-detail-content', 'children'),
    Input('calculate-sgpa-btn', 'n_clicks'),
    [
        State('student-search', 'value'),
        State('stored-data', 'data'),
        State('section-data', 'data'),
        State('analysis-type-radio', 'value'),
        State({'type': 'credit-input-student', 'index': ALL}, 'id'),
        State({'type': 'credit-input-student', 'index': ALL}, 'value'),
    ],
    prevent_initial_call=True
)
def display_full_report(n_clicks, search_value, json_data, section_ranges, analysis_type, credit_ids, credit_vals):
    if not all([json_data, search_value]):
        return ""

    # Load & normalize base columns
    df = pd.read_json(json_data, orient='split')
    if 'Name' not in df.columns:
        df['Name'] = ""

    # Normalize identifier column to 'Student ID' (keep original too)
    first_col = df.columns[0]
    if 'Student ID' not in df.columns:
        df.rename(columns={first_col: 'Student ID'}, inplace=True)

    # ---------- ✅ SECTION ASSIGNMENT ----------
    df['Section'] = df['Student ID'].apply(lambda x: assign_section(x, section_ranges))

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
    student_mask = (
        df['Student ID'].astype(str).str.contains(search_value, case=False, na=False) |
        df['Name'].astype(str).str.contains(search_value, case=False, na=False)
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
                    html.I(className=f"{item['icon']} me-2", style={"color": item['color'], "fontSize": "1.2rem"}),
                    html.Small(item["label"], className="text-muted fw-semibold"),
                ]),
                html.H4(item["value"], className="fw-bold mt-2", style={"color": item["color"]}),
            ]),
            style={"backgroundColor": item["bg"], "border": "none", "borderRadius": "12px"},
            className="text-center shadow-sm p-2"
        )
        kpi_cards.append(dbc.Col(card, md=2, sm=4, xs=6, className="mb-3"))

    kpi_cards_row = dbc.Row(kpi_cards, className="g-3 mb-4 justify-content-center")

    # ---------- Header ----------
    header_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5(student_series.get('Name', ''), className="mb-0 text-center"),
            html.H6(f"Student ID: {student_series.get('Student ID', '')}", className="text-muted text-center"),
            html.H6(f"Section: {student_series.get('Section', 'Not Assigned')}", className="text-muted text-center")
        ]), className="mb-3 p-3 shadow-sm"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("SGPA", className="text-muted text-center"),
            html.H2(f"{sgpa:.2f}", className="fw-bold text-info text-center")
        ]), className="mb-3 p-3 shadow-sm"), md=6)
    ], className="mb-4 justify-content-center align-items-center")

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

    bar_fig = go.Figure(data=[
        go.Bar(
            x=scores_above_zero.index,
            y=scores_above_zero.values,
            text=[f"{v:.0f}" for v in scores_above_zero.values],
            textposition='auto',
            marker=dict(color='rgb(31,119,180)')
        )
    ])
    bar_fig.update_layout(
        title_text=f"Subject-wise Performance ({analysis_type})",
        title_x=0.5,
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=20, l=20, r=20)
    )

    class_averages = df[kpi_cols_all].replace(0, pd.NA).mean()
    comp_fig = go.Figure(data=[
        go.Bar(x=scores_above_zero.index, y=scores_above_zero.values, name="Student", marker_color='dodgerblue'),
        go.Bar(x=scores_above_zero.index, y=class_averages.reindex(scores_above_zero.index).fillna(0).values, name="Class Avg", marker_color='orange')
    ])
    comp_fig.update_layout(
        title_text="Student vs Class Average",
        title_x=0.5,
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=20, l=20, r=20)
    )

    pie_fig = go.Figure(data=[
        go.Pie(
            labels=["Strong (75+)", "Average (50-75)", "Weak (<50)"],
            values=[
                (scores_above_zero > 75).sum(),
                ((scores_above_zero >= 50) & (scores_above_zero <= 75)).sum(),
                (scores_above_zero < 50).sum()
            ],
            marker=dict(colors=['#2ecc71', '#f1c40f', '#e74c3c']),
            hole=0.35
        )
    ])
    pie_fig.update_layout(title_text="Performance Distribution", title_x=0.5, margin=dict(t=30, b=10))

    top_subjects = scores_above_zero.nlargest(3)
    weak_subjects = scores_above_zero.nsmallest(3)
    strong_card = dbc.Card([
        dbc.CardHeader("💪 Top Subjects", className="bg-success text-white"),
        dbc.CardBody([html.Ul([html.Li(f"{s}: {m:.0f}") for s, m in top_subjects.items()])])
    ], className="shadow-sm")
    weak_card = dbc.Card([
        dbc.CardHeader("⚠️ Bottom Subjects", className="bg-danger text-white"),
        dbc.CardBody([html.Ul([html.Li(f"{s}: {m:.0f}") for s, m in weak_subjects.items()])])
    ], className="shadow-sm")

    # ---------- Result Table ----------
        # ---------- Result Table ----------
    def subject_pass_text(subject_col_name, mark):
        """
        Uses EXACT SAME LOGIC as Result_Selected / Ranking page
        """

        if mark == 0:
            return "N/A"

        parts = str(subject_col_name).split()
        code = parts[0] if parts else ""

        credit = credit_dict_all.get(code, 0)
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

            result_val = str(
                student_series.get(f"{code} Result", "")
            ).strip().upper()

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
            'padding': '6px',
            'font-family': 'Arial, sans-serif',
            'fontSize': 13,
            'whiteSpace': 'normal'
        },
        style_header={
            'backgroundColor': '#0d6efd',
            'color': 'white',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {'if': {'row_index': 'even'}, 'backgroundColor': '#f8f9fa'},
            {
                'if': {'filter_query': '{Result} = "Pass"', 'column_id': 'Result'},
                'color': 'green',
                'fontWeight': 'bold'
            },
            {
                'if': {'filter_query': '{Result} = "Fail"', 'column_id': 'Result'},
                'color': 'red',
                'fontWeight': 'bold'
            },
        ],
        page_size=8,
        style_table={'overflowX': 'auto', 'maxHeight': '360px'}
    )

    # ---------- Final Layout ----------
    return dbc.Card(dbc.CardBody([
        html.H4("Full Performance Report", className="text-center mb-3"),
        header_row,
        kpi_cards_row,
        html.Hr(),
        dbc.Row([
            dbc.Col(strong_card, md=4, align='center'),
            dbc.Col(weak_card, md=4, align='center'),
            dbc.Col(dbc.Card(dbc.CardBody([dcc.Graph(figure=pie_fig, config={"displayModeBar": False})]),
                             className="h-100 shadow-sm"), md=4, align='center')
        ], className="g-3 mb-4 justify-content-center"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=bar_fig), md=6),
            dbc.Col(dcc.Graph(figure=comp_fig), md=6)
        ], className="mb-4"),
        html.Hr(),
        html.H5("📘 Detailed Performance", className="text-center mb-3"),
        result_table
    ]), className="mt-3 shadow")
