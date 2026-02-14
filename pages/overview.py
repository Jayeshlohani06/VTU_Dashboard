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

def assign_section(roll_no, section_ranges, usn_mapping=None):
    """Assigns sections based on either specific mapping or numeric roll number ranges."""
    roll_no_str = str(roll_no).strip().upper()
    
    # Check direct mapping first
    if usn_mapping:
         # Ensure usn_mapping keys are all upper/stripped just in case
         # (Though we do this at upload time, safe to cover bases)
         if roll_no_str in usn_mapping:
             return usn_mapping[roll_no_str]
    
    # Then check ranges if mapping not found
    roll_num = extract_numeric(roll_no)
    if section_ranges:
        for sec_name, (start, end) in section_ranges.items():
            start_num = extract_numeric(start)
            end_num = extract_numeric(end)
            if start_num <= roll_num <= end_num:
                return sec_name
    return "Unassigned"

def process_usn_mapping_file(contents, filename, section_name=None):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(decoded))
        
        # Clean column names
        df.columns = df.columns.astype(str).str.strip().str.lower()
        
        # Scenario 1: Section name provided (Single section upload)
        if section_name:
            # Look for USN column only
            usn_col = next((c for c in df.columns if 'usn' in c), None)
            if usn_col:
                 # Map all USNs in this file to the provided section_name
                 return {usn: section_name for usn in df[usn_col].astype(str).str.strip().str.upper()}
            return {}

        # Scenario 2: No section name (Global mapping file)
        # Find USN and Section columns
        usn_col = next((c for c in df.columns if 'usn' in c), None)
        section_col = next((c for c in df.columns if 'section' in c or 'sec' in c), None)
        
        if usn_col and section_col:
            # Create mapping: USN -> Section
            return dict(zip(df[usn_col].astype(str).str.strip().str.upper(), df[section_col].astype(str).str.strip()))
        return {}
    except Exception as e:
        print(f"Error processing USN file: {e}")
        return {}

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
        html.P("Analyze university results with custom section filtering", className="text-white-50 mb-0"),
        dbc.Button("ℹ️ Logic & Legends", id="open-legend-overview", color="light", size="sm", className="mt-3 fw-bold", outline=True)
    ], style={
        "background": "linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%)", 
        "padding": "2.0rem 1rem", 
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
                    
                    html.Label("Section Config Mode", className="small fw-bold mb-2"),
                    dbc.RadioItems(
                        id="config-mode-selector",
                        options=[
                            {"label": "Manual Ranges", "value": "manual"},
                            {"label": "Upload Files", "value": "upload"},
                        ],
                        value="manual",
                        inline=True,
                        className="mb-3 small",
                        inputClassName="me-1",
                        labelClassName="me-3"
                    ),

                    # --- MANUAL MODE ---
                    html.Div([
                        html.Label("Define Ranges", className="small fw-bold mb-1"),
                        dbc.InputGroup([
                            dbc.Input(id='num-sections', type='number', value=1, min=1, max=10),
                            dbc.Button("Generate", id='generate-sections-btn', color="secondary"),
                        ], size="sm", className="mb-3"),
                        
                        html.Div(id='section-input-container'),
                        dbc.Button("Apply Ranges", id='submit-sections-btn', color='info', className='w-100 mt-2 fw-bold text-white'),
                    ], id="manual-section-container"),

                    # --- UPLOAD MODE ---
                    html.Div([
                        html.Label("Upload per Section", className="small fw-bold mb-1"),
                        dbc.InputGroup([
                            dbc.Input(id='num-upload-sections', type='number', value=1, min=1, max=10),
                            dbc.Button("Generate", id='generate-upload-sections-btn', color="secondary"),
                        ], size="sm", className="mb-3"),
                        
                        html.Div(id='upload-sections-container'),
                    ], id="upload-section-container", style={"display": "none"}),

                    html.Div(id='usn-upload-status', className="small text-muted mt-2 fw-bold"),
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

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("📊 Dashboard Usage Guide")),
        dbc.ModalBody(
            html.Div([
                html.H6("📥 1. data Extraction", className="text-primary fw-bold"),
                html.P("Upload the raw VTU result Excel file to initialize the dashboard.", className="text-muted small mb-2"),
                html.Ul([
                    html.Li([html.Strong("File Format:"), " .xlsx or .xls file."]),
                    html.Li([html.Strong("Structure:"), " Multi-row header format (standard VTU result sheet)."]),
                    html.Li("Must contain 'USN' (or 'Student ID') and 'Name' columns."),
                    html.Li("Subject columns should clearly indicate 'Internal', 'External', and 'Total'."),
                ]),
                html.Hr(),
                html.H6("⚙️ 2. Section Configuration", className="text-primary fw-bold"),
                html.P("Map students to their respective classrooms/sections:", className="text-muted small mb-2"),
                html.Ul([
                     html.Li([html.Strong("Manual Ranges:"), " Use for sequential USNs. Define start/end numbers (e.g., 001-060 = Section A)."]),
                     html.Li([html.Strong("Upload Mapping:"), " Use for non-sequential lists. Upload a CSV/Excel with 'USN' and 'Section' columns."]),
                ]),
                html.Hr(),
                html.H6("📊 3. Analytics & Outputs", className="text-primary fw-bold"),
                html.Ul([
                    html.Li("Real-time extraction of unique subjects found in the file."),
                    html.Li("Instant calculation of Pass Rate, Total Count, and Attendance."),
                    html.Li("Preview of the processed data table with filtering options."),
                    html.Li("Data persists across pages (Ranking, Analysis) once loaded."),
                ], className="mb-0")
            ])
        ),
        dbc.ModalFooter(dbc.Button("Got it!", id="close-legend-overview", className="ms-auto", color="primary"))
    ], id="legend-modal-overview", is_open=False, size="lg", style={"zIndex": 10500}),

    # STORES REMOVED FROM HERE TO APP.PY TO ENSURE PERSISTENCE
    
], fluid=True, className="pb-5 bg-light", style={"minHeight": "100vh"})

