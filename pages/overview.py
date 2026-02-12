import dash
from dash import html, dcc, Input, Output, State, callback, ALL, no_update, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import re

dash.register_page(__name__, path='/', name="Overview")

# ---------- HELPER FUNCTIONS ----------

def process_uploaded_excel(contents):
    """Processes Excel with Multi-Index headers and cleans column names."""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        # Handles the University/Subject structure
        df_raw = pd.read_excel(io.BytesIO(decoded), header=[0, 1])

        fixed_cols = []
        for h1, h2 in df_raw.columns:
            h1 = str(h1).strip() if str(h1).lower() != "nan" else ""
            h2 = str(h2).strip() if str(h2).lower() != "nan" else ""

            # Preserve Name/Identity columns, merge others
            if h1.lower() == "name" or any(x in h1.lower() for x in ["seat", "usn", "sl"]):
                fixed_cols.append("Name" if h1.lower() == "name" else h1)
            elif h2:
                fixed_cols.append(f"{h1} {h2}")
            else:
                fixed_cols.append(h1)

        df_raw.columns = fixed_cols
        # Remove empty columns
        df = df_raw.loc[:, df_raw.columns.str.strip() != ""]
        return df
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def get_subject_codes(df):
    """Extracts unique subject codes using strict VTU format."""
    subject_codes = set()
    for col in df.columns:
        col = col.strip()
        if " " not in col:
            continue
        prefix, suffix = col.rsplit(" ", 1)
        if suffix in ["Internal", "External", "Total", "Result"]:
            if re.fullmatch(r"[A-Z]{2,}\d{3}[A-Z]?", prefix):
                subject_codes.add(prefix)
    return sorted(list(subject_codes))

def extract_numeric(roll):
    """Extracts the numeric part of a USN/Roll Number safely."""
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges):
    """Assigns sections based on numeric roll number ranges."""
    roll_num = extract_numeric(roll_no)
    for sec_name, (start, end) in section_ranges.items():
        start_num = extract_numeric(start)
        end_num = extract_numeric(end)
        if start_num <= roll_num <= end_num:
            return sec_name
    return "Unassigned"

# ---------- UI COMPONENTS ----------

def kpi_card(title, value, id_val, icon, color):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.I(className=f"bi {icon} mb-2", style={"fontSize": "1.8rem", "color": color}),
                html.H3(children=value, id=id_val, className="fw-bold mb-0", style={"color": color}),
                html.Small(title, className="text-muted fw-bold text-uppercase", style={"letterSpacing": "0.5px", "fontSize": "0.75rem"})
            ], className="text-center")
        ])
    ], className="border-0 shadow-sm h-100", style={"borderRadius": "12px"})

# ---------- LAYOUT ----------

