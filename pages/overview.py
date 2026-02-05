import dash
from dash import html, dcc, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import re

dash.register_page(__name__, path='/', name="Overview")

# ---------- Helper Functions ----------
def process_uploaded_excel(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    df_raw = pd.read_excel(io.BytesIO(decoded), header=[0, 1])

    fixed_cols = []
    for h1, h2 in df_raw.columns:
        h1 = str(h1).strip() if str(h1).lower() != "nan" else ""
        h2 = str(h2).strip() if str(h2).lower() != "nan" else ""

        # 🔥 FORCE Name column preservation
        if h1.lower() == "name":
            fixed_cols.append("Name")
        elif h2:
            fixed_cols.append(f"{h1} {h2}")
        else:
            fixed_cols.append(h1)

    df_raw.columns = fixed_cols

    # remove empty columns
    df = df_raw.loc[:, df_raw.columns.str.strip() != ""]
    return df


def get_subject_codes(df):
    subject_codes = set()

    for col in df.columns:
        col = col.strip()

        # Must be like: BCS501 Internal / External / Total / Result
        if " " not in col:
            continue

        prefix, suffix = col.rsplit(" ", 1)

        # Accept only subject-related suffixes
        if suffix not in ["Internal", "External", "Total", "Result"]:
            continue

        # STRICT VTU SUBJECT CODE FORMAT
        # Examples: BCS501, BAIL504, BCS515C, BIS586, BRMK557
        if re.fullmatch(r"[A-Z]{2,}\d{3}[A-Z]?", prefix):
            subject_codes.add(prefix)

    return sorted(subject_codes)


def extract_numeric(roll):
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges):
    roll_num = extract_numeric(roll_no)
    for sec_name, (start, end) in section_ranges.items():
        start_num = extract_numeric(start)
        end_num = extract_numeric(end)
        if start_num <= roll_num <= end_num:
            return sec_name
    return "Unassigned"

# ---------- PAGE LAYOUT ----------
layout = dbc.Container([
    html.H3("📊 Class Overview with Section Input", className="text-center mb-4 fw-bold"),

    # Upload Excel
    dbc.Card(
        dbc.CardBody([
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    html.I(className="bi bi-upload", style={'fontSize': '2rem'}),
                    " Drag and Drop or ",
                    html.A("Select Excel File", className="text-decoration-underline fw-semibold")
                ]),
                style={
                    'width': '100%', 'height': '70px', 'lineHeight': '70px',
                    'borderWidth': '2px', 'borderStyle': 'dashed',
                    'borderRadius': '15px', 'textAlign': 'center',
                    'backgroundColor': '#f4f6fb', 'cursor': 'pointer',
                    "color": "#4b5563", "fontWeight": 600
                },
                multiple=False
            ),
        ]),
        className="shadow-sm p-2 mb-4"
    ),

    # Subject selector
    dbc.Card(
        dbc.CardBody([
            html.H6("Select Subject(s):", className="fw-bold mb-1"),
            dcc.Dropdown(
                id='subject-selector',
                options=[], value=[],
                multi=True,
                placeholder="Upload file to select subjects",
                style={'maxHeight': '150px', 'overflowY': 'auto'}
            )
        ]),
        className="shadow-sm mb-4"
    ),

    # Section input, clean alignment and message
    dbc.Card(
        dbc.CardBody([
            html.H5(
                [html.I(className="bi bi-123 me-2", style={'fontSize': '2rem', 'color': '#2563eb'}),
                 "Define Sections:"],
                className="fw-bold text-center mb-3"
            ),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Number of Sections:", className="fw-semibold"),
                    dbc.Input(id='num-sections', type='number', min=1, max=10, step=1, value=1, className="mb-2"),
                ], md=5, xs=12),
                dbc.Col([
                    dbc.Button(
                        "Generate Section Inputs", id='generate-sections-btn',
                        color='dark', className='w-100 mt-md-4 mb-2 mb-md-0', style={"height": "48px"}
                    ),
                ], md=5, xs=12)
            ], className="mb-2 justify-content-center align-items-end gx-2"),
            html.Div(id='section-input-container', className='mt-2'),
            dbc.Button("Submit Sections", id='submit-sections-btn', color='success', className='w-100 mt-3'),
            html.Div(id="section-submit-message", className="mt-3")
        ]),
        className="shadow-sm mb-4"
    ),

    # KPI cards
    dbc.Row([
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6("Total Students", className="text-muted mb-2"),
                html.Div(html.I(className="bi bi-people-fill", style={'fontSize': '2rem', 'color': '#2563eb'}), className="mb-2"),
                html.H2(id="total-students", className="fw-bold text-primary")
            ]), className="shadow-sm h-100"), md=3, sm=6
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6("Present", className="text-muted mb-2"),
                html.Div(html.I(className="bi bi-person-check-fill", style={'fontSize': '2rem', 'color': '#64748b'}), className="mb-2"),
                html.H2(id="present-students", className="fw-bold text-secondary")
            ]), className="shadow-sm h-100"), md=3, sm=6
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6("Passed", className="text-muted mb-2"),
                html.Div(html.I(className="bi bi-award-fill", style={'fontSize': '2rem', 'color': '#059669'}), className="mb-2"),
                html.H2(id="passed-students", className="fw-bold text-success")
            ]), className="shadow-sm h-100"), md=3, sm=6
        ),
        dbc.Col(
            dbc.Card(dbc.CardBody([
                html.H6("Result %", className="text-muted mb-2"),
                html.Div(html.I(className="bi bi-pie-chart-fill", style={'fontSize': '2rem', 'color': '#f59e0b'}), className="mb-2"),
                html.H2(id="result-percent", className="fw-bold text-warning")
            ]), className="shadow-sm h-100"), md=3, sm=6
        ),
    ], className="mb-4 g-3 text-center justify-content-center"),

    html.Hr(),

    html.H5("📋 Uploaded Data Preview", className="text-center mb-3 fw-bold"),
    html.Div(id='data-preview', className="mt-3"),

    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True, className="py-4")


