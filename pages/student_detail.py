import dash
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go

dash.register_page(__name__, path="/student_detail", name="Student Detail")

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("🎓 Student Detail Lookup", className="mb-4 text-center"),

    # 🔍 Search Section
    dbc.Row([
        dbc.Col(dcc.Input(
            id='student-search',
            type='text',
            placeholder='Enter Student ID or Name...',
            debounce=True,
            className="form-control"
        ), md=6),
        dbc.Col(dbc.Button("Search", id='search-btn', color="primary", className="ms-2"), md=2)
    ], justify="center", className="mb-4"),

    html.Div(id='student-detail-content')
], fluid=True)


# ---------- Callback ----------
@dash.callback(
    Output('student-detail-content', 'children'),
    Input('search-btn', 'n_clicks'),
    State('student-search', 'value'),
    State('stored-data', 'data')
)
def display_student_detail(n_clicks, search_value, json_data):
    if not json_data:
        return html.P("Please upload data first on the Overview page.", className="text-muted text-center")

    if not search_value:
        return html.P("Enter Student ID or Name to search.", className="text-muted text-center")

    df = pd.read_json(json_data, orient='split')

    # Ensure Student ID and Name columns
    if 'Student ID' not in df.columns:
        df.rename(columns={df.columns[0]: 'Student ID'}, inplace=True)
    if 'Name' not in df.columns:
        df['Name'] = ""

    # Filter the student row
    mask = df.apply(lambda row: search_value.lower() in str(row.get('Student ID', '')).lower()
                    or search_value.lower() in str(row.get('Name', '')).lower(), axis=1)
    student_df = df[mask]
    if student_df.empty:
        return html.P("No student found with this ID or Name.", className="text-danger text-center")

    student_df = student_df.reset_index(drop=True)

    # Identify subjects dynamically
    exclude_cols = ['Student ID', 'Name', 'Section', 'Attendance', 'Total_Marks',
                    'Class_Rank', 'Section_Rank', 'Overall_Result']
    subjects = [col for col in df.columns if col not in exclude_cols]

    # --- Extract Info ---
    student_id = student_df.at[0, 'Student ID']
    name = student_df.at[0, 'Name']
    section = student_df.at[0, 'Section'] if 'Section' in student_df.columns else 'N/A'
    total_marks = student_df.at[0, 'Total_Marks'] if 'Total_Marks' in student_df.columns else 0
    class_rank = student_df.at[0, 'Class_Rank'] if 'Class_Rank' in student_df.columns else 'N/A'
    section_rank = student_df.at[0, 'Section_Rank'] if 'Section_Rank' in student_df.columns else 'N/A'
    result = student_df.at[0, 'Overall_Result'] if 'Overall_Result' in student_df.columns else 'N/A'

    # Compute percentage dynamically
    max_total = len(subjects) * 100 if subjects else 1
    percentage = (total_marks / max_total) * 100

    # ---------- 🎯 Performance Summary ----------
    summary_cards = dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Total Marks", className="card-title text-muted"),
                                        html.H3(f"{total_marks}")])],
                         className="shadow-sm text-center border-0 bg-light"), md=2),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Percentage", className="card-title text-muted"),
                                        html.H3(f"{percentage:.2f}%")])],
                         className="shadow-sm text-center border-0 bg-info text-white"), md=2),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Class Rank", className="card-title text-muted"),
                                        html.H3(f"{class_rank}")])],
                         className="shadow-sm text-center border-0 bg-warning"), md=2),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Section Rank", className="card-title text-muted"),
                                        html.H3(f"{section_rank}")])],
                         className="shadow-sm text-center border-0 bg-primary text-white"), md=2),
        dbc.Col(dbc.Card([dbc.CardBody([html.H6("Result", className="card-title text-muted"),
                                        html.H3(f"{result}")])],
                         className=f"shadow-sm text-center border-0 {'bg-success text-white' if str(result).lower() == 'pass' else 'bg-danger text-white'}"), md=2)
    ], justify="center", className="mb-4 g-3")

    # ---------- 📘 Subject-wise Marks ----------
    # Convert subject marks to numeric to avoid nlargest error
    subject_marks = [pd.to_numeric(student_df.at[0, s], errors='coerce') or 0 for s in subjects]
    bar_chart = dcc.Graph(
        figure={
            "data": [go.Bar(
                x=subjects,
                y=subject_marks,
                marker_color="#1f77b4",
                text=[f"{m}" for m in subject_marks],
                textposition='auto'
            )],
            "layout": go.Layout(
                title="📊 Subject-wise Performance",
                xaxis={"title": "Subjects"},
                yaxis={"title": "Marks"},
                height=400
            )
        }
    )

    # ---------- 🧠 Strongest & Weakest Subjects ----------
    subject_scores = pd.Series(subject_marks, index=subjects)
    top_subjects = subject_scores.nlargest(3)
    weak_subjects = subject_scores.nsmallest(3)

    strong_card = dbc.Card([dbc.CardHeader("💪 Top 3 Strongest Subjects", className="fw-bold bg-success text-white"),
                            dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark} marks") for sub, mark in top_subjects.items()])])],
                           className="shadow-sm")

    weak_card = dbc.Card([dbc.CardHeader("⚠️ Bottom 3 Weakest Subjects", className="fw-bold bg-danger text-white"),
                          dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark} marks") for sub, mark in weak_subjects.items()])])],
                         className="shadow-sm")

    # ---------- 📈 Compare with Class Average ----------
    class_averages = df[subjects].apply(pd.to_numeric, errors='coerce').fillna(0).mean()
    comparison_chart = dcc.Graph(
        figure={
            "data": [
                go.Bar(x=subjects, y=subject_marks, name=f"{name} (You)", marker_color="#1f77b4"),
                go.Bar(x=subjects, y=class_averages, name="Class Average", marker_color="#ff7f0e")
            ],
            "layout": go.Layout(
                title="📈 Student vs Class Average",
                barmode="group",
                xaxis={"title": "Subjects"},
                yaxis={"title": "Marks"},
                height=400
            )
        }
    )

    # ---------- 🧾 Basic Info ----------
    student_info = dbc.Card([dbc.CardBody([html.H5(f"Student ID: {student_id}"),
                                           html.H5(f"Name: {name}"),
                                           html.H5(f"Section: {section}")])],
                            className="mb-4 shadow-sm")

    # ---------- Combine Everything ----------
    return html.Div([
        student_info,
        summary_cards,
        html.Hr(),
        bar_chart,
        html.Br(),
        dbc.Row([dbc.Col(strong_card, md=6), dbc.Col(weak_card, md=6)], className="g-3"),
        html.Br(),
        comparison_chart
    ])
