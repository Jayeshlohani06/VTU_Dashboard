import dash
from dash import html, dcc, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import numpy as np
import re

dash.register_page(__name__, path="/student_detail", name="Student Detail")

# ---------- Helper Functions ----------
def extract_numeric(roll):
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges=None):
    """
    Assign section based on roll number and optional section_ranges dict
    e.g. {'A': ('1','50'), 'B': ('51','100')}
    """
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
    html.H2("🎓 Student Detail Lookup", className="text-center mb-4 fw-bold"),

    # 🔍 Control Panel Card
    dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Input(
                    id='student-search',
                    type='text',
                    placeholder='Enter Student ID or Name...',
                    debounce=True,
                    className="form-control"
                ), md=4),
                dbc.Col(dcc.Dropdown(
                    id='student-subject-dropdown',
                    placeholder="Select Subject Code(s)",
                    multi=True
                ), md=5),
                dbc.Col(dbc.Button("Search & Analyze", id='search-btn', color="primary", className="w-100"), md=3)
            ], className="g-2 align-items-center"),
            html.Hr(className="my-3"),
            dbc.Row([
                dbc.Col(html.H6("Select Analysis Type:", className="fw-bold"), width="auto"),
                dbc.Col(dcc.RadioItems(
                    id='analysis-type-radio',
                    options=[
                        {'label': 'Internal Marks', 'value': 'Internal'},
                        {'label': 'External Marks', 'value': 'External'},
                        {'label': 'Total Marks', 'value': 'Total'},
                    ],
                    value='Total',  # Default selection
                    inline=True,
                    labelClassName="me-3",
                    inputClassName="me-1"
                ))
            ], align="center")
        ]),
        className="shadow-sm p-3 mb-4"
    ),

    html.Div(id='student-detail-content'),

    # Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True)

