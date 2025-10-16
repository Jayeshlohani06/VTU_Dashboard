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
    html.H4("🎓 Student Detail Lookup", className="mb-4 text-center"),

    # 🔍 Student Search & Subject Selection (Aligned in one card)
    dbc.Card(
        dbc.CardBody([
            html.H6("Step 1: Find Student & Select Subjects", className="fw-bold mb-3"),
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
                    placeholder="Select Subject(s)",
                    multi=True
                ), md=6),
                dbc.Col(dbc.Button("Search", id='search-btn', color="primary", className="w-100"), md=2)
            ], className="g-2 align-items-center"),
        ]),
        className="shadow-sm p-3 mb-4"
    ),

    html.Div(id='student-detail-content'),

    # Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True)

# ---------- Callback: Populate Subject Dropdown ----------
@callback(
    Output('student-subject-dropdown', 'options'),
    Output('student-subject-dropdown', 'value'),
    Input('stored-data', 'data'),
)
def populate_subject_dropdown(json_data):
    if not json_data:
        return [], []
    
    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]

    exclude_cols = [first_col, 'Name', 'Section', 'Attendance', 'Total_Marks', 
                    'Class_Rank', 'Section_Rank', 'Overall_Result', 
                    'Total_Marks_Selected', 'Result_Selected', 
                    'Class_Rank_Selected', 'Section_Rank_Selected']

    all_subject_components = sorted([col for col in df.columns if col not in exclude_cols])
    
    options = [{'label': 'Select All', 'value': 'ALL'}] + [{'label': s, 'value': s} for s in all_subject_components]
    return options, ['ALL']  # default select all