layout = dbc.Container([
    # Hero Header
    html.Div([
        html.H2("Student Performance Dashboard", className="fw-bold text-white mb-1"),
        html.P("Analyze university results with custom section filtering", className="text-white-50 mb-0")
    ], style={
        "background": "linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%)", 
        "padding": "2.5rem 1rem", 
        "borderRadius": "0 0 15px 15px", 
        "textAlign": "center", 
        "marginBottom": "2rem"
    }),

    dbc.Row([
        # Left Sidebar: Inputs
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("1. Data Intake", className="fw-bold bg-light"),
                dbc.CardBody([
                    dcc.Upload(
                        id='upload-data',
                        children=html.Div(["Drop Excel File or ", html.B("Click to Upload")]),
                        style={
                            'width': '100%', 'height': '70px', 'lineHeight': '70px', 
                            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px', 
                            'textAlign': 'center', 'backgroundColor': '#fbfcfc', 'cursor': 'pointer'
                        }
                    )
                ], style={"overflow": "visible"}),
            ], className="mb-4 border-0 shadow-sm", style={"overflow": "visible"}),

            dbc.Card([
                dbc.CardHeader("2. Configuration", className="fw-bold bg-light", style={"overflow": "visible"}),
                dbc.CardBody([
                    html.Label("Filter Subjects", className="small fw-bold mb-1"),
                    html.Div([
                        dcc.Dropdown(
                            id='subject-selector', 
                            multi=True, 
                            className="mb-3 custom-dropdown",
                            optionHeight=50,
                            maxHeight=300,
                            style={
                                "position": "relative", 
                                "zIndex": "1000",
                                "minHeight": "45px"
                            }
                        )
                    ], style={"overflow": "visible", "position": "relative", "zIndex": "1000"}),
                    html.Div(style={"height": "10px"}),
                    
                    html.Label("Manage Sections", className="small fw-bold mb-1"),
                    dbc.InputGroup([
                        dbc.Input(id='num-sections', type='number', value=1, min=1, max=10),
                        dbc.Button("Generate", id='generate-sections-btn', color="secondary"),
                    ], size="sm", className="mb-3"),
                    
                    html.Div(id='section-input-container'),
                    dbc.Button("Apply Config & Refresh", id='submit-sections-btn', color='info', className='w-100 mt-3 fw-bold text-white'),
                ], style={"overflow": "visible", "position": "relative"}),
            ], className="border-0 shadow-sm", style={"overflow": "visible"})
        ], lg=4, md=5, style={"overflow": "visible"}),

        # Right Main: Analytics
        dbc.Col([
            # KPI Cards
            dbc.Row([
                dbc.Col(kpi_card("Total Students", "0", "total-students", "bi-people-fill", "#3498db"), width=6, lg=3),
                dbc.Col(kpi_card("Present", "0", "present-students", "bi-person-check-fill", "#27ae60"), width=6, lg=3),
                dbc.Col(kpi_card("Passed", "0", "passed-students", "bi-check-all", "#16a085"), width=6, lg=3),
                dbc.Col(kpi_card("Pass Rate", "0%", "result-percent", "bi-graph-up-arrow", "#f39c12"), width=6, lg=3),
            ], className="g-3 mb-4"),

            # Table Card
            dbc.Card([
                dbc.CardHeader([
                    html.H6("Top 10 Data Preview", className="mb-0 fw-bold d-inline-block"),
                    html.Small(" (Filtered by Selection)", className="text-muted ms-2")
                ], className="bg-white py-3"),
                dbc.CardBody([
                    dcc.Loading(
                        id="loading-table", 
                        children=html.Div(id='data-preview'), 
                        type="default", 
                        color="#3498db"
                    )
                ], className="p-0")
            ], className="border-0 shadow-sm overflow-hidden")
        ], lg=8, md=7)
    ], style={"overflow": "visible"}),

    # Session stores for persistence across pages
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session'),
    dcc.Store(id='overview-selected-subjects', storage_type='session'),
    dcc.Store(id='subject-options-store', storage_type='session')
], fluid=True, className="pb-5 bg-light", style={"minHeight": "100vh"})

# ---------- CALLBACKS ----------

@callback(
    Output('subject-selector', 'options'),
    Output('subject-selector', 'value'),
    Output('stored-data', 'data'),
    Output('overview-selected-subjects', 'data'),
    Output('subject-options-store', 'data'),
    Input('upload-data', 'contents'),
    Input('subject-options-store', 'data'),
    Input('overview-selected-subjects', 'data'),
    prevent_initial_call=False
)
def manage_subjects(upload_contents, stored_options, stored_subjects):
    # NEW UPLOAD - process fresh data
    if upload_contents:
        df = process_uploaded_excel(upload_contents)
        if df.empty:
            return [], [], None, None, None
        subjects = get_subject_codes(df)
        options = [{'label': s, 'value': s} for s in subjects]
        json_data = df.to_json(date_format='iso', orient='split')
        return options, subjects, json_data, subjects, options
    
    # RESTORE FROM STORAGE - when page reloads without new upload
    if stored_options and stored_subjects:
        return stored_options, stored_subjects, no_update, no_update, no_update
    
    # DEFAULT - empty state
    return [], [], None, None, None