# ---------- Callback: Populate Subject Dropdown with unique codes ----------
@callback(
    Output('student-subject-dropdown', 'options'),
    Output('student-subject-dropdown', 'value'),
    Input('stored-data', 'data'),
    State('overview-selected-subjects', 'data')
)
def populate_subject_dropdown(json_data, subject_components):
    if not json_data or not subject_components:
        return [], []
    
    # Extract unique subject codes
    subject_codes = sorted(list(set([c.split(' ')[0] for c in subject_components])))
    options = [{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in subject_codes]
    return options, ['ALL']

# ---------- Main Callback: Triggered ONLY by Search Button ----------
@callback(
    Output('student-detail-content', 'children'),
    Input('search-btn', 'n_clicks'),
    State('analysis-type-radio', 'value'), # Now a State
    State('student-search', 'value'),
    State('stored-data', 'data'),
    State('student-subject-dropdown', 'value'),
    State('section-data', 'data')
)
def display_student_detail(n_clicks, analysis_type, search_value, json_data, selected_subject_codes, section_ranges):
    if n_clicks is None:
        return html.P("Enter a student ID and click 'Search & Analyze' to begin.", className="text-muted text-center")
        
    if not json_data:
        return html.P("Please upload data first on the Overview page.", className="text-muted text-center")
    if not search_value:
        return html.P("Enter Student ID or Name to begin analysis.", className="text-muted text-center")

    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]

    if 'Student ID' not in df.columns: df.rename(columns={first_col: 'Student ID'}, inplace=True)
    if 'Name' not in df.columns: df['Name'] = ""

    df['Section'] = df['Student ID'].apply(lambda x: assign_section(x, section_ranges))
    
    all_subject_components = [col for col in df.columns if ' ' in col]
    
    if not selected_subject_codes or 'ALL' in selected_subject_codes:
        codes_selected = sorted(list(set([c.split(' ')[0] for c in all_subject_components])))
    else:
        codes_selected = [s for s in selected_subject_codes if s != 'ALL']

    subjects_to_process = [
        col for col in all_subject_components 
        if col.split(' ')[0] in codes_selected and analysis_type in col
    ]
    
    if not subjects_to_process:
        return dbc.Alert(f"No '{analysis_type}' columns found for the selected subjects.", color="warning", className="text-center")

    df[subjects_to_process] = df[subjects_to_process].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    df['Total_Marks_Selected'] = df[subjects_to_process].sum(axis=1)
    
    pass_mark = 18 if analysis_type != 'Total' else 35
    df['Result_Selected'] = df.apply(lambda row: 'Fail' if any(0 < row[c] < pass_mark for c in subjects_to_process) else 'Pass', axis=1)

    df['Class_Rank_Selected'] = df[df['Result_Selected'] == 'Pass']['Total_Marks_Selected'].rank(method='min', ascending=False).astype('Int64')
    df['Section_Rank_Selected'] = df.groupby('Section')['Total_Marks_Selected'].rank(method='min', ascending=False).astype('Int64')

    mask = df.apply(lambda row: search_value.lower() in str(row.get('Student ID', '')).lower()
                    or search_value.lower() in str(row.get('Name', '')).lower(), axis=1)
    student_df = df[mask].reset_index(drop=True)
    if student_df.empty:
        return html.P("No student found with this ID or Name.", className="text-danger text-center")

    student_series = student_df.iloc[0]
    total_marks = student_series['Total_Marks_Selected']
    max_total = len(subjects_to_process) * (50 if analysis_type != 'Total' else 100)
    percentage = (total_marks / max_total) * 100 if max_total > 0 else 0
    result = student_series['Result_Selected']
    
    subject_scores = pd.Series({s: pd.to_numeric(student_series[s], errors='coerce') for s in subjects_to_process}).dropna()
    scores_above_zero = subject_scores[subject_scores > 0]
    
    summary_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6(f"Total {analysis_type} Marks"), html.H3(f"{total_marks}")])), className="shadow-sm text-center bg-light", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Percentage"), html.H3(f"{percentage:.2f}%")])), className="shadow-sm text-center bg-info text-white", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Result"), html.H3(f"{result}")])), className=f"shadow-sm text-center {'bg-success text-white' if result=='Pass' else 'bg-danger text-white'}", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Class Rank"), html.H3(f"{student_series['Class_Rank_Selected']}")])), className="shadow-sm text-center bg-warning", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Section Rank"), html.H3(f"{student_series['Section_Rank_Selected']}")])), className="shadow-sm text-center bg-primary text-white", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Section"), html.H3(f"{student_series['Section']}")])), className="shadow-sm text-center bg-secondary text-white", md=2)
    ], justify="center", className="mb-4 g-3")

    if scores_above_zero.empty:
        return html.Div([ #... UI for no scores ...
        ])

    top_subjects = scores_above_zero.nlargest(3)
    weak_subjects = scores_above_zero.nsmallest(3)

    bar_fig = go.Figure(data=[go.Bar(x=subject_scores.index, y=subject_scores.values, text=subject_scores.values, textposition='auto', marker_color='rgb(26, 118, 255)')])
    bar_fig.update_layout(title_text=f"📊 Subject-wise Performance ({analysis_type} Marks)", title_x=0.5, template='plotly_white', height=400)
    
    strong_card = dbc.Card([dbc.CardHeader("💪 Top 3 Strongest Subjects", className="fw-bold bg-success text-white"), dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark}") for sub, mark in top_subjects.items()])])])
    weak_card = dbc.Card([dbc.CardHeader("⚠️ Bottom 3 Weakest Subjects", className="fw-bold bg-danger text-white"), dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark}") for sub, mark in weak_subjects.items()])])])
    
    class_averages = df[subjects_to_process].replace(0, np.nan).mean()
    
    comp_fig = go.Figure(data=[
        go.Bar(x=subject_scores.index, y=subject_scores.values, name=f"{student_series['Name']} (You)", marker_color="#1f77b4"),
        go.Bar(x=subject_scores.index, y=class_averages.reindex(subject_scores.index), name="Class Average", marker_color="#ff7f0e")
    ])
    comp_fig.update_layout(title_text=f"📈 Student vs Class Average ({analysis_type} Marks)", title_x=0.5, barmode="group", template='plotly_white', height=400)

    pie_fig = go.Figure(data=[go.Pie(
        labels=["Strong (>75)", "Average (50-75)", "Weak (<50)"], 
        values=[(scores_above_zero > 75).sum(), ((scores_above_zero >= 50) & (scores_above_zero <= 75)).sum(), (scores_above_zero < 50).sum()],
        marker=dict(colors=["#28a745", "#ffc107", "#dc3545"]),
        hole=0.4
    )])
    pie_fig.update_layout(title_text="🎯 Performance Distribution", title_x=0.5, template='plotly_white', height=400)

    result_table_df = pd.DataFrame({
        "Subject": subject_scores.index, "Marks": subject_scores.values,
        "Result": ["Pass" if m >= pass_mark else "Fail" for m in subject_scores.values],
        "% Weight": [(m / total_marks * 100 if total_marks > 0 else 0) for m in subject_scores.values],
        "Class Avg": [class_averages.get(s, 0) for s in subject_scores.index],
        "Difference": [m - class_averages.get(s, 0) for s, m in zip(subject_scores.index, subject_scores.values)]
    })

    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in result_table_df.columns],
        style_table={'overflowX': 'auto', 'borderRadius': '8px'}, 
        style_cell={'textAlign': 'center', 'padding': '10px', 'fontFamily': 'sans-serif'},
        style_header={'backgroundColor': '#343a40', 'color': 'white', 'fontWeight': 'bold'},
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}
        ]
    )
    
    student_info = dbc.Card(dbc.CardBody([
        html.H5(f"Student ID: {student_series['Student ID']}"),
        html.H5(f"Name: {student_series['Name']}"),
        html.H5(f"Section: {student_series['Section']}")
    ]), className="mb-4 shadow-sm")

    return dbc.Card(
        dbc.CardBody([
            student_info,
            summary_cards,
            html.Hr(),
            dbc.Row([
                dbc.Col(strong_card, md=6),
                dbc.Col(weak_card, md=6)
            ], className="g-3 mb-4"),
            dcc.Graph(figure=bar_fig),
            html.Hr(),
            dcc.Graph(figure=comp_fig),
            html.Hr(),
            dbc.Row(dbc.Col(dcc.Graph(figure=pie_fig), md=8), justify="center", className="mb-4"),
            html.Hr(),
            html.H5(f"📘 Detailed {analysis_type} Performance", className="text-center mb-3"),
            result_table
        ]),
        className="mt-4 shadow"
    )

