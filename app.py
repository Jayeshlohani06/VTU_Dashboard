import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from cache_config import cache
from services.google_sheets_service import save_feedback

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

# ----------------- Feedback Modal -----------------
feedback_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            html.Div([
                html.Div([
                    html.Div(
                        html.I(className="bi bi-headset", style={"fontSize": "1.6rem"}),
                        className="feedback-header-icon"
                    ),
                    html.Div([
                        html.H5("Feedback & Contact", className="fw-bold mb-0"),
                        html.Small("We're here to help", className="text-muted")
                    ])
                ], className="d-flex align-items-center gap-3")
            ], className="w-100"),
            close_button=True,
            className="feedback-modal-header"
        ),
        dbc.ModalBody([
            # Tab switcher
            dbc.Tabs([
                # ──── FEEDBACK TAB ────
                dbc.Tab(
                    html.Div([

                        # ── Emoji mood rating ──
                        html.Div([
                            html.Label([
                                html.I(className="bi bi-emoji-smile me-2 text-primary"),
                                "How's your experience?"
                            ], className="fw-semibold small d-block mb-2"),
                            dbc.RadioItems(
                                id="fb-rating",
                                options=[
                                    {"label": "😡", "value": "1"},
                                    {"label": "😕", "value": "2"},
                                    {"label": "😐", "value": "3"},
                                    {"label": "🙂", "value": "4"},
                                    {"label": "😍", "value": "5"},
                                ],
                                value=None,
                                inline=True,
                                className="emoji-rating-group",
                            ),
                        ], className="mb-3"),

                        html.Hr(className="my-2", style={"opacity": "0.1"}),

                        # ── Name + Email ──
                        dbc.Row([
                            dbc.Col([
                                dbc.Label([
                                    html.I(className="bi bi-person-fill me-2 text-primary"),
                                    "Name"
                                ], className="fw-semibold small"),
                                dbc.Input(
                                    id="fb-name", placeholder="John Doe",
                                    className="feedback-input"
                                ),
                            ], md=6),
                            dbc.Col([
                                dbc.Label([
                                    html.I(className="bi bi-envelope-fill me-2 text-primary"),
                                    "Email"
                                ], className="fw-semibold small"),
                                dbc.Input(
                                    id="fb-email", type="email", placeholder="you@example.com",
                                    className="feedback-input"
                                ),
                            ], md=6),
                        ], className="mb-3"),

                        # ── Feedback Type as icon cards ──
                        dbc.Label([
                            html.I(className="bi bi-tag-fill me-2 text-primary"),
                            "Feedback Type"
                        ], className="fw-semibold small"),
                        dbc.RadioItems(
                            id="fb-type",
                            options=[
                                {"label": html.Span([
                                    html.Span("🐛", className="fb-type-emoji"),
                                    html.Span("Bug Report", className="fb-type-text"),
                                ], className="fb-type-option fb-type-bug"), "value": "Bug"},
                                {"label": html.Span([
                                    html.Span("✨", className="fb-type-emoji"),
                                    html.Span("Feature Request", className="fb-type-text"),
                                ], className="fb-type-option fb-type-feature"), "value": "Feature"},
                                {"label": html.Span([
                                    html.Span("🎨", className="fb-type-emoji"),
                                    html.Span("UI Suggestion", className="fb-type-text"),
                                ], className="fb-type-option fb-type-ui"), "value": "UI"},
                                {"label": html.Span([
                                    html.Span("💡", className="fb-type-emoji"),
                                    html.Span("Other", className="fb-type-text"),
                                ], className="fb-type-option fb-type-other"), "value": "Other"},
                            ],
                            value=None,
                            inline=True,
                            className="feedback-type-pills",
                        ),

                        html.Div(style={"height": "12px"}),

                        # ── Message + character counter ──
                        html.Div([
                            dbc.Label([
                                html.I(className="bi bi-chat-text-fill me-2 text-primary"),
                                "Message"
                            ], className="fw-semibold small"),
                            dbc.Textarea(
                                id="fb-message",
                                placeholder="Tell us what's on your mind...",
                                rows=3,
                                className="feedback-input",
                                maxLength=500,
                                style={"resize": "vertical"}
                            ),
                            html.Div(
                                html.Small("0 / 500", id="fb-char-count", className="text-muted"),
                                className="text-end mt-1"
                            ),
                        ]),

                        # ── Tip: share screenshots via WhatsApp ──
                        html.Div([
                            html.I(className="bi bi-info-circle me-2"),
                            "Want to share a screenshot? Reach out via ",
                            html.Strong("WhatsApp"),
                            " in the Contact Us tab."
                        ], className="screenshot-tip mt-3"),

                        dcc.Loading(
                            html.Div(id="fb-status"),
                            type="circle",
                            color="#6366f1",
                            className="mt-3"
                        ),

                        html.Div(
                            dbc.Button([
                                html.I(className="bi bi-send-fill me-2"),
                                "Submit Feedback"
                            ], id="fb-submit", className="feedback-submit-btn mt-3"),
                            className="text-end"
                        )
                    ], className="pt-3"),
                    label="❤️ Feedback",
                    tab_id="tab-feedback",
                    className="feedback-tab-pane",
                ),

                # ──── CONTACT US TAB ────
                dbc.Tab(
                    html.Div([
                        # WhatsApp Card
                        html.A(
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div([
                                        html.Div(
                                            html.I(className="bi bi-whatsapp", style={"fontSize": "1.8rem"}),
                                            className="contact-icon-circle contact-whatsapp"
                                        ),
                                        html.Div([
                                            html.H6("Chat on WhatsApp", className="fw-bold mb-0"),
                                            html.Small("Tap to start a conversation", className="text-muted")
                                        ])
                                    ], className="d-flex align-items-center gap-3"),
                                    html.I(className="bi bi-arrow-right", style={"fontSize": "1.2rem", "color": "#9ca3af"})
                                ], className="d-flex align-items-center justify-content-between")
                            ], className="contact-card"),
                            href="https://wa.me/918936897736?text=Hi%2C%20I%20have%20a%20query%20about%20the%20VTU%20Dashboard",
                            target="_blank",
                            style={"textDecoration": "none"}
                        ),

                        # Email Card
                        html.A(
                            dbc.Card([
                                dbc.CardBody([
                                    html.Div([
                                        html.Div(
                                            html.I(className="bi bi-envelope-fill", style={"fontSize": "1.8rem"}),
                                            className="contact-icon-circle contact-email"
                                        ),
                                        html.Div([
                                            html.H6("Send an Email", className="fw-bold mb-0"),
                                            html.Small("dashboardhelpdesk06@gmail.com", className="text-muted")
                                        ])
                                    ], className="d-flex align-items-center gap-3"),
                                    html.I(className="bi bi-arrow-right", style={"fontSize": "1.2rem", "color": "#9ca3af"})
                                ], className="d-flex align-items-center justify-content-between")
                            ], className="contact-card"),
                            href="mailto:dashboardhelpdesk06@gmail.com?subject=VTU%20Dashboard%20Query",
                            target="_blank",
                            style={"textDecoration": "none"}
                        ),

                        # Info note
                        html.Div([
                            html.I(className="bi bi-info-circle me-2"),
                            "We typically respond within 24 hours."
                        ], className="contact-info-note mt-3")

                    ], className="pt-3 d-grid gap-3"),
                    label="\U0001f4de Contact Us",
                    tab_id="tab-contact",
                    className="feedback-tab-pane",
                ),
            ], id="feedback-tabs", active_tab="tab-feedback", className="feedback-tabs"),

        ], className="feedback-modal-body"),
        dbc.ModalFooter([
            html.Small("We value your feedback ❤️", className="text-muted me-auto"),
        ], className="feedback-modal-footer"),
    ],
    id="feedback-modal",
    is_open=False,
    centered=True,
    scrollable=True,
    size="lg",
    className="feedback-modal",
    style={"zIndex": 2050},
    backdrop_class_name="feedback-backdrop",
)