# ---------- CALLBACKS ----------

@callback(
    Output("legend-modal-overview", "is_open"),
    [Input("open-legend-overview", "n_clicks"), Input("close-legend-overview", "n_clicks")],
    [State("legend-modal-overview", "is_open")],
    prevent_initial_call=True
)
def toggle_legend_overview(n1, n2, is_open): return not is_open if n1 or n2 else is_open

@callback(
    [Output("manual-section-container", "style"),
     Output("upload-section-container", "style")],
    Input("config-mode-selector", "value")
)
def toggle_config_mode(mode):
    if mode == "upload":
        return {"display": "none"}, {"display": "block"}
    # Default manual
    return {"display": "block"}, {"display": "none"}

@callback(
    Output('subject-selector', 'options'),
    Output('subject-selector', 'value'),
    Output('stored-data', 'data'),
    Output('overview-selected-subjects', 'data'),
    Output('subject-options-store', 'data'),
    Input('upload-data', 'contents'),
    Input('subject-options-store', 'data'),
    Input('url', 'pathname'),
    State('overview-selected-subjects', 'data'),
    prevent_initial_call=False
)
def manage_subjects(upload_contents, stored_options, pathname, stored_subjects):
    if pathname != "/" and pathname is not None:
        return no_update, no_update, no_update, no_update, no_update

    ctx_id = ctx.triggered_id

    # 1️⃣ If new file uploaded (Explicit User Action)
    if ctx_id == 'upload-data' and upload_contents:
        df = process_uploaded_excel(upload_contents)
        if df.empty:
            return [], [], None, None, None

        subjects = get_subject_codes(df)
        options = [{'label': s, 'value': s} for s in subjects]
        json_data = df.to_json(date_format='iso', orient='split')

        return options, subjects, json_data, subjects, options

    # 2️⃣ If data already exists in session (Navigation / Restore)
    if stored_options:
        safe_subjects = stored_subjects if isinstance(stored_subjects, list) else []
        return stored_options, safe_subjects, no_update, no_update, no_update

    # 3️⃣ Default empty state
    return [], [], no_update, no_update, no_update

@callback(
    Output('overview-selected-subjects', 'data', allow_duplicate=True),
    Input('subject-selector', 'value'),
    prevent_initial_call=True
)
def update_selected_subjects_store(selected_values):
    return selected_values

@callback(
    Output('section-input-container', 'children'),
    Input('generate-sections-btn', 'n_clicks'),
    Input('section-data', 'data'), # Listen to store changes or initial load
    State('num-sections', 'value'),
    prevent_initial_call=False
)
def render_section_fields(n_clicks, stored_sections, num_sections):
    ctx_id = ctx.triggered_id
    
    # 1. Button Click - Generate New Empty Fields
    if ctx_id == 'generate-sections-btn' and n_clicks:
        count = num_sections if num_sections else 1
        return [
            dbc.Row([
                dbc.Col(dbc.Input(id={'type': 'sec-n', 'index': i}, placeholder="Name", size="sm"), width=3),
                dbc.Col(dbc.Input(id={'type': 'sec-s', 'index': i}, placeholder="Start USN", size="sm"), width=4),
                dbc.Col(dbc.Input(id={'type': 'sec-e', 'index': i}, placeholder="End USN", size="sm"), width=4),
            ], className="g-2 mb-2") for i in range(1, count + 1)
        ]

    # 2. Restore from Store (Initial Load or Store Update)
    if stored_sections and isinstance(stored_sections, dict):
        rows = []
        for i, (name, (start, end)) in enumerate(stored_sections.items()):
            rows.append(dbc.Row([
                dbc.Col(dbc.Input(id={'type': 'sec-n', 'index': i+1}, value=name, placeholder="Name", size="sm"), width=3),
                dbc.Col(dbc.Input(id={'type': 'sec-s', 'index': i+1}, value=start, placeholder="Start USN", size="sm"), width=4),
                dbc.Col(dbc.Input(id={'type': 'sec-e', 'index': i+1}, value=end, placeholder="End USN", size="sm"), width=4),
            ], className="g-2 mb-2"))
        if rows:
            return rows

    # Default empty
    return []


