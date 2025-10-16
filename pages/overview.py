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
    df = pd.read_excel(io.BytesIO(decoded), header=[0, 1])  # Multi-level header
    df.columns = [' '.join([str(i) for i in col if str(i) != 'nan']).strip() for col in df.columns.values]
    df = df.loc[:, df.columns.str.strip() != '']  # remove empty cols
    return df

def get_subject_codes(df):
    cols = df.columns[1:]  # skip first metadata column
    cols = [c for c in cols if c.strip() != '']
    subject_codes = sorted(list(set([c.split()[0] for c in cols])))
    return subject_codes

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
    html.H4("📊 Class Overview with Section Input", className="text-center mb-4 fw-bold"),

    # Upload Excel
    dcc.Upload(
        id='upload-data',
        children=html.Div(['📁 Drag and Drop or ', html.A('Select Excel File')]),
        style={
            'width': '100%', 'height': '70px', 'lineHeight': '70px',
            'borderWidth': '2px', 'borderStyle': 'dashed',
            'borderRadius': '12px', 'textAlign': 'center',
            'marginBottom': '25px', 'backgroundColor': '#f9fafb',
            'cursor': 'pointer'
        },
        multiple=False
    ),

    # Subject selector
    dbc.Card(
        dbc.CardBody([
            html.H6("Select Subject(s):", className="fw-bold"),
            dcc.Dropdown(
                id='subject-selector',
                options=[], value=[],
                multi=True,
                placeholder="Upload file to select subjects",
                style={'maxHeight': '150px', 'overflowY': 'auto'}
            )
        ]),
        className="shadow-sm p-3 mb-4"
    ),

    # Section input
    dbc.Card(
        dbc.CardBody([
            html.H6("Define Sections:", className="fw-bold mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Number of Sections:"),
                    dbc.Input(id='num-sections', type='number', min=1, max=10, step=1, value=1)
                ], md=3, sm=12),
                dbc.Col([
                    dbc.Button("Generate Section Inputs", id='generate-sections-btn', color='primary', className='mt-2 mt-md-4')
                ], md=3, sm=12),
            ], className="mb-3 g-3"),
            html.Div(id='section-input-container', className='mt-2'),
            dbc.Button("Submit Sections", id='submit-sections-btn', color='success', className='mt-3')
        ]),
        className="shadow-sm p-3 mb-4"
    ),

    # KPI cards
    dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6("Total Students", className="text-muted"),
                    html.H2(id="total-students", className="fw-bold text-primary")
                ]),
                style={
                    "backgroundColor": "#dbeafe",
                    "borderLeft": "6px solid #3b82f6",
                    "borderRadius": "12px",
                    "boxShadow": "0 4px 15px rgba(0,0,0,0.1)",
                    "textAlign": "center",
                    "padding": "20px"
                }
            ), md=3, sm=6
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6("Present Students", className="text-muted"),
                    html.H2(id="present-students", className="fw-bold text-secondary")
                ]),
                style={
                    "backgroundColor": "#e5e7eb",
                    "borderLeft": "6px solid #6b7280",
                    "borderRadius": "12px",
                    "boxShadow": "0 4px 15px rgba(0,0,0,0.1)",
                    "textAlign": "center",
                    "padding": "20px"
                }
            ), md=3, sm=6
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6("Passed Students", className="text-muted"),
                    html.H2(id="passed-students", className="fw-bold text-success")
                ]),
                style={
                    "backgroundColor": "#d1fae5",
                    "borderLeft": "6px solid #10b981",
                    "borderRadius": "12px",
                    "boxShadow": "0 4px 15px rgba(0,0,0,0.1)",
                    "textAlign": "center",
                    "padding": "20px"
                }
            ), md=3, sm=6
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H6("Result %", className="text-muted"),
                    html.H2(id="result-percent", className="fw-bold text-warning")
                ]),
                style={
                    "backgroundColor": "#fef3c7",
                    "borderLeft": "6px solid #f59e0b",
                    "borderRadius": "12px",
                    "boxShadow": "0 4px 15px rgba(0,0,0,0.1)",
                    "textAlign": "center",
                    "padding": "20px"
                }
            ), md=3, sm=6
        ),
    ], className="mb-4 g-3 text-center"),

    html.Hr(),

    html.H5("📋 Uploaded Data Preview", className="text-center mb-3 fw-bold"),
    html.Div(id='data-preview', className="mt-3"),

    # Stores
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session')
], fluid=True)