# ---------- Callback: Display Student Detail ----------
@callback(
    Output('student-detail-content', 'children'),
    Input('search-btn', 'n_clicks'),
    State('student-search', 'value'),
    State('stored-data', 'data'),
    State('student-subject-dropdown', 'value'),
    State('section-data', 'data')
)
def display_student_detail(n_clicks, search_value, json_data, selected_subject_codes, section_ranges):
    if not json_data:
        return html.P("Please upload data first on the Overview page.", className="text-muted text-center")
    if not search_value:
        return html.P("Enter Student ID or Name to search.", className="text-muted text-center")
    
    # Added check to ensure section data exists
    if not section_ranges:
        return dbc.Alert(
            "Section data not found. Please go to the Overview page to define section ranges first.",
            color="warning",
            className="text-center mt-3"
        )

    df = pd.read_json(json_data, orient='split')
    first_col = df.columns[0]

    # Ensure required columns
    if 'Student ID' not in df.columns:
        df.rename(columns={first_col: 'Student ID'}, inplace=True)
    if 'Name' not in df.columns:
        df['Name'] = ""

    # Assign Section
    df['Section'] = df['Student ID'].apply(lambda x: assign_section(x, section_ranges))
    
    # ---------- Subject Selection Logic ----------
    exclude_cols = ['Student ID', 'Name', 'Section', 'Attendance']
    all_subject_components = [col for col in df.columns if col not in exclude_cols and 'Rank' not in col and 'Result' not in col and 'Total' not in col]

    if not selected_subject_codes or 'ALL' in selected_subject_codes:
        subjects_to_process = all_subject_components
    else:
        # Corrected Logic: Find all component columns that match the selected subject codes
        codes_selected = [s for s in selected_subject_codes if s != 'ALL']
        subjects_to_process = [col for col in all_subject_components if any(col.startswith(code) for code in codes_selected)]
    
    # Ensure subjects_to_process is not empty
    if not subjects_to_process:
        return dbc.Alert("No data columns found for the selected subjects. Please check your selection.", color="warning")


    # Convert only selected subject columns to numeric
    df[subjects_to_process] = df[subjects_to_process].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # ---------- DYNAMICALLY CALCULATE TOTALS AND RANKS BASED ON SELECTION ----------
    # Calculate total marks based ONLY on the selected subjects
    df['Total_Marks_Selected'] = df[subjects_to_process].sum(axis=1)
    
    # Determine result based ONLY on selected subjects (a score of 0 is not a fail)
    df['Result_Selected'] = df.apply(lambda row: 'Fail' if any(0 < row[c] < 18 for c in subjects_to_process) else 'Pass', axis=1)

    # Re-calculate ranks based on the new selected totals
    df['Class_Rank_Selected'] = df[df['Result_Selected'] == 'Pass']['Total_Marks_Selected'].rank(method='min', ascending=False).astype('Int64')
    df['Section_Rank_Selected'] = df.groupby('Section')['Total_Marks_Selected'].rank(method='min', ascending=False).astype('Int64')

    # Filter by student name or ID AFTER all calculations are done
    mask = df.apply(lambda row: search_value.lower() in str(row.get('Student ID', '')).lower()
                    or search_value.lower() in str(row.get('Name', '')).lower(), axis=1)
    student_df = df[mask]
    if student_df.empty:
        return html.P("No student found with this ID or Name.", className="text-danger text-center")
    student_df = student_df.reset_index(drop=True)

    # ---------- Prepare data for display ----------
    student_series = student_df.iloc[0]
    total_marks = student_series['Total_Marks_Selected']
    
    # Corrected Percentage Calculation
    unique_codes_in_selection = set([col.split(' ')[0] for col in subjects_to_process])
    max_total = len(unique_codes_in_selection) * 100 if unique_codes_in_selection else 0
    percentage = (total_marks / max_total) * 100 if max_total > 0 else 0
    result = student_series['Result_Selected']
    
    # CORRECTED LOGIC: Create a series of scores > 0 for all visualizations and analysis
    raw_subject_scores = pd.Series({s: pd.to_numeric(student_series[s], errors='coerce') for s in subjects_to_process}).dropna()
    subject_scores = raw_subject_scores[raw_subject_scores > 0]
    
    # ---------- KPI CARDS (Now using dynamically calculated ranks and totals) ----------
    summary_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Total Marks (Selected)"), html.H3(f"{total_marks}")])), className="shadow-sm text-center bg-light", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Percentage"), html.H3(f"{percentage:.2f}%")])), className="shadow-sm text-center bg-info text-white", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Result (Selected)"), html.H3(f"{result}")])), className=f"shadow-sm text-center {'bg-success text-white' if result=='Pass' else 'bg-danger text-white'}", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Class Rank (Selected)"), html.H3(f"{student_series['Class_Rank_Selected']}")])), className="shadow-sm text-center bg-warning", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Section Rank (Selected)"), html.H3(f"{student_series['Section_Rank_Selected']}")])), className="shadow-sm text-center bg-primary text-white", md=2),
        dbc.Col(dbc.Card(dbc.CardBody([html.H6("Section"), html.H3(f"{student_series['Section']}")])), className="shadow-sm text-center bg-secondary text-white", md=2)
    ], justify="center", className="mb-4 g-3")

    # Handle case where there are no scores to display
    if subject_scores.empty:
        return html.Div([
            dbc.Card(dbc.CardBody([
                html.H5(f"Student ID: {student_series['Student ID']}"),
                html.H5(f"Name: {student_series['Name']}"),
                html.H5(f"Section: {student_series['Section']}")
            ]), className="mb-4 shadow-sm"),
            summary_cards,
            dbc.Alert("No scores above zero found for the selected subjects.", color="info", className="text-center")
        ])

    # ---------- Performance Visualizations ----------
    top_subjects = subject_scores.nlargest(3)
    weak_subjects = subject_scores.nsmallest(3)

    bar_chart = dcc.Graph(figure=go.Figure(data=[go.Bar(x=subject_scores.index, y=subject_scores.values, text=subject_scores.values, textposition='auto')], layout=go.Layout(title="📊 Subject-wise Performance", xaxis=dict(title="Subjects"), yaxis=dict(title="Marks"), height=400)))
    strong_card = dbc.Card([dbc.CardHeader("💪 Top 3 Strongest Subjects", className="fw-bold bg-success text-white"), dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark}") for sub, mark in top_subjects.items()])])], className="shadow-sm")
    weak_card = dbc.Card([dbc.CardHeader("⚠️ Bottom 3 Weakest Subjects", className="fw-bold bg-danger text-white"), dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark}") for sub, mark in weak_subjects.items()])])], className="shadow-sm")
    
    class_averages = df[subjects_to_process].replace(0, np.nan).mean()
    
    comparison_chart = dcc.Graph(figure=go.Figure(
        data=[
            go.Bar(x=subject_scores.index, y=subject_scores.values, name=f"{student_series['Name']} (You)", marker_color="#1f77b4"),
            go.Bar(x=subject_scores.index, y=class_averages.reindex(subject_scores.index), name="Class Average", marker_color="#ff7f0e")
        ],
        layout=go.Layout(title="📈 Student vs Class Average", barmode="group", height=400)
    ))

    strong = (subject_scores > 75).sum()
    average = ((subject_scores >= 50) & (subject_scores <= 75)).sum()
    weak = (subject_scores < 50).sum()
    pie_chart = dcc.Graph(figure=go.Figure(data=[go.Pie(labels=["Strong (75+)", "Average (50-75)", "Weak (<50)"], values=[strong, average, weak], marker=dict(colors=["#2ecc71", "#f1c40f", "#e74c3c"]), hole=0.4)], layout=go.Layout(title="🎯 Performance Distribution", height=400)))

    # ---------- Detailed Table ----------
    result_table_df = pd.DataFrame({
        "Subject": subject_scores.index,
        "Marks": subject_scores.values,
        "Result": ["Pass" if m >= 18 else "Fail" for m in subject_scores.values],
        "% Weight in Total": [(m / total_marks * 100 if total_marks > 0 else 0) for m in subject_scores.values],
        "Class Avg": [class_averages.get(s, 0) for s in subject_scores.index],
        "Difference from Avg": [m - class_averages.get(s, 0) for s, m in zip(subject_scores.index, subject_scores.values)]
    })

    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in result_table_df.columns],
        style_table={'overflowX': 'auto'}, style_cell={'textAlign': 'center'},
        style_header={'backgroundColor': '#007bff', 'color': 'white', 'fontWeight': 'bold'},
        style_data_conditional=[
            {"if": {"filter_query": "{Difference from Avg} > 0", "column_id": "Difference from Avg"}, "backgroundColor": "#d4edda", "color": "black"},
            {"if": {"filter_query": "{Difference from Avg} < 0", "column_id": "Difference from Avg"}, "backgroundColor": "#f8d7da", "color": "black"},
            {"if": {"filter_query": "{Result}='Fail'", "column_id": "Result"}, "backgroundColor": "#f8d7da", "color": "black"},
            {"if": {"filter_query": "{Result}='Pass'", "column_id": "Result"}, "backgroundColor": "#d4edda", "color": "black"}
        ]
    )

    student_info = dbc.Card(dbc.CardBody([
        html.H5(f"Student ID: {student_series['Student ID']}"),
        html.H5(f"Name: {student_series['Name']}"),
        html.H5(f"Section: {student_series['Section']}")
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
        dbc.Row([dbc.Col(pie_chart, md=6)], justify="center", className="g-3"),
        html.Br(),
        html.H5("📘 Detailed Subject Performance", className="text-center mb-2"),
        result_table
    ])