# Floating feedback button
feedback_fab = dbc.Button(
    html.Div([
        html.I(className="bi bi-headset", style={"fontSize": "1.4rem"}),
        html.Span("Help", className="feedback-fab-label")
    ], className="d-flex align-items-center gap-2"),
    id="feedback-fab",
    className="feedback-fab",
    title="Feedback & Contact",
    n_clicks=0,
)

# ----------------- Layout -----------------
app.layout = html.Div([
    dbc.Container(
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
            dcc.Store(id="scheme-semester-store", storage_type="session"),
            dcc.Store(id="sgpa-store", storage_type="session"),

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
                        html.Span("Jayesh Lohani | Amit Kumar Thakur | Aman Raj | Avni Chauhan", className="fw-medium"),
                        html.Br(),
                        html.Span("Under the Guidance of Professor Arun K H, Assistant Professor Acharya Institute of Technology", className="fw-bold mt-2 d-inline-block")
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
    ),

    # FEEDBACK COMPONENTS — placed outside Container to avoid navbar stacking context
    feedback_fab,
    feedback_modal,
])

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


# ----------------- Feedback Callbacks -----------------
@callback(
    Output("feedback-modal", "is_open"),
    Input("feedback-fab", "n_clicks"),
    State("feedback-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_feedback_modal(n, is_open):
    if n:
        return not is_open
    return is_open


# Character counter for message textarea
@callback(
    Output("fb-char-count", "children"),
    Input("fb-message", "value"),
    prevent_initial_call=True
)
def update_char_count(msg):
    length = len(msg) if msg else 0
    return f"{length} / 500"


@callback(
    Output("fb-status", "children"),
    Output("fb-name", "value"),
    Output("fb-email", "value"),
    Output("fb-type", "value"),
    Output("fb-message", "value"),
    Output("fb-rating", "value"),
    Input("fb-submit", "n_clicks"),
    State("fb-name", "value"),
    State("fb-email", "value"),
    State("fb-type", "value"),
    State("fb-message", "value"),
    State("fb-rating", "value"),
    prevent_initial_call=True
)
def submit_feedback(n, name, email, ftype, message, rating):
    if not n:
        raise dash.exceptions.PreventUpdate
    if not name or not message:
        return (
            dbc.Alert("Name and Message are required.", color="warning"),
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        )
    try:
        rating_map = {"1": "😡", "2": "😕", "3": "😐", "4": "🙂", "5": "😍"}
        rating_label = rating_map.get(rating, "N/A")
        save_feedback(name, email, ftype, message, rating_label)
        return (
            dbc.Alert([
                html.I(className="bi bi-check-circle-fill me-2"),
                "Feedback submitted — thank you! 🎉"
            ], color="success", className="d-flex align-items-center"),
            "", "", None, "", None
        )
    except Exception as e:
        return (
            dbc.Alert(f"Error: {e}", color="danger"),
            dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        )


# ----------------- Server -----------------
server = app.server


# ----------------- Run App -----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)