@callback(
    Output('section-input-container', 'children'),
    Input('generate-sections-btn', 'n_clicks'),
    State('num-sections', 'value'),
    prevent_initial_call=True
)
def render_section_fields(n, num):
    if not n or not num: return no_update
    return [
        dbc.Row([
            dbc.Col(dbc.Input(id={'type': 'sec-n', 'index': i}, placeholder="Name", size="sm"), width=3),
            dbc.Col(dbc.Input(id={'type': 'sec-s', 'index': i}, placeholder="Start USN", size="sm"), width=4),
            dbc.Col(dbc.Input(id={'type': 'sec-e', 'index': i}, placeholder="End USN", size="sm"), width=4),
        ], className="g-2 mb-2") for i in range(1, num + 1)
    ]

@callback(
    Output('section-data', 'data'),
    Output('submit-sections-btn', 'children'), # Visual feedback on button
    Input('submit-sections-btn', 'n_clicks'),
    [State({'type': 'sec-n', 'index': ALL}, 'value'),
     State({'type': 'sec-s', 'index': ALL}, 'value'),
     State({'type': 'sec-e', 'index': ALL}, 'value')],
    prevent_initial_call=True
)
def save_sections(n, names, starts, ends):
    if not n: return no_update, "Apply Config & Refresh"
    section_dict = {str(n).strip(): (str(s).strip(), str(e).strip()) for n, s, e in zip(names, starts, ends) if n and s and e}
    return section_dict, "✅ Config Applied"

@callback(
    [Output('total-students', 'children'),
     Output('present-students', 'children'),
     Output('passed-students', 'children'),
     Output('result-percent', 'children'),
     Output('data-preview', 'children')],
    [Input('stored-data', 'data'),
     Input('subject-selector', 'value'),
     Input('section-data', 'data')]
)
def update_dashboard(data, selected_subjects, section_ranges):
    if not data or not selected_subjects:
        return "0", "0", "0", "0%", html.Div("Upload data and select subjects to view analytics.", className="p-4 text-center text-muted")
    
    df = pd.read_json(data, orient='split')
    meta_col = df.columns[0]
    
    # 1. Filter relevant columns
    all_subject_codes = get_subject_codes(df)
    relevant_cols = [c for c in df.columns if any(c.startswith(s) for s in selected_subjects)]
    info_cols = [c for c in df.columns if not any(s in c for s in all_subject_codes)]
    
    df_filtered = df[info_cols + relevant_cols].copy()

    # 2. Convert Mark columns to Numeric
    for c in relevant_cols:
        if any(k in c for k in ['Internal', 'External', 'Total']):
            df_filtered[c] = pd.to_numeric(df_filtered[c], errors='coerce').fillna(0)

    # 3. Robust Pass Logic (Case-insensitive 'P')
    res_cols = [c for c in relevant_cols if "Result" in c]
    if res_cols:
        df_filtered['Overall_Result'] = df_filtered[res_cols].apply(
            lambda row: 'P' if all(str(v).strip().upper() == 'P' for v in row if pd.notna(v)) else 'F', 
            axis=1
        )
    else:
        df_filtered['Overall_Result'] = 'P'

    # 4. Metrics calculation
    total = len(df_filtered)
    passed_count = (df_filtered['Overall_Result'] == 'P').sum()
    rate = f"{round((passed_count/total)*100, 2)}%" if total > 0 else "0%"

    # 5. Section Assignment
    if section_ranges:
        df_filtered['Section'] = df_filtered[meta_col].apply(lambda x: assign_section(x, section_ranges))

    # 6. Generate Table UI
    table = dbc.Table.from_dataframe(
        df_filtered.head(10), 
        striped=True, borderless=True, hover=True, responsive=True, 
        className="mb-0 align-middle",
        style={"fontSize": "0.85rem"}
    )

    return str(total), str(total), str(passed_count), rate, table