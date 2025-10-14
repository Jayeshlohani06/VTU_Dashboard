# pages/student_detail.py

import dash
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go
import numpy as np

dash.register_page(__name__, path="/student_detail", name="Student Detail")

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
    dcc.Store(id='overview-selected-subjects', storage_type='session')
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
    State('student-subject-dropdown', 'value')
)
def display_student_detail(n_clicks, search_value, json_data, selected_subjects):
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

    # Filter student row
    mask = df.apply(lambda row: search_value.lower() in str(row.get('Student ID', '')).lower()
                    or search_value.lower() in str(row.get('Name', '')).lower(), axis=1)
    student_df = df[mask]
    if student_df.empty:
        return html.P("No student found with this ID or Name.", className="text-danger text-center")
    student_df = student_df.reset_index(drop=True)

    # Determine subjects to show
    exclude_cols = ['Student ID', 'Name', 'Section', 'Attendance', 'Total_Marks',
                    'Class_Rank', 'Section_Rank', 'Overall_Result']

    all_subjects = [col for col in df.columns if col not in exclude_cols]

    if not selected_subjects or 'ALL' in selected_subjects:
        subjects = all_subjects
    else:
        subjects = [col for col in df.columns if any(col.startswith(s) for s in selected_subjects)]

    # Treat empty cells as NaN
    student_df[subjects] = student_df[subjects].replace(r'^\s*$', np.nan, regex=True)

    # Compute Overall_Result based on Result columns
    result_cols = [c for c in student_df.columns if 'Result' in c and (not selected_subjects or 'ALL' in selected_subjects or any(c.startswith(s) for s in selected_subjects))]
    
    def overall_result(row):
        relevant_results = [v for v in row[result_cols] if pd.notna(v)]
        if not relevant_results:
            return 'Fail'
        return 'Pass' if all(v == 'P' for v in relevant_results) else 'Fail'

    student_df['Overall_Result'] = student_df.apply(overall_result, axis=1)

    # ---------- Total Marks & Percentage ----------
    if not selected_subjects or 'ALL' in selected_subjects:
        total_cols = [c for c in student_df.columns if 'Total' in c]
    else:
        total_cols = []
        for s in selected_subjects:
            matching = [c for c in student_df.columns if s in c and 'Total' in c]
            total_cols.extend(matching)

    student_df['Total_Marks'] = student_df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
    total_marks = student_df.at[0, 'Total_Marks']
    max_total = len(total_cols) * 100
    percentage = (total_marks / max_total) * 100 if max_total > 0 else 0
    result = student_df.at[0, 'Overall_Result']

    # ---------- KPI Cards ----------
    summary_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Marks", className="text-muted"), html.H3(f"{total_marks}")]),
                         className="shadow-sm text-center bg-light"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Percentage", className="text-muted"), html.H3(f"{percentage:.2f}%")]),
                         className="shadow-sm text-center bg-info text-white"), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Result", className="text-muted"), html.H3(f"{result}")]),
                         className=f"shadow-sm text-center {'bg-success text-white' if result=='Pass' else 'bg-danger text-white'}"), md=2)
    ], justify="center", className="mb-4 g-3")

    # ---------- Subject-wise Marks ----------
    subject_marks = [pd.to_numeric(student_df.at[0, s], errors='coerce') if pd.notna(student_df.at[0, s]) else 0 for s in subjects]

    # Ensure numeric Series
    subject_scores = pd.Series(subject_marks, index=subjects).fillna(0)

    # Top and Bottom Subjects
    top_subjects = subject_scores.nlargest(3)
    weak_subjects = subject_scores.nsmallest(3)

    bar_chart = dcc.Graph(
        figure=go.Figure(
            data=[go.Bar(x=subjects, y=subject_marks, text=subject_marks, textposition='auto')],
            layout=go.Layout(title="📊 Subject-wise Performance", xaxis=dict(title="Subjects"), yaxis=dict(title="Marks"), height=400)
        )
    )

    # ---------- Strongest & Weakest Subjects ----------
    strong_card = dbc.Card([
        dbc.CardHeader("💪 Top 3 Strongest Subjects", className="fw-bold bg-success text-white"),
        dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark} marks") for sub, mark in top_subjects.items()])])
    ], className="shadow-sm")

    weak_card = dbc.Card([
        dbc.CardHeader("⚠️ Bottom 3 Weakest Subjects", className="fw-bold bg-danger text-white"),
        dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark} marks") for sub, mark in weak_subjects.items()])])
    ], className="shadow-sm")

    # ---------- Class Average ----------
    class_averages = df[subjects].apply(pd.to_numeric, errors='coerce').fillna(0).mean()
    comparison_chart = dcc.Graph(
        figure=go.Figure(
            data=[
                go.Bar(x=subjects, y=subject_marks, name=f"{student_df.at[0,'Name']} (You)", marker_color="#1f77b4"),
                go.Bar(x=subjects, y=class_averages, name="Class Average", marker_color="#ff7f0e")
            ],
            layout=go.Layout(title="📈 Student vs Class Average", barmode="group", xaxis=dict(title="Subjects"), yaxis=dict(title="Marks"), height=400)
        )
    )

    # ---------- Performance Distribution Pie Chart ----------
    strong = (subject_scores > 75).sum()
    average = ((subject_scores >= 50) & (subject_scores <= 75)).sum()
    weak = (subject_scores < 50).sum()
    pie_chart = dcc.Graph(
        figure=go.Figure(
            data=[go.Pie(labels=["Strong (75+)", "Average (50-75)", "Weak (<50)"],
                         values=[strong, average, weak],
                         marker=dict(colors=["#2ecc71", "#f1c40f", "#e74c3c"]),
                         hole=0.4)],
            layout=go.Layout(title="🎯 Performance Distribution", height=400)
        )
    )

    # ---------- Detailed Table ----------
    result_table_df = pd.DataFrame({
        "Subject": subjects,
        "Marks": subject_marks,
        "Result": ["Pass" if m >= 18 else "Fail" for m in subject_marks],
        "% Weight in Total": [(m / total_marks * 100 if total_marks > 0 else 0) for m in subject_marks],
        "Class Avg": class_averages.round(2).values,
        "Difference from Avg": (np.array(subject_marks) - class_averages.values).round(2)
    })

    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in result_table_df.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        style_header={'backgroundColor': '#007bff', 'color': 'white', 'fontWeight': 'bold'},
        style_data_conditional=[
            {"if": {"filter_query": "{Difference from Avg} > 0", "column_id": "Difference from Avg"},
             "backgroundColor": "#d4edda", "color": "black"},
            {"if": {"filter_query": "{Difference from Avg} < 0", "column_id": "Difference from Avg"},
             "backgroundColor": "#f8d7da", "color": "black"},
            {"if": {"filter_query": "{Result}='Fail'", "column_id": "Result"},
             "backgroundColor": "#f8d7da", "color": "black"},
            {"if": {"filter_query": "{Result}='Pass'", "column_id": "Result"},
             "backgroundColor": "#d4edda", "color": "black"}
        ]
    )

    # ---------- Student Info ----------
    student_info = dbc.Card(dbc.CardBody([
        html.H5(f"Student ID: {student_df.at[0,'Student ID']}"),
        html.H5(f"Name: {student_df.at[0,'Name']}")
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
