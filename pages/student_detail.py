# pages/student_detail.py

import dash
from dash import html, dcc, Input, Output, State, dash_table
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
    html.H4("🎓 Student Detail Lookup", className="mb-4 text-center"),

    # 🔍 Student Search
    dbc.Row([
        dbc.Col(dcc.Input(
            id='student-search',
            type='text',
            placeholder='Enter Student ID or Name...',
            debounce=True,
            className="form-control"
        ), md=4),
        dbc.Col(dbc.Button("Search", id='search-btn', color="primary", className="ms-2"), md=2)
    ], justify="center", className="mb-4"),

    # 🔽 Subject Dropdown with Select All
    dbc.Row([
        dbc.Col(dcc.Dropdown(
            id='student-subject-dropdown',
            placeholder="Select Subject(s)",
            multi=True
        ), md=6)
    ], justify="center", className="mb-4"),

    html.Div(id='student-detail-content'),

    # Stores to access uploaded data and overview-selected subjects
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')  # Optional section ranges
], fluid=True)

# ---------- Callback to populate Subject Dropdown ----------
@dash.callback(
    Output('student-subject-dropdown', 'options'),
    Output('student-subject-dropdown', 'value'),
    Input('stored-data', 'data'),
    Input('overview-selected-subjects', 'data')
)
def populate_subject_dropdown(json_data, selected_subjects):
    if not json_data or not selected_subjects:
        return [], []
    options = [{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in selected_subjects]
    value = ['ALL']  # default select all
    return options, value

# ---------- Callback to display student detail ----------
@dash.callback(
    Output('student-detail-content', 'children'),
    Input('search-btn', 'n_clicks'),
    State('student-search', 'value'),
    State('stored-data', 'data'),
    State('student-subject-dropdown', 'value'),
    State('section-data', 'data')
)
def display_student_detail(n_clicks, search_value, json_data, selected_subjects, section_ranges):
    if not json_data:
        return html.P("Please upload data first on the Overview page.", className="text-muted text-center")
    if not search_value:
        return html.P("Enter Student ID or Name to search.", className="text-muted text-center")

    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]

    # Ensure Student ID and Name
    if 'Student ID' not in df.columns:
        df.rename(columns={first_col: 'Student ID'}, inplace=True)
    if 'Name' not in df.columns:
        df['Name'] = ""

    # Assign Section dynamically
    df['Section'] = df['Student ID'].apply(lambda x: assign_section(x, section_ranges))

    # Compute Total Marks
    total_cols = [c for c in df.columns if 'Total' in c or 'Marks' in c or 'Score' in c]
    df[total_cols] = df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df['Total_Marks'] = df[total_cols].sum(axis=1)

    # Compute Overall Result
    result_cols = [c for c in df.columns if 'Result' in c]
    if result_cols:
        df['Overall_Result'] = df[result_cols].apply(lambda row: 'Pass' if all(str(v).strip().upper()=='P' for v in row if pd.notna(v)) else 'Fail', axis=1)
    else:
        df['Overall_Result'] = df.apply(lambda row: 'Fail' if any(row[c]<18 for c in total_cols) else 'Pass', axis=1)

    # Compute Class Rank
    df['Class_Rank'] = df[df['Overall_Result']=='Pass']['Total_Marks'].rank(method='min', ascending=False).astype('Int64')

    # Compute Section Rank based on all students in the section
    df['Section_Rank'] = df.groupby('Section')['Total_Marks'].rank(method='min', ascending=False).astype('Int64')

    # Filter student row
    mask = df.apply(lambda row: search_value.lower() in str(row.get('Student ID','')).lower() 
                    or search_value.lower() in str(row.get('Name','')).lower(), axis=1)
    student_df = df[mask]
    if student_df.empty:
        return html.P("No student found with this ID or Name.", className="text-danger text-center")
    student_df = student_df.reset_index(drop=True)

    # ---------- Subject selection ----------
    exclude_cols = ['Student ID','Name','Section','Attendance','Total_Marks','Class_Rank','Section_Rank','Overall_Result'] + result_cols
    all_subjects = [col for col in df.columns if col not in exclude_cols]

    if not selected_subjects or 'ALL' in selected_subjects:
        subjects = all_subjects
    else:
        subjects = [col for col in df.columns if any(col.startswith(s) for s in selected_subjects)]

    # Treat empty cells or 0 as NaN
    student_df[subjects] = student_df[subjects].replace(r'^\s*$', np.nan, regex=True)
    student_df[subjects] = student_df[subjects].replace(0, np.nan)

    # ---------- KPI Cards ----------
    total_marks = student_df.at[0,'Total_Marks']
    max_total = len(subjects)*100 if subjects else 0
    percentage = (total_marks/max_total)*100 if max_total>0 else 0
    result = student_df.at[0,'Overall_Result']

    summary_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Marks"), html.H3(f"{total_marks}")]), className="shadow-sm text-center bg-light"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Percentage"), html.H3(f"{percentage:.2f}%")]), className="shadow-sm text-center bg-info text-white"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Result"), html.H3(f"{result}")]), className=f"shadow-sm text-center {'bg-success text-white' if result=='Pass' else 'bg-danger text-white'}"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Class Rank"), html.H3(f"{student_df.at[0,'Class_Rank']}")]), className="shadow-sm text-center bg-warning"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Section Rank"), html.H3(f"{student_df.at[0,'Section_Rank']}")]), className="shadow-sm text-center bg-primary text-white"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Section"), html.H3(f"{student_df.at[0,'Section']}")]), className="shadow-sm text-center bg-secondary text-white"), md=2)
    ], justify="center", className="mb-4 g-3")

    # ---------- Subject-wise Performance Charts ----------
    subject_scores = pd.Series({s: pd.to_numeric(student_df.at[0,s], errors='coerce') for s in subjects}).dropna()
    top_subjects = subject_scores.nlargest(3)
    weak_subjects = subject_scores.nsmallest(3)

    bar_chart = dcc.Graph(
        figure=go.Figure(
            data=[go.Bar(x=subject_scores.index, y=subject_scores.values,
                         text=subject_scores.values, textposition='auto')],
            layout=go.Layout(title="📊 Subject-wise Performance", xaxis=dict(title="Subjects"), yaxis=dict(title="Marks"), height=400)
        )
    )

    strong_card = dbc.Card([dbc.CardHeader("💪 Top 3 Strongest Subjects", className="fw-bold bg-success text-white"),
                            dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark}") for sub, mark in top_subjects.items()])])], className="shadow-sm")
    weak_card = dbc.Card([dbc.CardHeader("⚠️ Bottom 3 Weakest Subjects", className="fw-bold bg-danger text-white"),
                          dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark}") for sub, mark in weak_subjects.items()])])], className="shadow-sm")

    class_averages = df[subjects].apply(pd.to_numeric, errors='coerce').replace(0,np.nan).mean()
    comparison_chart = dcc.Graph(
        figure=go.Figure(
            data=[
                go.Bar(x=subject_scores.index, y=subject_scores.values, name=f"{student_df.at[0,'Name']} (You)", marker_color="#1f77b4"),
                go.Bar(x=subjects, y=class_averages, name="Class Average", marker_color="#ff7f0e")
            ],
            layout=go.Layout(title="📈 Student vs Class Average", barmode="group", height=400)
        )
    )

    # Performance Pie
    strong = (subject_scores>75).sum()
    average = ((subject_scores>=50)&(subject_scores<=75)).sum()
    weak = (subject_scores<50).sum()
    pie_chart = dcc.Graph(
        figure=go.Figure(data=[go.Pie(labels=["Strong (75+)","Average (50-75)","Weak (<50)"],
                                      values=[strong,average,weak],
                                      marker=dict(colors=["#2ecc71","#f1c40f","#e74c3c"]), hole=0.4)],
                         layout=go.Layout(title="🎯 Performance Distribution", height=400))
    )

    # Detailed Table
    result_table_df = pd.DataFrame({
        "Subject": subject_scores.index,
        "Marks": subject_scores.values,
        "Result": ["Pass" if m>=18 else "Fail" for m in subject_scores.values],
        "% Weight in Total": [(m/total_marks*100 if total_marks>0 else 0) for m in subject_scores.values],
        "Class Avg": [class_averages[s] for s in subject_scores.index],
        "Difference from Avg": [m-class_averages[s] for s,m in zip(subject_scores.index, subject_scores.values)]
    })

    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i,"id":i} for i in result_table_df.columns],
        style_table={'overflowX':'auto'},
        style_cell={'textAlign':'center'},
        style_header={'backgroundColor':'#007bff','color':'white','fontWeight':'bold'},
        style_data_conditional=[
            {"if":{"filter_query":"{Difference from Avg} > 0","column_id":"Difference from Avg"},
             "backgroundColor":"#d4edda","color":"black"},
            {"if":{"filter_query":"{Difference from Avg} < 0","column_id":"Difference from Avg"},
             "backgroundColor":"#f8d7da","color":"black"},
            {"if":{"filter_query":"{Result}='Fail'","column_id":"Result"},
             "backgroundColor":"#f8d7da","color":"black"},
            {"if":{"filter_query":"{Result}='Pass'","column_id":"Result"},
             "backgroundColor":"#d4edda","color":"black"}
        ]
    )

    # Student Info Card
    student_info = dbc.Card(dbc.CardBody([
        html.H5(f"Student ID: {student_df.at[0,'Student ID']}"),
        html.H5(f"Name: {student_df.at[0,'Name']}"),
        html.H5(f"Section: {student_df.at[0,'Section']}")
    ]), className="mb-4 shadow-sm")

    return html.Div([
        student_info,
        summary_cards,
        dbc.Row([dbc.Col(strong_card, md=6), dbc.Col(weak_card, md=6)], className="g-3"),
        html.Br(),
        bar_chart,
        html.Br(),
        comparison_chart,
        html.Br(),
        dbc.Row([dbc.Col(pie_chart, md=6)], className="g-3"),
        html.Br(),
        html.H5("📘 Detailed Subject Performance", className="text-center mb-2"),
        result_table
    ])