# ---------- CALLBACKS ----------
# 1️⃣ Populate dropdown & store uploaded data
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

# 2️⃣ Generate section input fields
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
                          placeholder=f"Section {i} Name", type='text'), width=3),
        dbc.Col(dbc.Input(id={'type': 'start-roll', 'index': i},
                          placeholder="Start Roll No", type='text'), width=4),
        dbc.Col(dbc.Input(id={'type': 'end-roll', 'index': i},
                          placeholder="End Roll No", type='text'), width=4),
    ], className='mb-2') for i in range(1, num_sections + 1)]

# 3️⃣ Submit sections & store in session
@callback(
    Output('section-data', 'data'),
    Input('submit-sections-btn', 'n_clicks'),
    State({'type': 'section-name', 'index': ALL}, 'value'),
    State({'type': 'start-roll', 'index': ALL}, 'value'),
    State({'type': 'end-roll', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def submit_sections(n_clicks, section_names, start_rolls, end_rolls):
    if not n_clicks:
        return dash.no_update
    section_ranges = {}
    for name, start, end in zip(section_names, start_rolls, end_rolls):
        if name and start and end:
            section_ranges[name.strip()] = (start.strip(), end.strip())
    return section_ranges if section_ranges else dash.no_update

# 4️⃣ Update KPIs + table dynamically
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
        return "", "", "", "", html.Div("⬆️ Please upload file, select subjects, and define sections.",
                                        className="text-muted text-center")
    df = pd.read_json(json_data, orient='split')
    meta_col = df.columns[0]
    selected_cols = [c for c in df.columns if any(c.startswith(s) for s in selected_subjects)]
    df_filtered = df[[meta_col] + selected_cols].copy()

    # Convert numeric columns
    for c in selected_cols:
        if any(k in c for k in ['Internal', 'External', 'Total']):
            df_filtered[c] = pd.to_numeric(df_filtered[c], errors='coerce').fillna(0)

    # Assign section only if section_ranges exist
    show_section = False
    if section_ranges and isinstance(section_ranges, dict) and len(section_ranges) > 0:
        df_filtered['Section'] = df_filtered[meta_col].apply(lambda x: assign_section(str(x), section_ranges))
        show_section = True

    # Compute total & result
    total_cols = [c for c in selected_cols if 'Total' in c]
    df_filtered['Total_Marks'] = df_filtered[total_cols].sum(axis=1) if total_cols else 0
    result_cols = [c for c in selected_cols if 'Result' in c]
    if result_cols:
        df_filtered['Overall_Result'] = df_filtered[result_cols].apply(
            lambda row: 'P' if all(v == 'P' for v in row if pd.notna(v)) else 'F', axis=1)
    else:
        df_filtered['Overall_Result'] = 'P'

    # KPI metrics
    total_students = len(df_filtered)
    passed_students = (df_filtered['Overall_Result'] == 'P').sum()
    result_percent = round((passed_students / total_students) * 100, 2) if total_students > 0 else 0
    present_students = total_students

    # Preview table (hide Section if not submitted)
    table_df = df_filtered.copy()
    if not show_section:
        table_df = table_df.drop(columns=['Section'], errors='ignore')

    preview_table = html.Div([
        html.H6("Preview (first 10 rows):", className="fw-bold mb-2"),
        dbc.Table.from_dataframe(table_df.head(10), striped=True, bordered=True, hover=True, className="shadow-sm table-sm")
    ])

    return total_students, present_students, passed_students, f"{result_percent}%", preview_table

