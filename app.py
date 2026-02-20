import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
from cache_config import cache

# ----------------- Initialize Dash App -----------------
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.FLATLY,
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"
    ],
    suppress_callback_exceptions=True,
    prevent_initial_callbacks='initial_duplicate'
)

server = app.server
cache.init_app(server)

app.title = "Student Performance Dashboard"

# ----------------- Navbar -----------------
navbar = dbc.Navbar(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            [
                                html.Span("📊", style={"fontSize": "1.6rem", "marginRight": "8px"}),
                                html.Span("Student Performance Dashboard",
                                          className="fw-bold",
                                          style={"fontSize": "1.3rem"})
                            ],
                            className="text-white d-flex align-items-center"
                        ),
                        width="auto",
                    )
                ],
                align="center",
            ),

            dbc.Nav(
                [
                    dbc.NavLink("Overview", href="/", active="exact", className="nav-pill"),
                    dbc.NavLink("Ranking", href="/ranking", active="exact", className="nav-pill"),
                    dbc.NavLink("Subject Analysis", href="/subject_analysis", active="exact", className="nav-pill"),
                    dbc.NavLink("Student Detail", href="/student_detail", active="exact", className="nav-pill"),
                    dbc.NavLink("Branch Analysis", href="/branch-analysis", active="exact", className="nav-pill"),
                ],
                pills=True,
                className="ms-auto",
            ),
        ],
        fluid=True
    ),
    color="#111827",
    dark=True,
    sticky="top",
    className="shadow-sm px-3",
    style={"zIndex": 2000}
)

# ----------------- Layout -----------------
app.layout = dbc.Container(
    [

        dcc.Location(id="url", refresh=False),

        # NAVBAR
        navbar,

        # PAGE HEADER (UPGRADED)
        html.Div(
            id="page-title-display",
            children=[
                html.H3("🏠 Overview", className="fw-bold mb-1"),
                html.P(
                    "Track overall student performance, pass percentage, and academic insights.",
                    className="text-muted mb-0"
                )
            ],
            style={
                "background": "white",
                "padding": "20px",
                "borderRadius": "14px",
                "marginBottom": "20px",
                "boxShadow": "0 4px 14px rgba(0,0,0,0.06)"
            }
        ),

        # 🔥 GLOBAL SESSION STORES
        dcc.Store(id="stored-data", storage_type="session"),
        dcc.Store(id="overview-selected-subjects", storage_type="session"),
        dcc.Store(id="branch-long-data", storage_type="session"),
        dcc.Store(id="section-data", storage_type="session"),
        dcc.Store(id="usn-mapping-store", storage_type="session"),
        dcc.Store(id="subject-options-store", storage_type="session"),

        # PAGE CONTENT
        html.Div(
            dash.page_container,
            style={
                "background": "white",
                "padding": "20px",
                "borderRadius": "14px",
                "boxShadow": "0 4px 14px rgba(0,0,0,0.05)"
            }
        ),

        # ----------------- Footer -----------------
        html.Footer(
            html.Div(
                [
                    html.Span("Designed & Developed by Students of Acharya Institute of Technology:", className="fw-bold"),
                    html.Br(),
                    html.Span("Jayesh Lohani | Amit Kumar Thakur | Aman Raj | Avni Chauhan", className="fw-medium")
                ],
                className="text-center",
                style={
                    "fontSize": "1rem", 
                    "padding": "15px", 
                    "color": "#333",
                    "backgroundColor": "#e9ecef",
                    "borderRadius": "8px",
                    "border": "1px solid #ced4da"
                }
            ),
            style={"marginTop": "30px", "paddingBottom": "20px"}
        )

    ],
    fluid=True,
    className="d-flex flex-column",
    style={
        "backgroundColor": "#f3f4f6",
        "padding": "25px",
        "minHeight": "100vh"
    },
)

# ----------------- Dynamic Page Title -----------------
@callback(
    Output("page-title-display", "children"),
    Input("url", "pathname"),
    prevent_initial_call=False
)
def display_page_title(pathname):

    if pathname is None:
        pathname = "/"

    page_info = {
        "/": ("🏠 Overview", "Track overall performance, pass %, and academic insights."),
        "/ranking": ("🏆 Ranking", "Compare student rankings and academic performance."),
        "/subject_analysis": ("📚 Subject Analysis", "Analyze subject-wise pass/fail trends."),
        "/student_detail": ("🎓 Student Detail", "Deep dive into individual student data."),
        "/branch-analysis": ("🏫 Branch Analysis", "Compare performance across branches.")
    }

    title, subtitle = page_info.get(pathname, ("📊 Dashboard", "Analytics Overview"))

    return [
        html.H3(title, className="fw-bold mb-1"),
        html.P(subtitle, className="text-muted mb-0")
    ]


# ----------------- Server -----------------
server = app.server


# ----------------- Run App -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)