@callback(
    Output('upload-sections-container', 'children'),
    Input('generate-upload-sections-btn', 'n_clicks'),
    State('num-upload-sections', 'value'),
    prevent_initial_call=True
)
def render_upload_section_fields(n, num):
    if not n or not num: return no_update
    return [
        dbc.Row([
            dbc.Col(dbc.Input(id={'type': 'usec-n', 'index': i}, placeholder=f"Sec {chr(65 + i)} Name", size="sm"), width=4),
            dbc.Col(
                dcc.Upload(
                    id={'type': 'usec-u', 'index': i},
                    children=html.Div(['📂 Upload USN List'], style={'fontSize': '0.8rem', 'fontWeight': 'bold'}),
                    style={
                        'width': '100%', 'height': '31px', 'lineHeight': '31px', 
                        'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '4px',
                        'textAlign': 'center', 'backgroundColor': '#f0f2f5', 'cursor': 'pointer',
                        'color': '#495057'
                    },
                    multiple=False
                ), width=8
            ),
        ], className="g-2 mb-2 align-items-center") for i in range(0, num)
    ]


@callback(
    Output('section-data', 'data'),
    Output('submit-sections-btn', 'children'), # Visual feedback on button
    Input('submit-sections-btn', 'n_clicks'),
    [State({'type': 'sec-n', 'index': ALL}, 'value'),
     State({'type': 'sec-s', 'index': ALL}, 'value'),
     State({'type': 'sec-e', 'index': ALL}, 'value'),
     State('section-data', 'data')],
    prevent_initial_call=True
)
def save_sections(n, names, starts, ends, current_data):
    if not n: return no_update, "Apply Config & Refresh"
    
    # Create new dict from inputs
    new_section_dict = {str(n).strip(): (str(s).strip(), str(e).strip()) for n, s, e in zip(names, starts, ends) if n and s and e}
    
    # If inputs are empty (user cleared them), we should probably clear the store too?
    # Or keep the old store? Given "Apply" button intent, if you see empty fields and click Apply, you expect clear.
    # However, since fields might not have rendered yet (if manage_subjects is slow?), we should be careful.
    # But save_sections is triggered by CLICK, so fields must exist.
    
    return new_section_dict, "✅ Config Applied"

@callback(
    Output('usn-mapping-store', 'data'),
    Output('usn-upload-status', 'children'),
    [Input({'type': 'usec-u', 'index': ALL}, 'contents')],
    [State({'type': 'usec-u', 'index': ALL}, 'filename'),
     State({'type': 'usec-n', 'index': ALL}, 'value'),
     State('usn-mapping-store', 'data')],
    prevent_initial_call=True
)
def process_multi_usn_upload(all_contents, all_filenames, all_names, current_mapping):
    # Ensure all_contents is a list, otherwise return
    if not isinstance(all_contents, list) or not any(all_contents):
        return no_update, ""
    
    # Initialize or copy existing mapping
    mapping = current_mapping.copy() if current_mapping else {}
    new_entries_count = 0
    
    # Iterate through all upload components
    for i, content in enumerate(all_contents):
        if content: # If this specific upload has content
             name = all_names[i] if i < len(all_names) else None
             filename = all_filenames[i] if i < len(all_filenames) else ""
             
             # Determine section name (User input > Default A, B, C...)
             sec_name = name.strip() if name and name.strip() else f"Section {chr(65+i)}"
             
             # Process the file for this specific section mapping
             file_mapping = process_usn_mapping_file(content, filename, sec_name)
             
             if file_mapping:
                 mapping.update(file_mapping)
                 new_entries_count += len(file_mapping)
    
    total_entries = len(mapping)
    if total_entries > 0:
        return mapping, f"✅ Total {total_entries} USNs mapped"
    
    return no_update, "ℹ️ No valid USNs found in uploaded files"

@callback(
    [Output('total-students', 'children'),
     Output('present-students', 'children'),
     Output('passed-students', 'children'),
     Output('result-percent', 'children'),
     Output('data-preview', 'children')],
    [Input('stored-data', 'data'),
     Input('subject-selector', 'value'),
     Input('section-data', 'data'),
     Input('usn-mapping-store', 'data')]
)
def update_dashboard(data, selected_subjects, section_ranges, usn_mapping):
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
    if section_ranges or usn_mapping:
        df_filtered['Section'] = df_filtered[meta_col].apply(lambda x: assign_section(x, section_ranges, usn_mapping))

    # 6. Generate Table UI
    table = dbc.Table.from_dataframe(
        df_filtered.head(10), 
        striped=True, borderless=True, hover=True, responsive=True, 
        className="mb-0 align-middle",
        style={"fontSize": "0.85rem"}
    )

    return str(total), str(total), str(passed_count), rate, table