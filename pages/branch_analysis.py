import dash
from dash import html, dcc, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd
import re

import utils.master_store as ms   # ⭐ global dataset store

dash.register_page(__name__, path="/branch-analysis", name="Branch Analysis")


# ---------------- VTU PARSER ----------------

def process_uploaded_excel(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    df_raw = pd.read_excel(io.BytesIO(decoded), header=[0, 1])

    fixed_cols = []
    for h1, h2 in df_raw.columns:
        h1 = str(h1).strip() if str(h1).lower() != "nan" else ""
        h2 = str(h2).strip() if str(h2).lower() != "nan" else ""

        if h1.lower() == "name":
            fixed_cols.append("Name")
        elif h2:
            fixed_cols.append(f"{h1} {h2}")
        else:
            fixed_cols.append(h1)

    df_raw.columns = fixed_cols
    df = df_raw.loc[:, df_raw.columns.str.strip() != ""]
    return df


def get_subject_codes(df):
    subject_codes = set()

    for col in df.columns:
        col = col.strip()
        if " " not in col:
            continue

        prefix, suffix = col.rsplit(" ", 1)

        if suffix not in ["Internal", "External", "Total", "Result"]:
            continue

        if re.fullmatch(r"[A-Z]{2,}\d{3}[A-Z]?", prefix):
            subject_codes.add(prefix)

    return sorted(subject_codes)


# ---------------- Layout ----------------

layout = dbc.Container([

    html.Br(),
    html.H2("🏫 Branch Intelligence Dashboard", className="text-center"),

    html.P(
        "Upload multiple branch result files and compare performance across departments.",
        className="text-center text-muted"
    ),

    html.Hr(),

    dbc.Card([
        dbc.CardBody([
            html.H5("Step 1: Enter Number of Branches"),

            dbc.Input(id="branch-count", type="number", min=1, max=10),
            html.Br(),
            dbc.Button("Generate Branch Inputs", id="generate-branch-inputs", color="primary")
        ])
    ], className="shadow-sm"),

    html.Br(),
    html.Div(id="branch-input-container"),
    html.Br(),

    dbc.Button("Analyze Branch Results", id="analyze-branches", color="success", size="lg", className="w-100"),

    html.Br(), html.Br(),

    html.Div(id="final-actions-container")

], fluid=True)


# ---------------- Generate Inputs ----------------

@callback(
    Output("branch-input-container", "children"),
    Input("generate-branch-inputs", "n_clicks"),
    State("branch-count", "value"),
    prevent_initial_call=True
)
def generate_branch_inputs(n_clicks, branch_count):

    if not branch_count:
        return ""

    inputs = []

    for i in range(branch_count):
        inputs.append(
            dbc.Card([
                dbc.CardBody([

                    html.H5(f"Branch {i+1}"),

                    dbc.Input(id={'type': 'branch-name', 'index': i}, placeholder="Enter Branch Name"),
                    html.Br(),

                    dcc.Upload(
                        id={'type': 'branch-file', 'index': i},
                        children=html.Div(id={'type': 'upload-text', 'index': i}, children=['Drag & Drop or Upload Excel']),
                        style={'border': '1px dashed gray','padding': '12px','textAlign': 'center','borderRadius': '8px'},
                        multiple=False,
                        accept=".xlsx,.xls"
                    ),

                    html.Div(id={'type': 'upload-msg', 'index': i}),
                    html.Div(id={'type': 'process-msg', 'index': i})

                ])
            ], className="mb-3 shadow-sm")
        )

    return inputs


# ---------------- Upload UI ----------------

@callback(
    Output({'type': 'upload-text', 'index': ALL}, 'children'),
    Output({'type': 'upload-msg', 'index': ALL}, 'children'),
    Input({'type': 'branch-file', 'index': ALL}, 'contents'),
    State({'type': 'branch-name', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def update_upload_ui(contents_list, names):

    texts = []
    messages = []

    for content, name in zip(contents_list, names):

        if content:
            texts.append("✔ File uploaded")

            messages.append(
                dbc.Alert(f"{name.upper()} uploaded", color="success", duration=4000)
            )
        else:
            texts.append("Drag & Drop or Upload Excel")
            messages.append("")

    return texts, messages


# ---------------- Process branch files ----------------

@callback(
    Output({'type': 'process-msg', 'index': ALL}, 'children'),
    Output("final-actions-container", "children"),
    Input("analyze-branches", "n_clicks"),
    State({'type': 'branch-name', 'index': ALL}, 'value'),
    Input({'type': 'branch-file', 'index': ALL}, 'contents'),
    prevent_initial_call=True
)
def process_branch_files(n_clicks, branch_names, branch_files):

    if not branch_files or all(f is None for f in branch_files):
        return ["Upload files first"] * len(branch_names), ""

    all_long_data = []
    branch_summaries = []

    for name, content in zip(branch_names, branch_files):

        if not name or not content:
            branch_summaries.append("")
            continue

        df = process_uploaded_excel(content)
        subjects = get_subject_codes(df)

        for _, row in df.iterrows():
            for subject in subjects:
                all_long_data.append({
                    "Student_ID": row.iloc[0],
                    "Name": row.get("Name"),
                    "Branch": name.upper(),
                    "Subject": subject,
                    "Total": row.get(f"{subject} Total"),
                    "Result": row.get(f"{subject} Result")
                })

        branch_summaries.append(
            dbc.Alert(
                [html.H6(f"{name.upper()} Processed"),
                 html.Div(f"Subjects: {len(subjects)}"),
                 html.Div(f"Records: {len(df)}")],
                color="info",
                duration=7000
            )
        )

    long_df = pd.DataFrame(all_long_data)

    # ⭐ SAVE GLOBALLY
    ms.MASTER_BRANCH_DATA = long_df

    actions = html.Div([

        dbc.Button("Proceed to Branch Intelligence →", href="/branch-intelligence",
                   color="primary", size="lg", className="w-100 mt-3")
    ])

    return branch_summaries, actions
