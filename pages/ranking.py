# pages/ranking.py

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px

dash.register_page(__name__, path="/ranking", name="Ranking")

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("🏆 Class & Section Ranking", className="mb-4 text-center"),
    html.Div(id='ranking-content')
], fluid=True)


# ---------- Callback ----------
@callback(
    Output('ranking-content', 'children'),
    Input('stored-data', 'data')
)
def display_ranking(json_data):
    # ---------------- Handle No Data ----------------
    if json_data is None:
        return html.P(
            "Please upload data first on the Overview page.",
            className="text-muted text-center"
        )

    # Load DataFrame from stored JSON
    df = pd.read_json(json_data, orient='split')

    # ---------------- Ensure Required Columns ----------------
    if 'Total_Marks' not in df.columns:
        numeric_cols = df.select_dtypes(include='number').columns
        df['Total_Marks'] = df[numeric_cols].sum(axis=1)

    if 'Overall_Result' not in df.columns:
        df['Overall_Result'] = df['Total_Marks'].apply(lambda x: 'P' if x >= 40 else 'F')

    # ---------------- Calculate Rankings ----------------
    # Class Rank
    df['Class_Rank'] = df['Total_Marks'].rank(method='min', ascending=False).astype(int)

    # Section Rank (if column exists)
    if 'Section' in df.columns:
        df['Section_Rank'] = (
            df.groupby('Section')['Total_Marks']
            .rank(method='min', ascending=False)
            .astype(int)
        )
    else:
        df['Section_Rank'] = None

    # ---------------- Top 10 Students Chart ----------------
    top10 = df.sort_values(by='Total_Marks', ascending=False).head(10)
    first_col = df.columns[0]  # assume first column is Student Name or ID

    fig = px.bar(
        top10,
        x=first_col,
        y='Total_Marks',
        color='Total_Marks',
        text='Class_Rank',
        title="Top 10 Students by Total Marks"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        xaxis_title="Student",
        yaxis_title="Total Marks",
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )

    # ---------------- Ranking Table ----------------
    display_cols = ['Class_Rank', 'Section_Rank', first_col, 'Total_Marks', 'Overall_Result']
    display_cols = [col for col in display_cols if col in df.columns]

    table = dbc.Table.from_dataframe(
        top10[display_cols],
        striped=True,
        bordered=True,
        hover=True,
        className="shadow-sm"
    )

    # ---------------- Layout Return ----------------
    return dbc.Container([
        html.H5("🏅 Top 10 Students", className="text-center mb-3"),
        dcc.Graph(figure=fig, className="mb-4"),
        html.Hr(),
        html.H5("📋 Ranking Table", className="text-center mb-2"),
        table
    ])
