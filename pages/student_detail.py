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

    # Identify subjects dynamically (exclude metadata columns)
    exclude_cols = ['Student ID', 'Name', 'Section', 'Attendance', 'Total_Marks',
                    'Class_Rank', 'Section_Rank', 'Overall_Result']
    subjects = [col for col in df.columns if col not in exclude_cols]

    # --- Extract Info ---
    student_id = student_df.at[0, 'Student ID']
    name = student_df.at[0, 'Name']
    section = student_df.at[0, 'Section'] if 'Section' in student_df.columns else 'N/A'
    total_marks = student_df.at[0, 'Total_Marks'] if 'Total_Marks' in student_df.columns else sum([pd.to_numeric(student_df.at[0, s], errors='coerce') or 0 for s in subjects])
    class_rank = student_df.at[0, 'Class_Rank'] if 'Class_Rank' in student_df.columns else 'N/A'
    section_rank = student_df.at[0, 'Section_Rank'] if 'Section_Rank' in student_df.columns else 'N/A'
    result = student_df.at[0, 'Overall_Result'] if 'Overall_Result' in student_df.columns else 'N/A'

    max_total = len(subjects) * 100
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
    subject_marks = [pd.to_numeric(student_df.at[0, s], errors='coerce') or 0 for s in subjects]
    subject_scores = pd.Series(subject_marks, index=subjects)

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
    top_subjects = subject_scores.nlargest(3)
    weak_subjects = subject_scores.nsmallest(3)

    strong_card = dbc.Card([
        dbc.CardHeader("💪 Top 3 Strongest Subjects", className="fw-bold bg-success text-white"),
        dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark} marks") for sub, mark in top_subjects.items()])])
    ], className="shadow-sm")

    weak_card = dbc.Card([
        dbc.CardHeader("⚠️ Bottom 3 Weakest Subjects", className="fw-bold bg-danger text-white"),
        dbc.CardBody([html.Ul([html.Li(f"{sub}: {mark} marks") for sub, mark in weak_subjects.items()])])
    ], className="shadow-sm")

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

    # ---------- 🥧 Performance Distribution Pie Chart ----------
    strong = (subject_scores > 75).sum()
    average = ((subject_scores >= 50) & (subject_scores <= 75)).sum()
    weak = (subject_scores < 50).sum()

    pie_chart = dcc.Graph(
        figure=go.Figure(
            data=[go.Pie(
                labels=["Strong (75+)", "Average (50-75)", "Weak (<50)"],
                values=[strong, average, weak],
                marker=dict(colors=["#2ecc71", "#f1c40f", "#e74c3c"]),
                hole=0.4
            )],
            layout=go.Layout(title="🎯 Performance Distribution", height=400)
        )
    )

    # ---------- 🧾 Detailed Table with Student ID, Result, % Weight, Class Avg, Difference ----------
    result_table_df = pd.DataFrame({
        "Student ID": [student_id]*len(subjects),
        "Subject": subjects,
        "Marks": subject_marks,
        "Result": ["Pass" if m >= 50 else "Fail" for m in subject_marks],
        "% Weight in Total": [(m/total_marks*100 if total_marks>0 else 0) for m in subject_marks],
        "Class Avg": class_averages.round(2).values,
        "Difference from Avg": (np.array(subject_marks) - class_averages.values).round(2)
    })

    style_data_conditional = [
        {"if": {"filter_query": "{Difference from Avg} > 0", "column_id": "Difference from Avg"},
         "backgroundColor": "#d4edda", "color": "black"},
        {"if": {"filter_query": "{Difference from Avg} < 0", "column_id": "Difference from Avg"},
         "backgroundColor": "#f8d7da", "color": "black"}
    ]

    result_table = dash_table.DataTable(
        data=result_table_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in result_table_df.columns],
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center'},
        style_header={'backgroundColor': '#007bff', 'color': 'white', 'fontWeight': 'bold'},
        style_data_conditional=style_data_conditional
    )

    # ---------- 🧠 Performance Insights ----------
    avg_marks = np.mean(subject_marks)
    if avg_marks >= 85:
        insights = f"{name} has shown outstanding academic performance! Keep up the excellent work."
    elif avg_marks >= 60:
        insights = f"{name} has performed well but can further improve by focusing on weaker subjects."
    else:
        insights = f"{name} needs improvement. Focused practice on weak subjects is recommended."

    insights_card = dbc.Card([dbc.CardHeader("📊 Performance Insights", className="fw-bold bg-secondary text-white"),
                              dbc.CardBody(html.P(insights))], className="shadow-sm mb-4")

    # ---------- Basic Info ----------
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
        comparison_chart,
        html.Br(),
        dbc.Row([dbc.Col(pie_chart, md=6)], className="g-3"),
        html.Br(),
        html.H5("📘 Detailed Subject Performance", className="text-center mb-2"),
        result_table,
        html.Br(),
        insights_card
    ])
