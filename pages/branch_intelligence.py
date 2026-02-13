import dash
from dash import html, dcc, Input, Output, callback, State, no_update
import dash_bootstrap_components as dbc
import pandas as pd

import utils.master_store as ms

dash.register_page(__name__, path="/branch-intelligence", name="Branch Intelligence")

# --------------------------------------------------
# NORMALIZATION (STUDENT-LEVEL PASS / FAIL)
# --------------------------------------------------
def normalize_for_branch(df_long):

    if df_long.empty:
        return df_long

    df_wide = df_long.pivot_table(
        index=["Student_ID", "Name", "Branch"],
        columns="Subject",
        values="Result",
        aggfunc="first"
    ).reset_index()

    subject_cols = [c for c in df_wide.columns if c not in ["Student_ID", "Name", "Branch"]]

    df_wide["Overall_Result"] = df_wide[subject_cols].apply(
        lambda row: "P" if all(str(v).upper() == "P" for v in row if pd.notna(v)) else "F",
        axis=1
    )

    return df_wide


# --------------------------------------------------
# LAYOUT
# --------------------------------------------------
layout = dbc.Container([

    html.Br(),
    html.H2("🧠 Branch Intelligence Dashboard", className="text-center"),
    html.P(
        "Advanced analytics across branches, subjects and student performance.",
        className="text-center text-muted"
    ),
    html.Hr(),

    # ---------- BASIC KPIs ----------
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Total Students"),
            html.H3(id="bi-total-students")
        ]), className="shadow-sm text-center"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Branches Loaded"),
            html.H3(id="bi-total-branches")
        ]), className="shadow-sm text-center"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Subjects Detected"),
            html.H3(id="bi-total-subjects")
        ]), className="shadow-sm text-center"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Overall Pass %"),
            html.H3(id="bi-pass-percent")
        ]), className="shadow-sm text-center"), md=3),
    ], className="mb-3"),

    # ---------- INTELLIGENCE KPIs ----------
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Best Performing Branch"),
            html.H3(id="bi-best-branch")
        ]), className="shadow-sm text-center"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Weak Branch"),
            html.H3(id="bi-weak-branch")
        ]), className="shadow-sm text-center"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Hardest Subject"),
            html.H3(id="bi-hardest-subject")
        ]), className="shadow-sm text-center"), md=3),

        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Easiest Subject"),
            html.H3(id="bi-easiest-subject")
        ]), className="shadow-sm text-center"), md=3),
    ], className="mb-4"),

    # ---------- FILTERS ----------
    dbc.Card([
        dbc.CardBody([
            html.H4("📊 Branch Performance Comparison"),

            dbc.Row([
                dbc.Col([
                    html.Label("Select Branch(es)", className="fw-bold"),
                    html.Div([
                        dcc.Dropdown(
                            id="bi-branch-selector",
                            multi=True,
                            placeholder="Select branch(es)",
                            className="custom-dropdown",
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"overflow": "visible", "position": "relative", "zIndex": "1000"})
                ], md=5),

                dbc.Col([
                    html.Label(" ", className="d-block"),
                    dbc.ButtonGroup([
                        dbc.Button("Select All", id="bi-select-all-btn",
                                   color="success", outline=True, size="sm"),
                        dbc.Button("Clear", id="bi-clear-btn",
                                   color="danger", outline=True, size="sm"),
                    ], className="w-100")
                ], md=2),

                dbc.Col([
                    html.Label("Select Subject(s)", className="fw-bold"),
                    html.Div([
                        dcc.Dropdown(
                            id="bi-subject-selector",
                            multi=True,
                            placeholder="Select subject(s)",
                            className="custom-dropdown",
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        ),
                        html.Div(style={"height": "10px"})
                    ], style={"overflow": "visible", "position": "relative", "zIndex": "100"})
                ], md=5),
            ], className="mb-3"),

            html.Div(id="bi-branch-table")
        ], style={"overflow": "visible", "position": "relative"})
    ], className="shadow-sm mb-4", style={"overflow": "visible"}),

    dbc.Card([
        dbc.CardBody([
            html.H4("📚 Subject Overview"),
            html.Div(id="bi-subject-summary")
        ], style={"overflow": "visible"})
    ], className="shadow-sm mb-4", style={"overflow": "visible"})

], fluid=True)


# --------------------------------------------------
# SELECT ALL / CLEAR (BRANCHES)
# --------------------------------------------------
@callback(
    Output("bi-branch-selector", "value"),
    Input("bi-select-all-btn", "n_clicks"),
    Input("bi-clear-btn", "n_clicks"),
    State("bi-branch-selector", "options"),
    prevent_initial_call=True
)
def handle_select_buttons(select_all, clear, options):

    if not options:
        return []

    triggered = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    if triggered == "bi-select-all-btn":
        return [o["value"] for o in options]

    if triggered == "bi-clear-btn":
        return []

    return no_update


