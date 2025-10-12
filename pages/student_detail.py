# pages/student_detail.py

import dash
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import pandas as pd

dash.register_page(__name__, path="/student_detail", name="Student Detail")

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("🎓 Student Detail Lookup", className="mb-4 text-center"),

    # Input box for Student ID or Name
    dbc.Row([
        dbc.Col(dcc.Input(
            id='student-search',
            type='text',
            placeholder='Enter Student ID or Name...',
            debounce=True,  # triggers callback when user stops typing
            className="form-control"
        ), md=6),
        dbc.Col(dbc.Button("Search", id='search-btn', color="primary", className="ms-2"), md=2)
    ], justify="center", className="mb-4"),

    # Div to show student info
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

    # Ensure 'Student ID' and 'Name' exist
    if 'Student ID' not in df.columns:
        df['Student ID'] = ""
    if 'Name' not in df.columns:
        df['Name'] = ""

    # Filter by Student ID or Name (case-insensitive)
    mask = df.apply(
        lambda row: search_value.lower() in str(row.get('Student ID', '')).lower()
                    or search_value.lower() in str(row.get('Name', '')).lower(),
        axis=1
    )
    student_df = df[mask]

    if student_df.empty:
        return html.P("No student found with this ID or Name.", className="text-danger text-center")

    student_df = student_df.reset_index(drop=True)

    # Identify subject columns dynamically
    exclude_cols = ['Student ID', 'Name', 'Section', 'Attendance', 'Total_Marks',
                    'Class_Rank', 'Section_Rank', 'Overall_Result']
    subjects = [col for col in student_df.columns if col not in exclude_cols]

    # Display basic info
    student_info = dbc.Card([
        dbc.CardBody([
            html.H5(f"Student ID: {student_df.at[0, 'Student ID']}"),
            html.H5(f"Name: {student_df.at[0, 'Name']}"),
            html.H5(f"Section: {student_df.at[0, 'Section'] if 'Section' in student_df.columns else 'N/A'}"),
            html.H5(f"Total Marks: {student_df.at[0, 'Total_Marks']}"),
            html.H5(f"Class Rank: {student_df.at[0, 'Class_Rank']}"),
            html.H5(f"Section Rank: {student_df.at[0, 'Section_Rank']}"),
            html.H5(f"Overall Result: {student_df.at[0, 'Overall_Result']}"),
        ])
    ], className="mb-4 shadow-sm")

    # Subject-wise marks table
    if subjects:
        subject_table = dash_table.DataTable(
            data=student_df[subjects].T.reset_index().rename(
                columns={'index': 'Subject', student_df.index[0]: 'Marks'}
            ).to_dict('records'),
            columns=[{"name": 'Subject', "id": 'Subject'}, {"name": 'Marks', "id": 'Marks'}],
            style_header={'backgroundColor': '#f0f0f0', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'center'},
            style_table={'width': '50%', 'margin': 'auto'}
        )
        return html.Div([student_info, subject_table])
    else:
        return html.Div([student_info, html.P("No subject data available.", className="text-muted text-center")])
