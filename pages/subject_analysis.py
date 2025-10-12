# pages/subject_analysis.py

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objs as go

dash.register_page(__name__, path="/subject_analysis", name="Subject Analysis")

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("📊 Subject-wise Analysis", className="mb-4 text-center"),

    dbc.Row([
        dbc.Col(dcc.Dropdown(id='subject-dropdown', placeholder="Select a subject"), md=6)
    ], justify="center", className="mb-4"),

    html.Div(id='subject-analysis-content')
], fluid=True)


@callback(
    [Output('subject-dropdown', 'options'),
     Output('subject-analysis-content', 'children')],
    [Input('stored-data', 'data'),
     Input('subject-dropdown', 'value')]
)
def update_subject_analysis(json_data, selected_subject):
    if json_data is None:
        return [], html.P("Please upload data first on the Overview page.", className="text-muted text-center")

    df = pd.read_json(json_data, orient='split')

    if 'Name' not in df.columns:
        df['Name'] = df.index.astype(str)

    exclude_cols = ['Student ID', 'Name', 'Section', 'Attendance',
                    'Total_Marks', 'Class_Rank', 'Section_Rank', 'Overall_Result']
    subjects = [col for col in df.columns if col not in exclude_cols]
    dropdown_options = [{'label': s, 'value': s} for s in subjects]

    if selected_subject is None or selected_subject not in df.columns:
        return dropdown_options, html.P("Select a subject to see analysis.", className="text-center text-muted")

    pass_marks = 18

    # ---------------- Detect if it's a Result column ----------------
    if "result" in selected_subject.lower():
        df['Result'] = df[selected_subject].astype(str).str.strip().str.capitalize()
        df['Result'] = df['Result'].apply(lambda x: 'Pass' if x.lower() == 'p' or x.lower() == 'pass' else 'Fail')
        df['Pass_Marks'] = df['Result'].apply(lambda x: pass_marks if x=='Pass' else 0)
        df['Fail_Marks'] = df['Result'].apply(lambda x: pass_marks if x=='Fail' else 0)

        pass_count = (df['Result'] == 'Pass').sum()
        fail_count = (df['Result'] == 'Fail').sum()
        total_students = len(df)
        pass_percent = round((pass_count / total_students) * 100, 2)
        fail_percent = round((fail_count / total_students) * 100, 2)

        kpi_cards = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Pass Students"), html.H2(pass_count)]),
                            color="success", inverse=True), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Fail Students"), html.H2(fail_count)]),
                            color="danger", inverse=True), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Pass %"), html.H2(f"{pass_percent}%")]),
                            color="info", inverse=True), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Fail %"), html.H2(f"{fail_percent}%")]),
                            color="warning", inverse=True), md=3)
        ], className="g-3 mb-4")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df['Name'],
            y=df['Pass_Marks'],
            name='Pass',
            marker_color='green'
        ))
        fig.add_trace(go.Bar(
            x=df['Name'],
            y=df['Fail_Marks'],
            name='Fail',
            marker_color='red'
        ))

        fig.update_layout(
            barmode='stack',
            title=f"{selected_subject} Pass/Fail Stacked Summary",
            xaxis_title="Student",
            yaxis_title="Marks",
            height=500
        )

        failed_students = df[df['Result']=='Fail']['Name'].tolist()
        failed_list = html.Div([
            html.H5("❌ Students who Failed:"),
            html.Ul([html.Li(name) for name in failed_students]) if failed_students else html.P("None")
        ], className="mb-4")

        return dropdown_options, dbc.Container([kpi_cards, dcc.Graph(figure=fig), failed_list], fluid=True)

    else:
        # ---------------- Numeric subjects ----------------
        related_cols = [col for col in df.columns if selected_subject.lower() in col.lower()]
        if not related_cols:
            related_cols = [selected_subject]

        for col in related_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)

        # Determine Pass/Fail based on Total if exists
        if any("total" in col.lower() for col in related_cols):
            total_col = [col for col in related_cols if "total" in col.lower()][0]
            df['Result'] = df[total_col].apply(lambda x: 'Pass' if x >= pass_marks else 'Fail')
        else:
            df['Result'] = df[related_cols[0]].apply(lambda x: 'Pass' if x >= pass_marks else 'Fail')

        pass_count = (df['Result'] == 'Pass').sum()
        fail_count = (df['Result'] == 'Fail').sum()
        total_students = len(df)
        pass_percent = round((pass_count / total_students) * 100, 2)
        fail_percent = round((fail_count / total_students) * 100, 2)

        kpi_cards = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Pass Students"), html.H2(pass_count)]),
                            color="success", inverse=True), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Fail Students"), html.H2(fail_count)]),
                            color="danger", inverse=True), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Pass %"), html.H2(f"{pass_percent}%")]),
                            color="info", inverse=True), md=3),
            dbc.Col(dbc.Card(dbc.CardBody([html.H5("Fail %"), html.H2(f"{fail_percent}%")]),
                            color="warning", inverse=True), md=3)
        ], className="g-3 mb-4")

        # Create stacked bars for each column
        fig = go.Figure()
        for col in related_cols:
            df[f'{col}_Pass'] = df[col].apply(lambda x: x if x >= pass_marks else 0)
            df[f'{col}_Fail'] = df[col].apply(lambda x: x if x < pass_marks else 0)
            fig.add_trace(go.Bar(
                x=df['Name'],
                y=df[f'{col}_Pass'],
                name=f'{col} - Pass',
                marker_color='green'
            ))
            fig.add_trace(go.Bar(
                x=df['Name'],
                y=df[f'{col}_Fail'],
                name=f'{col} - Fail',
                marker_color='red'
            ))

        fig.update_layout(
            barmode='stack',
            title=f"{selected_subject} Marks Stacked Analysis",
            xaxis_title="Student",
            yaxis_title="Marks",
            height=500
        )

        failed_students = df[df['Result']=='Fail']['Name'].tolist()
        failed_list = html.Div([
            html.H5("❌ Students who Failed:"),
            html.Ul([html.Li(name) for name in failed_students]) if failed_students else html.P("None")
        ], className="mb-4")

        return dropdown_options, dbc.Container([kpi_cards, dcc.Graph(figure=fig), failed_list], fluid=True)