# --------------------------------------------------
# KPI CONTROLLER (FILTER AWARE)
# --------------------------------------------------
@callback(
    Output("bi-total-students", "children"),
    Output("bi-total-branches", "children"),
    Output("bi-total-subjects", "children"),
    Output("bi-pass-percent", "children"),
    Output("bi-branch-selector", "options"),
    Output("bi-subject-selector", "options"),
    Output("bi-best-branch", "children"),
    Output("bi-weak-branch", "children"),
    Output("bi-hardest-subject", "children"),
    Output("bi-easiest-subject", "children"),
    Input("bi-branch-selector", "value"),
    Input("bi-subject-selector", "value")
)
def update_kpis(branches, subjects):

    if ms.MASTER_BRANCH_DATA is None:
        return "-", "-", "-", "-", [], [], "-", "-", "-", "-"

    df = ms.MASTER_BRANCH_DATA.copy()

    if branches:
        df = df[df["Branch"].isin(branches)]

    if subjects:
        df = df[df["Subject"].isin(subjects)]

    if df.empty:
        return "0", "0", "0", "0%", [], [], "-", "-", "-", "-"

    df_students = normalize_for_branch(df)

    total_students = df_students["Student_ID"].nunique()
    total_branches = df_students["Branch"].nunique()
    total_subjects = df["Subject"].nunique()

    pass_percent = round((df_students["Overall_Result"] == "P").mean() * 100, 2)

    branch_options = [
        {"label": b, "value": b}
        for b in sorted(ms.MASTER_BRANCH_DATA["Branch"].unique())
    ]

    subject_options = [
        {"label": s, "value": s}
        for s in sorted(df["Subject"].unique())
    ]

    # ---------- BRANCH INTELLIGENCE ----------
    if total_branches <= 1:
        best_branch = "N/A"
        weak_branch = "N/A"
    else:
        perf = df_students.groupby("Branch").apply(
            lambda x: (x["Overall_Result"] == "P").mean()
        ).reset_index(name="PassRate")

        best_branch = perf.sort_values("PassRate", ascending=False).iloc[0]["Branch"]
        weak_branch = perf.sort_values("PassRate").iloc[0]["Branch"]

    # ---------- SUBJECT INTELLIGENCE ----------
    subject_perf = df.groupby("Subject").apply(
        lambda x: (x["Result"] == "F").mean()
    ).reset_index(name="FailRate")

    hardest_subject = subject_perf.sort_values("FailRate", ascending=False).iloc[0]["Subject"]
    easiest_subject = subject_perf.sort_values("FailRate").iloc[0]["Subject"]

    return (
        total_students,
        total_branches,
        total_subjects,
        f"{pass_percent}%",
        branch_options,
        subject_options,
        best_branch,
        weak_branch,
        hardest_subject,
        easiest_subject
    )


# --------------------------------------------------
# BRANCH TABLE
# --------------------------------------------------
@callback(
    Output("bi-branch-table", "children"),
    Input("bi-branch-selector", "value"),
    Input("bi-subject-selector", "value")
)
def branch_table(branches, subjects):

    df = ms.MASTER_BRANCH_DATA.copy()

    if branches:
        df = df[df["Branch"].isin(branches)]

    if subjects:
        df = df[df["Subject"].isin(subjects)]

    if df.empty:
        return dbc.Alert("No data for selected filters", color="warning")

    df_students = normalize_for_branch(df)

    summary = df_students.groupby("Branch").agg(
        Students=("Student_ID", "nunique"),
        Passed=("Overall_Result", lambda x: (x == "P").sum()),
        Failed=("Overall_Result", lambda x: (x == "F").sum())
    ).reset_index()

    return dbc.Table.from_dataframe(summary, bordered=True, striped=True, hover=True)


# --------------------------------------------------
# SUBJECT SUMMARY
# --------------------------------------------------
@callback(
    Output("bi-subject-summary", "children"),
    Input("bi-branch-selector", "value")
)
def subject_summary(branches):

    df = ms.MASTER_BRANCH_DATA.copy()

    if branches:
        df = df[df["Branch"].isin(branches)]

    if df.empty:
        return dbc.Alert("No subject data", color="warning")

    subject_stats = df.groupby("Subject").agg(
        Students=("Student_ID", "nunique"),
        Pass=("Result", lambda x: (x == "P").sum()),
        Fail=("Result", lambda x: (x == "F").sum())
    ).reset_index()

    return dbc.Table.from_dataframe(subject_stats, bordered=True, striped=True, hover=True)
