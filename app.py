# app.py

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# ----------------- Initialize Dash App -----------------
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.FLATLY],
    suppress_callback_exceptions=True
)
app.title = "Student Performance Dashboard"

# ----------------- Styled Navbar -----------------
navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col(
                html.H3(
                    "📊 Student Performance Dashboard",
                    className="text-white mb-0 fw-bold",
                    style={"textShadow": "1px 1px 2px #000"}
                ),
                width="auto"
            )
        ], align="center"),

        dbc.Nav(
            [
                dbc.NavLink("🏠 Overview", href="/", active="exact", className="mx-2"),
                dbc.NavLink("🏆 Ranking", href="/ranking", active="exact", className="mx-2"),
                dbc.NavLink("📚 Subject Analysis", href="/subject_analysis", active="exact", className="mx-2"),
                dbc.NavLink("🎓 Student Detail", href="/student_detail", active="exact", className="mx-2"),
            ],
            pills=True,
            className="ms-auto",
            style={"fontWeight": "bold", "fontSize": "1rem"}
        )
    ]),
    color="#1f2937",
    dark=True,
    sticky="top",
    className="shadow-lg rounded mb-4"
)

# ----------------- Page Container Styling -----------------
app.layout = dbc.Container([
    navbar,

    # Persistent Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),

    # Page container
    dbc.Card(
        dash.page_container,
        body=True,
        className="p-4 shadow-lg rounded text-center",
        style={
            "backgroundColor": "#fef9f0",
            "borderLeft": "8px solid #3b82f6",
            "borderRadius": "12px",
            "boxShadow": "0 6px 25px rgba(0,0,0,0.15)",
            "textAlign": "center",
            "color": "#111827"
        }
    )
],
fluid=True,
style={
    "backgroundColor": "#f0f4f8",
    "padding": "25px",
    "minHeight": "100vh"
})

# ----------------- Server for Deployment -----------------
server = app.server

# ----------------- Run App -----------------
if __name__ == '__main__':
    app.run(debug=True)
