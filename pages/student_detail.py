import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import numpy as np
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
    return "N/A"

# ---------- Layout ----------
layout = dbc.Container([
    html.H2("🎓 Student Detail & SGPA Dashboard", className="text-center mb-4 fw-bold"),

    # Step 1: Search & Select
    dbc.Card(
        dbc.CardBody([
            html.H5("Step 1: Find Student & Select Analysis", className="fw-bold mb-3"),
            dbc.Row([
                dbc.Col(dcc.Input(id='student-search', type='text', placeholder='Enter Student ID or Name...', debounce=True, className="form-control"), md=4),
                dbc.Col(dcc.Dropdown(id='student-subject-dropdown', placeholder="Select Subject Code(s)", multi=True), md=5),
                dbc.Col(dbc.Button("Search", id='search-btn', color="primary", className="w-100"), md=3)
            ], className="g-2 align-items-center"),
            html.Hr(className="my-3"),
            dbc.Row([
                dbc.Col(html.H6("Select Analysis Type:", className="fw-bold"), width="auto"),
                dbc.Col(dcc.RadioItems(
                    id='analysis-type-radio',
                    options=[
                        {'label': 'Internal Marks', 'value': 'Internal'},
                        {'label': 'External Marks', 'value': 'External'},
                        {'label': 'Total Breakdown', 'value': 'Total'},
                    ],
                    value='Total',
                    inline=True,
                    labelClassName="me-3",
                    inputClassName="me-1"
                ))
            ], align="center")
        ]),
        className="shadow-sm p-3 mb-4"
    ),

    # Step 2: Credit Inputs
    html.Div(id='credit-input-container'),

    # Step 3: Full Report
    html.Div(id='student-detail-content'),

    # Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True, className="py-4")

# ---------- CALLBACKS ----------

# 1. Populate Subject Dropdown
@callback(
    Output('student-subject-dropdown', 'options'),
    Output('student-subject-dropdown', 'value'),
    Input('stored-data', 'data')
)
def populate_subject_dropdown(json_data):
    if not json_data: return [], []
    df = pd.read_json(json_data, orient='split')
    if 'Name' not in df.columns:
        df['Name'] = ""
    exclude_cols = ['Student ID', 'Name', 'Section', df.columns[0]]
    subject_components = [c for c in df.columns if c not in exclude_cols and 'Rank' not in c and 'Result' not in c and 'Total_Marks' not in c]
    filtered_components = [c for c in subject_components if 'Result' not in c]
    subject_codes = sorted(list(set([c.split(' ')[0] for c in filtered_components])))
    options = [{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in subject_codes]
    return options, ['ALL']

# 2. Generate Credit Inputs
@callback(
    Output('credit-input-container', 'children'),
    Input('search-btn', 'n_clicks'),
    State('student-search', 'value'),
    State('stored-data', 'data'),
    State('student-subject-dropdown', 'value'),
    prevent_initial_call=True
)
def generate_credit_inputs(n_clicks, search_value, json_data, selected_subject_codes):
    if not json_data or not search_value: return ""
    df = pd.read_json(json_data, orient='split')
    if 'Name' not in df.columns: df['Name'] = ""
    
    mask = df[df.columns[0]].astype(str).str.contains(search_value, case=False, na=False) | \
           df['Name'].astype(str).str.contains(search_value, case=False, na=False)
    student_df = df[mask]
    if student_df.empty:
        return dbc.Alert("No student found with this ID or Name.", color="warning", className="text-center mt-3")

    student_series = student_df.iloc[0]
    all_subject_components = [col for col in df.columns if ' ' in col and 'Result' not in col]
    if not selected_subject_codes or 'ALL' in selected_subject_codes:
        codes_selected = sorted(list(set([c.split(' ')[0] for c in all_subject_components])))
    else:
        codes_selected = [s for s in selected_subject_codes if s != 'ALL']

    subject_codes_for_credits = sorted([code for code in codes_selected if pd.to_numeric(student_series.get(f"{code} Total"), errors='coerce') > 0])
    if not subject_codes_for_credits:
        return dbc.Alert("This student has no scores recorded for the selected subjects.", color="info", className="text-center mt-3")

    credit_inputs = [dbc.Row([
        dbc.Col(dbc.Label(code, className="fw-bold"), width=6, className="text-md-end"),
        dbc.Col(dcc.Input(id={'type': 'credit-input-student', 'index': code}, type='number', min=0, step=0.5, value=3, className="form-control"), width=6)
    ], className="mb-2 align-items-center") for code in subject_codes_for_credits]

    return dbc.Card(dbc.CardBody([
        html.H5("Step 2: Enter Subject Credits", className="fw-bold text-center mb-3"),
        html.P("SGPA and all other metrics will be calculated based on subjects with credits > 0.", className="text-muted text-center small"),
        *credit_inputs,
        dbc.Button("Calculate & View Full Report", id='calculate-sgpa-btn', color="success", className="w-100 mt-3")
    ]), className="shadow-sm p-3 mt-4")

# 3. Display Full Report
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
    if not all([json_data, search_value]): return ""
    
    df = pd.read_json(json_data, orient='split')
    if 'Name' not in df.columns: df['Name'] = ""
    if 'Student ID' not in df.columns: df.rename(columns={df.columns[0]: 'Student ID'}, inplace=True)
    
    df['Section'] = df['Student ID'].apply(lambda x: assign_section(x, section_ranges))
    credit_dict = {cid['index']: cval for cid, cval in zip(credit_ids, credit_vals) if cval is not None and cval > 0}
    codes_with_credits = list(credit_dict.keys())
    if not codes_with_credits: return dbc.Alert("Please enter credits > 0 for at least one subject.", color="warning")

    kpi_cols_to_process = [f"{code} {analysis_type}" for code in codes_with_credits if analysis_type != 'Total']
    if analysis_type == 'Total':
        kpi_cols_to_process = [f"{code} Total" for code in codes_with_credits]
        visual_cols_to_process = [col for col in df.columns if col.split(' ')[0] in codes_with_credits and 'Result' not in col]
    else:
        visual_cols_to_process = kpi_cols_to_process
    
    all_cols_to_process = list(set(kpi_cols_to_process + visual_cols_to_process))
    df[all_cols_to_process] = df[all_cols_to_process].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    df['Total_Marks_Selected'] = df[kpi_cols_to_process].sum(axis=1)
    pass_mark_kpi = 18 if analysis_type != 'Total' else 35
    df['Result_Selected'] = df.apply(lambda row: 'Fail' if any(0 < row[c] < pass_mark_kpi for c in kpi_cols_to_process) else 'Pass', axis=1)
    df['Class_Rank_Selected'] = df[df['Result_Selected'] == 'Pass']['Total_Marks_Selected'].rank(method='min', ascending=False).astype('Int64')
    df['Section_Rank_Selected'] = df.groupby('Section')['Total_Marks_Selected'].rank(method='min', ascending=False).astype('Int64')

    mask = df['Student ID'].astype(str).str.contains(search_value, case=False, na=False) | df['Name'].astype(str).str.contains(search_value, case=False, na=False)
    student_df = df[mask].reset_index(drop=True)
    if student_df.empty: return html.P("Student not found.", className="text-danger")
    student_series = student_df.iloc[0]

    # SGPA Calculation
    total_credit_points, total_credits = 0, 0
    for code, credit in credit_dict.items():
        grade_point = get_grade_point(student_series[f"{code} Total"])
        total_credit_points += grade_point * credit
        total_credits += credit
    sgpa = (total_credit_points / total_credits) if total_credits > 0 else 0.0

    total_marks = student_series['Total_Marks_Selected']
    max_total = len(kpi_cols_to_process) * (50 if analysis_type != 'Total' else 100)
    percentage = (total_marks / max_total) * 100 if max_total > 0 else 0
    result = student_series['Result_Selected']

    subject_scores = pd.Series({s: pd.to_numeric(student_series[s], errors='coerce') for s in visual_cols_to_process}).dropna()
    scores_above_zero = subject_scores[subject_scores > 0]

    # KPI Row
    kpi_row = dbc.Card(dbc.Row([
        dbc.Col(html.Div([html.H6("Total Marks", className="text-muted"), html.H3(f"{total_marks:.0f}", className="fw-bold")]), className="text-center"),
        dbc.Col(html.Div([html.H6("Percentage", className="text-muted"), html.H3(f"{percentage:.2f}%", className="fw-bold text-info")]), className="text-center"),
        dbc.Col(html.Div([html.H6("Result", className="text-muted"), html.H3(result, className=f"fw-bold {'text-success' if result == 'Pass' else 'text-danger'}")]), className="text-center"),
        dbc.Col(html.Div([html.H6("Class Rank", className="text-muted"), html.H3(student_series['Class_Rank_Selected'], className="fw-bold")]), className="text-center"),
        dbc.Col(html.Div([html.H6("Section Rank", className="text-muted"), html.H3(student_series['Section_Rank_Selected'], className="fw-bold")]), className="text-center"),
        dbc.Col(html.Div([html.H6("Section", className="text-muted"), html.H3(student_series['Section'], className="fw-bold")]), className="text-center")
    ], className="g-0"), body=True, className="mb-4 shadow-sm p-2")

    sgpa_card = dbc.Card(dbc.CardBody([html.H6("SGPA"), html.H2(f"{sgpa:.2f}", className="text-info fw-bold")]), className="text-center shadow-sm p-3")
    student_info = dbc.Card(dbc.CardBody([
        html.H5(f"Student ID: {student_series['Student ID']}"),
        html.H5(f"Name: {student_series['Name']}"),
        html.H5(f"Section: {student_series['Section']}")
    ]), className="mb-4 shadow-sm p-3")

    if scores_above_zero.empty:
        return html.Div([student_info, kpi_row, dbc.Row(dbc.Col(sgpa_card, md=4), justify="center"), dbc.Alert("No scores > 0.", color="info")])

    # Graphs
    top_subjects = scores_above_zero.nlargest(3)
    weak_subjects = scores_above_zero.nsmallest(3)
    bar_fig = go.Figure(data=[go.Bar(x=subject_scores.index, y=subject_scores.values, text=subject_scores.values, textposition='auto', marker_color='cornflowerblue')])
    bar_fig.update_layout(title_text=f"📊 Subject-wise Performance ({analysis_type} Breakdown)", title_x=0.5, plot_bgcolor='rgba(0,0,0,0)')

    strong_card = dbc.Card([dbc.CardHeader("💪 Top 3 Strongest", className="bg-success text-white"), dbc.CardBody([html.Ul([html.Li(f"{s}: {m}") for s, m in top_subjects.items()])])])
    weak_card = dbc.Card([dbc.CardHeader("⚠️ Bottom 3 Weakest", className="bg-danger text-white"), dbc.CardBody([html.Ul([html.Li(f"{s}: {m}") for s, m in weak_subjects.items()])])])

    class_averages = df[visual_cols_to_process].replace(0, np.nan).mean()
    comp_fig = go.Figure(data=[
        go.Bar(x=subject_scores.index, y=subject_scores.values, name="You", marker_color='dodgerblue'),
        go.Bar(x=subject_scores.index, y=class_averages.reindex(subject_scores.index), name="Class Average", marker_color='orange')
    ])
    comp_fig.update_layout(title_text="📈 Student vs Class Average", title_x=0.5, barmode="group", plot_bgcolor='rgba(0,0,0,0)')

    pie_fig = go.Figure(data=[go.Pie(labels=["Strong", "Avg", "Weak"],
                                     values=[(scores_above_zero > 75).sum(),
                                             ((scores_above_zero >= 50) & (scores_above_zero <= 75)).sum(),
                                             (scores_above_zero < 50).sum()],
                                     marker_colors=['green','gold','red'])])
    pie_fig.update_layout(title_text="🎯 Performance Distribution", title_x=0.5)

    def get_result_text(subject_name, mark):
        if mark == 0: return "N/A"
        pass_mark = 35 if 'Total' in subject_name else 18
        return "Pass" if mark >= pass_mark else "Fail"

    result_table_df = pd.DataFrame({
        "Subject": subject_scores.index, 
        "Marks": subject_scores.values,
        "Result": [get_result_text(s, m) for s, m in zip(subject_scores.index, subject_scores.values)],
        "Class Avg": [class_averages.get(s, 0) for s in subject_scores.index],
    })

    # ----------------- Enhanced DataTable -----------------
    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in result_table_df.columns],
        style_cell={'textAlign': 'center', 'padding': '8px', 'font-family': 'Arial, sans-serif', 'fontSize': 14, 'whiteSpace': 'normal', 'height': 'auto'},
        style_header={'backgroundColor': '#007bff','color': 'white','fontWeight': 'bold','textAlign': 'center','border': '1px solid #dee2e6'},
        style_data={'backgroundColor': '#f9f9f9','color': 'black','border': '1px solid #dee2e6'},
        style_data_conditional=[
            {'if': {'row_index': 'even'}, 'backgroundColor': '#e9ecef'},
            {'if': {'filter_query': '{Result} = "Pass"', 'column_id': 'Result'}, 'color': 'green', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Result} = "Fail"', 'column_id': 'Result'}, 'color': 'red', 'fontWeight': 'bold'},
            {'if': {'state': 'active'}, 'backgroundColor': '#d1ecf1', 'color': 'black'}
        ],
        page_size=10,
        fixed_rows={'headers': True},
        style_table={'overflowX': 'auto', 'maxHeight': '400px'},
    )

    return dbc.Card(dbc.CardBody([
        html.H4("Full Performance Report", className="text-center mb-4"),
        student_info,
        kpi_row,
        dbc.Row(dbc.Col(sgpa_card, md=4), justify="center", className="mb-4"),
        html.Hr(),
        dbc.Row([dbc.Col(strong_card, md=6), dbc.Col(weak_card, md=6)], className="g-3 mb-4"),
        dcc.Graph(figure=bar_fig),
        html.Hr(),
        dcc.Graph(figure=comp_fig),
        html.Hr(),
        dbc.Row(dbc.Col(dcc.Graph(figure=pie_fig), md=8), justify="center", className="mb-4"),
        html.Hr(),
        html.H5("📘 Detailed Performance", className="text-center mb-3"),
        result_table
    ]), className="mt-4 shadow p-3")
