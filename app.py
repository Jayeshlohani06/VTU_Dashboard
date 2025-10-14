# app.py

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# ----------------- Initialize Dash App -----------------
app = dash.Dash(
    __name__,
    use_pages=True,  # Enable multipage support
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "Student Performance Dashboard"

# ----------------- Navbar Links -----------------
nav_links = [
    dbc.NavItem(dbc.NavLink("🏠 Overview", href="/")),
    dbc.NavItem(dbc.NavLink("🏆 Ranking", href="/ranking")),
    dbc.NavItem(dbc.NavLink("📚 Subject Analysis", href="/subject_analysis")),
    dbc.NavItem(dbc.NavLink("🎓 Student Detail", href="/student_detail")),
]

# ----------------- Layout -----------------
app.layout = dbc.Container([
    html.H2("📊 Student Performance Dashboard", className="text-center mt-4 mb-3"),

    # Navbar for switching between pages
    dbc.NavbarSimple(
        children=nav_links,
        brand="Navigation",
        color="primary",
        dark=True,
        className="mb-4 rounded"
    ),

    # ✅ Persistent Stores for session-wide data
    dcc.Store(id='stored-data', storage_type='session'),                # For Excel data
    dcc.Store(id='overview-selected-subjects', storage_type='session'), # For selected subjects

    # Dynamic page container
    dash.page_container
], fluid=True)

# ----------------- Server for Deployment -----------------
server = app.server

# ----------------- Run App -----------------
if __name__ == '__main__':
    app.run(debug=True)