# ---------- CALLBACKS ----------
@callback(
    Output('subject-selector', 'options'),
    Output('subject-selector', 'value'),
    Output('stored-data', 'data'),
    Output('overview-selected-subjects', 'data'),
    Input('upload-data', 'contents'),
    prevent_initial_call=True
)
def populate_subject_dropdown(contents):
    if not contents:
        return [], [], None, None
    df = process_uploaded_excel(contents)
    subjects = get_subject_codes(df)
    options = [{'label': s, 'value': s} for s in subjects]
    json_data = df.to_json(date_format='iso', orient='split')
    return options, subjects, json_data, subjects

@callback(
    Output('section-input-container', 'children'),
    Input('generate-sections-btn', 'n_clicks'),
    State('num-sections', 'value'),
    prevent_initial_call=True
)
def generate_section_inputs(n_clicks, num_sections):
    if not n_clicks or not num_sections:
        return dash.no_update
    return [dbc.Row([
        dbc.Col(dbc.Input(id={'type': 'section-name', 'index': i},
                          placeholder=f"Section {i} Name", type='text', className="mb-2 border-2 shadow-sm"),
                width=3, sm=12, xs=12),
        dbc.Col(dbc.Input(id={'type': 'start-roll', 'index': i},
                          placeholder="Start Roll No", type='text', className="mb-2 border-2 shadow-sm"),
                width=4, sm=12, xs=12),
        dbc.Col(dbc.Input(id={'type': 'end-roll', 'index': i},
                          placeholder="End Roll No", type='text', className="mb-2 border-2 shadow-sm"),
                width=4, sm=12, xs=12),
    ], className='mb-2 justify-content-center gx-2') for i in range(1, num_sections + 1)]

@callback(
    Output('section-data', 'data'),
    Output('section-submit-message', 'children'),
    Input('submit-sections-btn', 'n_clicks'),
    State({'type': 'section-name', 'index': ALL}, 'value'),
    State({'type': 'start-roll', 'index': ALL}, 'value'),
    State({'type': 'end-roll', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def submit_sections(n_clicks, section_names, start_rolls, end_rolls):
    if not n_clicks:
        return dash.no_update, ""
    section_ranges = {}
    for name, start, end in zip(section_names, start_rolls, end_rolls):
        if name and start and end:
            section_ranges[name.strip()] = (start.strip(), end.strip())
    if section_ranges:
        message = dbc.Alert("✅ Sections submitted successfully!", color="success", className="text-center fw-semibold")
        return section_ranges, message
    else:
        message = dbc.Alert("⚠️ Please fill all fields for each section.", color="warning", className="text-center")
        return dash.no_update, message

@callback(
    [Output('total-students', 'children'),
     Output('present-students', 'children'),
     Output('passed-students', 'children'),
     Output('result-percent', 'children'),
     Output('data-preview', 'children')],
    Input('subject-selector', 'value'),
    Input('section-data', 'data'),
    State('stored-data', 'data')
)
def update_dashboard(selected_subjects, section_ranges, json_data):
    if json_data is None or not selected_subjects:
        return "", "", "", "", html.Div(
            [html.I(className="bi bi-info-circle me-2"), "Please upload file, select subjects, and define sections."],
            className="text-muted text-center border rounded p-3 bg-light"
        )
    df = pd.read_json(json_data, orient='split')
    meta_col = df.columns[0]
    # ✅ keep Name column if present (NOT a subject)
    base_cols = [meta_col]
    if 'Name' in df.columns:
        base_cols.append('Name')

    selected_cols = [
        c for c in df.columns
        if any(c.startswith(s) for s in selected_subjects)
    ]

    df_filtered = df[base_cols + selected_cols].copy()

    for c in selected_cols:
        if any(k in c for k in ['Internal', 'External', 'Total']):
            df_filtered[c] = pd.to_numeric(df_filtered[c], errors='coerce').fillna(0)

    show_section = False
    if section_ranges and isinstance(section_ranges, dict) and len(section_ranges) > 0:
        df_filtered['Section'] = df_filtered[meta_col].apply(lambda x: assign_section(str(x), section_ranges))
        show_section = True

    total_cols = [c for c in selected_cols if 'Total' in c]
    df_filtered['Total_Marks'] = df_filtered[total_cols].sum(axis=1) if total_cols else 0
    result_cols = [c for c in selected_cols if 'Result' in c]
    if result_cols:
        df_filtered['Overall_Result'] = df_filtered[result_cols].apply(
            lambda row: 'P' if all(v == 'P' for v in row if pd.notna(v)) else 'F', axis=1)
    else:
        df_filtered['Overall_Result'] = 'P'

    total_students = len(df_filtered)
    passed_students = (df_filtered['Overall_Result'] == 'P').sum()
    result_percent = round((passed_students / total_students) * 100, 2) if total_students > 0 else 0
    present_students = total_students

    table_df = df_filtered.copy()
    if not show_section:
        table_df = table_df.drop(columns=['Section'], errors='ignore')

    preview_table = html.Div([
        html.H6("Preview (first 10 rows):", className="fw-bold mb-2 text-primary"),
        dbc.Table.from_dataframe(table_df.head(10), striped=True, bordered=True, hover=True, className="shadow-sm table-sm border mb-3 bg-white", style={'fontSize': '0.98rem'})
    ])

    return total_students, present_students, passed_students, f"{result_percent}%", preview_table
