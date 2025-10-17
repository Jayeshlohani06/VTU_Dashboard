import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import re

dash.register_page(__name__, path="/student_detail", name="Student Detail")

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
                    dcc.Input(id='student-search', type='text', placeholder='e.g. 2023-001 or John Doe', debounce=True, className="form-control")
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
    subject_components = [c for c in df.columns if c not in exclude_cols and 'Rank' not in c and 'Result' not in c and 'Total_Marks' not in c]
    filtered_components = [c for c in subject_components if 'Result' not in c]
    subject_codes = sorted(list(set([c.split(' ')[0] for c in filtered_components])))
    options = [{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in subject_codes]
    return options, ['ALL']

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
    mask = df[df.columns[0]].astype(str).str.contains(search_value, case=False, na=False) | df['Name'].astype(str).str.contains(search_value, case=False, na=False)
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
        return dbc.Alert("This student has no scores recorded for the selected subjects.", color="info", className="text-center mt-3")
    credit_inputs = []
    for code in subject_codes_for_credits:
        credit_inputs.append(
            dbc.Row([
                dbc.Col(html.Label(code, className="fw-bold"), width=5, className="text-end"),
                dbc.Col(dcc.Input(id={'type': 'credit-input-student', 'index': code}, type='number', min=0, step=0.5, value=3, className="form-control"), width=4),
                dbc.Col(html.Span("credits", className="text-muted small ms-2"), width=3, className="align-self-center")
            ], className="mb-2")
        )
    card = dbc.Card([
        dbc.CardBody([
            html.H5("Step 2: Enter Subject Credits", className="fw-bold text-center mb-2"),
            html.P("Provide credits for subjects you want included in SGPA / KPI calculations.", className="text-muted small text-center mb-3"),
            dbc.Row(dbc.Col(credit_inputs), className="mb-2"),
            dbc.Button("Calculate & View Full Report", id='calculate-sgpa-btn', color="success", className="w-100 mt-2")
        ])
    ], className="shadow-sm mb-4 p-2")
    return card

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
    df = pd.read_json(json_data, orient='split')
    if 'Name' not in df.columns:
        df['Name'] = ""
    if 'Student ID' not in df.columns:
        df.rename(columns={df.columns[0]: 'Student ID'}, inplace=True)
    df['Section'] = df['Student ID'].apply(lambda x: assign_section(x, section_ranges))
    credit_dict = {cid['index']: cval for cid, cval in zip(credit_ids, credit_vals) if cval is not None and cval > 0}
    codes_with_credits = list(credit_dict.keys())
    if not codes_with_credits:
        return dbc.Alert("Please enter credits > 0 for at least one subject.", color="warning")
    # Use only columns for the selected analysis type
    kpi_cols_to_process = [f"{code} {analysis_type}" for code in codes_with_credits]
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
    if student_df.empty:
        return html.P("Student not found.", className="text-danger")
    student_series = student_df.iloc[0]
    total_credit_points, total_credits = 0, 0
    for code, credit in credit_dict.items():
        grade_point = get_grade_point(student_series.get(f"{code} {analysis_type}", 0))
        total_credit_points += grade_point * credit
        total_credits += credit
    sgpa = (total_credit_points / total_credits) if total_credits > 0 else 0.0
    total_marks = student_series['Total_Marks_Selected']
    percentage = sgpa * 10
    result = student_series['Result_Selected']
    subject_scores = pd.Series({s: pd.to_numeric(student_series.get(s, 0), errors='coerce') for s in visual_cols_to_process}).dropna()
    scores_above_zero = subject_scores[subject_scores > 0]

    kpi_cards_row = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Total Marks", className="text-muted"),
            html.H4(f"{total_marks:.0f}", className="fw-bold")
        ]), className="shadow-sm p-2"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Percentage", className="text-muted"),
            html.H4(f"{percentage:.2f}%", className="fw-bold text-info"),
            dbc.Progress(value=percentage, striped=True, animated=True, style={"height": "10px"}, className="mt-2")
        ]), className="shadow-sm p-2"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Result", className="text-muted"),
            html.H4(result, className=f"fw-bold {'text-success' if result == 'Pass' else 'text-danger'}")
        ]), className="shadow-sm p-2"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Class Rank", className="text-muted"),
            html.H4(student_series.get('Class_Rank_Selected', '—'), className="fw-bold")
        ]), className="shadow-sm p-2"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Section Rank", className="text-muted"),
            html.H4(student_series.get('Section_Rank_Selected', '—'), className="fw-bold")
        ]), className="shadow-sm p-2"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Section", className="text-muted"),
            html.H4(student_series.get('Section', 'Not Assigned'), className="fw-bold")
        ]), className="shadow-sm p-2"), md=2)
    ], className="g-3 mb-4 justify-content-center align-items-center")

    header_row = dbc.Row([
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H5(student_series.get('Name',''), className="mb-0 text-center"),
                html.H6(f"Student ID: {student_series.get('Student ID','')}", className="text-muted text-center"),
                html.H6(f"Section: {student_series.get('Section','Not Assigned')}", className="text-muted text-center"),
            ]), className="mb-3 p-3 shadow-sm"), md=6),  
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6("SGPA", className="text-muted text-center"),
                html.H2(f"{sgpa:.2f}", className="fw-bold text-info text-center")
            ]), className="mb-3 p-3 shadow-sm"), md=6),
    ], className="mb-4 justify-content-center align-items-center")

    if scores_above_zero.empty:
        return dbc.Card(dbc.CardBody([
            html.H4("Full Performance Report", className="text-center mb-3"),
            header_row,
            kpi_cards_row,
            dbc.Alert("No scores > 0 for the selected analysis/subjects.", color="info")
        ]), className="mt-3 shadow")

    bar_fig = go.Figure(data=[go.Bar(
        x=scores_above_zero.index,
        y=scores_above_zero.values,
        text=[f"{v:.0f}" for v in scores_above_zero.values],
        textposition='auto',
        marker=dict(color='rgb(31,119,180)')
    )])
    bar_fig.update_layout(title_text=f"Subject-wise Performance ({analysis_type})", title_x=0.5, plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=20, l=20, r=20))

    class_averages = df[visual_cols_to_process].replace(0, pd.NA).mean()
    comp_fig = go.Figure(data=[
        go.Bar(x=scores_above_zero.index, y=scores_above_zero.values, name="You", marker_color='dodgerblue'),
        go.Bar(x=scores_above_zero.index, y=class_averages.reindex(scores_above_zero.index).fillna(0).values, name="Class Avg", marker_color='orange')
    ])
    comp_fig.update_layout(title_text="Student vs Class Average", title_x=0.5, barmode='group', plot_bgcolor='rgba(0,0,0,0)', margin=dict(t=40, b=20, l=20, r=20))

    pie_fig = go.Figure(data=[go.Pie(labels=["Strong (75+)", "Average (50-75)", "Weak (<50)"],
                                values=[(scores_above_zero > 75).sum(),
                                        ((scores_above_zero >= 50) & (scores_above_zero <= 75)).sum(),
                                        (scores_above_zero < 50).sum()],
                                marker=dict(colors=['#2ecc71', '#f1c40f', '#e74c3c']),
                                hole=0.35)])
    pie_fig.update_layout(title_text="Performance Distribution", title_x=0.5, margin=dict(t=30, b=10))

    top_subjects = scores_above_zero.nlargest(3)
    weak_subjects = scores_above_zero.nsmallest(3)
    strong_card = dbc.Card([dbc.CardHeader("💪 Top Subjects", className="bg-success text-white"), dbc.CardBody([html.Ul([html.Li(f"{s}: {m:.0f}") for s, m in top_subjects.items()])])], className="shadow-sm")
    weak_card = dbc.Card([dbc.CardHeader("⚠️ Weak Subjects", className="bg-danger text-white"), dbc.CardBody([html.Ul([html.Li(f"{s}: {m:.0f}") for s, m in weak_subjects.items()])])], className="shadow-sm")

    def get_result_text(subject_name, mark):
        if mark == 0: return "N/A"
        pass_mark = 35 if 'Total' in subject_name else 18
        return "Pass" if mark >= pass_mark else "Fail"
    result_table_df = pd.DataFrame({
    "Subject": scores_above_zero.index,
    "Marks": scores_above_zero.values,
    "Result": [get_result_text(s, m) for s, m in zip(scores_above_zero.index, scores_above_zero.values)],
    "Class Avg": [round(class_averages.get(s, 0), 2) for s in scores_above_zero.index],
})

    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in result_table_df.columns],
        style_cell={'textAlign': 'center', 'padding': '6px', 'font-family': 'Arial, sans-serif', 'fontSize': 13, 'whiteSpace': 'normal'},
        style_header={'backgroundColor': '#0d6efd','color': 'white','fontWeight': 'bold'},
        style_data_conditional=[
            {'if': {'row_index': 'even'}, 'backgroundColor': '#f8f9fa'},
            {'if': {'filter_query': '{Result} = "Pass"', 'column_id': 'Result'}, 'color': 'green', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Result} = "Fail"', 'column_id': 'Result'}, 'color': 'red', 'fontWeight': 'bold'},
        ],
        page_size=8,
        style_table={'overflowX': 'auto', 'maxHeight': '360px'}
    )

    return dbc.Card(dbc.CardBody([
        html.H4("Full Performance Report", className="text-center mb-3"),
        header_row,
        kpi_cards_row,
        html.Hr(),
        dbc.Row([
            dbc.Col(strong_card, md=4, align='center'),
            dbc.Col(weak_card, md=4, align='center'),
            dbc.Col(dbc.Card(dbc.CardBody([dcc.Graph(figure=pie_fig, config={"displayModeBar": False})]), className="h-100 shadow-sm"), md=4, align='center')
        ], className="g-3 mb-4 justify-content-center"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=bar_fig), md=6),
            dbc.Col(dcc.Graph(figure=comp_fig), md=6)
        ], className="mb-4"),
        html.Hr(),
        html.H5("📘 Detailed Performance", className="text-center mb-3"),
        result_table
    ]), className="mt-3 shadow")
