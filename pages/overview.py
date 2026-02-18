import dash
from dash import html, dcc, Input, Output, State, callback, ALL, no_update, ctx
import dash_bootstrap_components as dbc
import pandas as pd
import base64
import io
import re


dash.register_page(__name__, path='/', name="Overview")

# ==================== Styles ====================

PAGE_CSS_LIGHT = r"""
:root{
  --bg: #f5f7fb;
  --card: #ffffff;
  --text: #1f2937;
  --muted:#6b7280;
  --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --k1:#fffbeb; --k2:#eff6ff; --k3:#fff7ed; --k45:#f8fafc;
  --pass-bg:#ecfdf5; --pass-text:#065f46;
  --fail-bg:#fef2f2; --fail-text:#991b1b;
}
.rnk-wrap{ background: var(--bg); padding: 20px; border-radius: 16px; }
.rnk-card{
  background: var(--card); border: 0 !important; border-radius: 12px !important;
  box-shadow: var(--shadow); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.rnk-card:hover{ transform: translateY(-2px); box-shadow: var(--shadow-hover); }
.kpi-card{ border-left: 4px solid transparent; height: 100%; display: flex; flex-direction: column; justify-content: center; }
.kpi-label{ color: var(--muted); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value{ font-weight: 800; font-size: 2.2rem; line-height: 1.2; }
.rank-chip{ display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%; font-weight:700; font-size:0.9rem; margin-right:8px; }
.rank-1{ background:var(--k1); color:#b45309; border:1px solid #fcd34d; }
.rank-2{ background:var(--k2); color:#1e40af; border:1px solid #93c5fd; }
.rank-3{ background:var(--k3); color:#9a3412; border:1px solid #fdba74; }
.rank-4,.rank-5{ background:var(--k45); color:#475569; border:1px solid #e2e8f0; }
.badge-pass{ background:var(--pass-bg); color:var(--pass-text); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; letter-spacing:0.5px; }
.badge-fail{ background:var(--fail-bg); color:var(--fail-text); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; letter-spacing:0.5px; }
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td{ border-bottom: 1px solid #f1f5f9 !important; }
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th{ border-bottom: 2px solid #e2e8f0 !important; font-weight: 700 !important; }
.accordion-button:not(.collapsed){ background-color: #eff6ff; color: #1e40af; }
.accordion-button{ color: #1f2937; }
.table { margin-bottom: 0; }
.table tbody tr { border-bottom: 1px solid #e9ecef; }
.table tbody tr:hover { background-color: #f8f9fa; }
.table thead { border-top: 2px solid #dee2e6; }
"""

PAGE_CSS_DARK = r"""
:root{
  --bg: #0f172a;
  --card: #1e293b;
  --text: #f8fafc;
  --muted:#94a3b8;
  --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
  --shadow-hover: 0 10px 15px -3px rgba(0, 0, 0, 0.6);
  --k1:#451a03; --k2:#172554; --k3:#431407; --k45:#334155;
  --pass-bg:#064e3b; --pass-text:#a7f3d0;
  --fail-bg:#7f1d1d; --fail-text:#fecaca;
}
.rnk-wrap{ background: var(--bg); padding: 20px; border-radius: 16px; }
.rnk-card{
  background: var(--card); border: 0 !important; border-radius: 12px !important;
  box-shadow: var(--shadow); transition: all 0.3s ease; color: var(--text);
}
.rnk-card:hover{ transform: translateY(-2px); box-shadow: var(--shadow-hover); }
.kpi-card{ border-left: 4px solid transparent; height: 100%; display: flex; flex-direction: column; justify-content: center; }
.kpi-label{ color: var(--muted); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value{ font-weight: 800; font-size: 2.2rem; line-height: 1.2; }
.rank-chip{ display:inline-flex; align-items:center; justify-content:center; width:28px; height:28px; border-radius:50%; font-weight:700; font-size:0.9rem; margin-right:8px; }
.rank-1{ background:var(--k1); color:#fbbf24; border:1px solid #78350f; }
.rank-2{ background:var(--k2); color:#60a5fa; border:1px solid #1e3a8a; }
.rank-3{ background:var(--k3); color:#fb923c; border:1px solid #7c2d12; }
.rank-4,.rank-5{ background:var(--k45); color:#cbd5e1; border:1px solid #475569; }
.badge-pass{ background:var(--pass-bg); color:var(--pass-text); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; }
.badge-fail{ background:var(--fail-bg); color:var(--fail-text); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700; }
"""

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

def kpi_card(title, value, id_val, icon, color, bg_color):
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                # Icon Box
                html.Div(
                    html.I(className=f"bi {icon}", style={"color": color, "fontSize": "1.4rem"}),
                    className="d-flex align-items-center justify-content-center",
                    style={
                        "minWidth": "44px", "width": "44px", "height": "44px", 
                        "borderRadius": "10px", "backgroundColor": bg_color
                    }
                ),
                # Text Content
                html.Div([
                    html.H6(title, className="text-muted text-uppercase fw-bold mb-0 text-truncate", style={"fontSize": "0.7rem", "letterSpacing": "0.5px", "maxWidth": "100px"}),
                    html.H3(children=value, id=id_val, className="fw-bold mb-0", style={"color": color, "fontSize": "1.6rem"})
                ], className="ms-2")
            ], className="d-flex align-items-center h-100")
        ], className="p-2"),
        className="kpi-card shadow-sm h-100 border-0 overflow-hidden",
        style={"borderLeft": f"4px solid {color} !important", "transition": "transform 0.2s ease-in-out"}
    )

# ---------- LAYOUT ----------

layout = dbc.Container([
    # Add Bootstrap Icons stylesheet
    html.Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"),
    dcc.Markdown(f"<style>{PAGE_CSS_LIGHT}</style>", dangerously_allow_html=True),
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
                dbc.CardHeader([
                    html.Span("1. Data Intake", className="fw-bold"),
                    dbc.Button("View Sample", id="btn-sample-format", color="link", size="sm", className="float-end p-0 text-decoration-none")
                ], className="bg-light d-flex justify-content-between align-items-center"),
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
                        html.Div([
                            html.Label("Upload per Section", className="small fw-bold mb-1"),
                            dbc.Button("View Format", id="open-section-format", size="sm", color="link", className="text-decoration-none p-0 small")
                        ], className="d-flex justify-content-between align-items-center"),

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
                dbc.Col(kpi_card("Total", "0", "total-students", "bi-people-fill", "#3b82f6", "#eff6ff"), className="d-flex"),
                dbc.Col(kpi_card("Appeared", "0", "present-students", "bi-person-circle", "#10b981", "#ecfdf5"), className="d-flex"),
                dbc.Col(kpi_card("Passed", "0", "passed-students", "bi-check-circle-fill", "#0ea5e9", "#f0f9ff"), className="d-flex"),
                dbc.Col(kpi_card("Failed", "0", "failed-students", "bi-x-circle-fill", "#ef4444", "#fef2f2"), className="d-flex"),
                dbc.Col(kpi_card("Absent", "0", "absent-students", "bi-person-x-fill", "#f59e0b", "#fffbeb"), className="d-flex"),
                dbc.Col(kpi_card("Pass %", "0%", "result-percent", "bi-percent", "#8b5cf6", "#f5f3ff"), className="d-flex"),
            ], className="row-cols-2 row-cols-md-3 row-cols-lg-6 g-2 mb-4"),

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
                html.H6("📥 1. Data Extraction", className="text-primary fw-bold"),
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

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("📅 Sample Excel Format")),
        dbc.ModalBody([
            html.P("Your uploaded Excel file must follow this structure:", className="text-muted small"),
            dbc.Table([
                html.Thead([
                    html.Tr([
                        html.Th("University Seat Number"), html.Th("Name"), 
                        html.Th("BAIL504", colSpan=4, className="text-center border-start border-dark"), 
                        html.Th("BCS501", colSpan=4, className="text-center border-start border-dark")
                    ]),
                    html.Tr([
                        html.Th(""), html.Th(""), 
                        html.Th("Internal", className="border-start border-dark"), html.Th("External"), html.Th("Total"), html.Th("Result"),
                        html.Th("Internal", className="border-start border-dark"), html.Th("External"), html.Th("Total"), html.Th("Result")
                    ], className="small text-muted")
                ]),
                html.Tbody([
                    html.Tr([
                        html.Td("1XX23CSXXX"), html.Td("Bob"), 
                        html.Td("46", className="border-start border-dark"), html.Td("49"), html.Td("95"), html.Td("P", className="text-success fw-bold"),
                        html.Td("44", className="border-start border-dark"), html.Td("37"), html.Td("81"), html.Td("P", className="text-success fw-bold")
                    ]),
                    html.Tr([
                        html.Td("1XX23CSXXX"), html.Td("Alice"), 
                        html.Td("47", className="border-start border-dark"), html.Td("49"), html.Td("96"), html.Td("P", className="text-success fw-bold"),
                        html.Td("37", className="border-start border-dark"), html.Td("20"), html.Td("57"), html.Td("P", className="text-success fw-bold")
                    ]),
                ])
            ], bordered=True, responsive=True, className="mb-0")
        ]),
    ], id="modal-sample-format", size="lg", is_open=False),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("📅 Sample Section File Format")),
        dbc.ModalBody([
            html.P("For each section, upload a file containing a list of USNs belonging to that section.", className="text-muted small"),
            html.P("The file should have a column header named 'USN' or 'Student ID'.", className="fw-bold small"),
            dbc.Table([
                html.Thead(html.Tr(html.Th("USN"))),
                html.Tbody([
                    html.Tr(html.Td("1XX20CS001")),
                    html.Tr(html.Td("1XX20CS005")),
                    html.Tr(html.Td("1XX20CS012")),
                    html.Tr(html.Td("...")),
                ])
            ], bordered=True, striped=True, className="mb-0", style={"maxWidth": "200px"})
        ]),
    ], id="modal-section-format", size="sm", is_open=False),

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
    Output("modal-sample-format", "is_open"),
    [Input("btn-sample-format", "n_clicks")],
    [State("modal-sample-format", "is_open")],
    prevent_initial_call=True
)
def toggle_sample_format(n, is_open):
    return not is_open if n else is_open

@callback(
    Output("modal-section-format", "is_open"),
    [Input("open-section-format", "n_clicks")],
    [State("modal-section-format", "is_open")],
    prevent_initial_call=True
)
def toggle_section_format(n, is_open):
    return not is_open if n else is_open

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
    duplicates = []
    
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
                 # Check for conflicts
                 for usn, section in file_mapping.items():
                     if usn in mapping and mapping[usn] != section:
                         duplicates.append(f"{usn} (in {mapping[usn]} & {section})")
                 
                 mapping.update(file_mapping)
    
    total_entries = len(mapping)
    status_msg = f"✅ Total {total_entries} USNs mapped"
    
    if duplicates:
        count = len(duplicates)
        examples = ", ".join(duplicates[:2])
        status_msg = f"⚠️ {count} Duplicates found: {examples}..."
    
    if total_entries > 0:
        return mapping, status_msg
    
    return no_update, "ℹ️ No valid USNs found in uploaded files"

@callback(
    [Output('total-students', 'children'),
     Output('present-students', 'children'),
     Output('passed-students', 'children'),
     Output('failed-students', 'children'),
     Output('absent-students', 'children'),
     Output('result-percent', 'children'),
     Output('data-preview', 'children')],
    [Input('stored-data', 'data'),
     Input('subject-selector', 'value'),
     Input('section-data', 'data'),
     Input('usn-mapping-store', 'data')]
)
def update_dashboard(data, selected_subjects, section_ranges, usn_mapping):
    if not data or not selected_subjects:
        return "0", "0", "0", "0", "0", "0%", html.Div("Upload data and select subjects to view analytics.", className="p-4 text-center text-muted")
    
    df = pd.read_json(data, orient='split')
    meta_col = df.columns[0]
    
    # 1. Filter relevant columns
    all_subject_codes = get_subject_codes(df)
    
    # Start with just info columns
    info_cols = [c for c in df.columns if not any(s in c for s in all_subject_codes)]
    df_filtered = df[info_cols].copy()
    
    # Add relevant subject columns
    subject_data_cols = [c for c in df.columns if any(c.startswith(s) for s in selected_subjects)]
    df_filtered = pd.concat([df_filtered, df[subject_data_cols]], axis=1)

    # 2. Convert Mark columns to Numeric
    for c in subject_data_cols:
        if any(k in c for k in ['Internal', 'External', 'Total']):
            df_filtered[c] = pd.to_numeric(df_filtered[c], errors='coerce').fillna(0)

    # 3. Robust Pass Logic (Matching Ranking Page Logic)
    res_cols = [c for c in subject_data_cols if "Result" in c]
    
    if res_cols:
        def calc_overall(row):
            subject_status = []
            for res_col in res_cols:
                # Identify components for this subject
                # Assumption: Column name format is like "SUBCODE Result"
                # And components are "SUBCODE Internal", "SUBCODE External"
                base_name = res_col.rsplit(' Result', 1)[0].rsplit('Result', 1)[0].strip()
                
                # Try specific suffixes first as seen in ranking.py
                i_col = f"{base_name} Internal"
                e_col = f"{base_name} External"
                
                # If not found, try to look for columns that start with base_name
                if i_col not in df_filtered.columns:
                     # Fallback logic if needed, but strict naming is preferred
                     pass

                i_val = row.get(i_col, 0)
                e_val = row.get(e_col, 0)
                
                try: i = float(i_val)
                except: i = 0
                try: e = float(e_val) 
                except: e = 0
                
                r = str(row.get(res_col, "")).strip().upper()

                # 🔥 ABSENT RULE (Enhanced)
                # If External is 0 and Result is Absent OR Empty -> Treat as Absent for that subject
                if (e == 0) and (r in ['A', 'ABSENT', '']):
                    subject_status.append('A')
                elif r in ['F', 'FAIL']:
                    subject_status.append('F')
                else:
                    # If Result is missing but Marks exist, check for pass/fail by marks
                    total_s = i + e
                    if r == '' and total_s < 35: # Assuming 35 is fail threshold
                         subject_status.append('F')
                    else:
                         subject_status.append('P')

            absent_count = subject_status.count('A')
            fail_count = subject_status.count('F')

            # === OVERALL LOGIC ===
            if not subject_status: res = 'P' # No subjects selected? Treat as Pass/Neutral
            elif absent_count == len(subject_status): res = 'A' # All selected subjects absent
            elif fail_count > 0 or absent_count > 0: res = 'F' # Any fail or any absent (if not all absent) -> Fail (as per ranking logic implication, actually ranking says: elif fail_count > 0 or absent_count > 0: res = 'F')
            # Wait, ranking logic:
            # elif fail_count > 0 or absent_count > 0: res = 'F'
            # else: res = 'P'
            # means if you are absent in 1 subject, you fail the overall check for the selected group.
            else: res = 'P'
            
            return res

        df_filtered['Overall_Result'] = df_filtered.apply(calc_overall, axis=1)
    else:
        df_filtered['Overall_Result'] = 'P'

    # 4. Metrics calculation
    total = len(df_filtered)
    
    passed_count = (df_filtered['Overall_Result'] == 'P').sum()
    absent_count = (df_filtered['Overall_Result'] == 'A').sum()
    failed_count = (df_filtered['Overall_Result'] == 'F').sum()
    
    # Present is Total - Absent (Absent means absent in ALL selected subjects)
    present_count = total - absent_count
    
    # Pass Percentage (Pass Rate) here:
    # Use Present count as denominator instead of Total
    passed_rate_val = (passed_count / present_count) * 100 if present_count > 0 else 0
    rate = f"{round(passed_rate_val, 2)}%"

    # 5. Section Assignment
    if section_ranges or usn_mapping:
        df_filtered['Section'] = df_filtered[meta_col].apply(lambda x: assign_section(x, section_ranges, usn_mapping))

    # 6. USN Validation (Check for Mismatched USNs)
    alert_msg = None
    if usn_mapping:
        result_usns = set(df_filtered[meta_col].astype(str).str.strip().str.upper())
        mapping_usns = set(k.strip().upper() for k in usn_mapping.keys())
        missing_usns = mapping_usns - result_usns
        
        if missing_usns:
            count = len(missing_usns)
            sorted_missing = sorted(list(missing_usns))
            
            if count <= 5:
                # Show all if few
                display_content = html.Div(f"Missing: {', '.join(sorted_missing)}", className="small mt-1")
            else:
                # Show summary + expander for many
                display_content = html.Div([
                    html.Div(f"Missing first 5: {', '.join(sorted_missing[:5])}...", className="small mt-1"),
                    html.Details([
                        html.Summary(f"Click to see all {count} missing USNs", style={"cursor": "pointer"}, className="small fw-bold text-muted mt-1"),
                        html.Div(
                            ", ".join(sorted_missing), 
                            className="small p-2 bg-light text-dark border rounded mt-1 text-break", 
                            style={"maxHeight": "150px", "overflowY": "auto"}
                        )
                    ])
                ])

            alert_msg = dbc.Alert(
                [
                    html.Div([
                        html.I(className="bi bi-exclamation-triangle-fill me-2"),
                        html.Strong(f"Warning: {count} USN(s) in Section Mapping NOT found in Result Data."),
                    ]),
                    display_content,
                    html.Div("These students will simply be ignored assigned to 'Unassigned'.", className="small text-muted mt-1")
                ],
                color="warning",
                className="mb-3 border-warning"
            )

    # 7. Generate Table UI
    table = dbc.Table.from_dataframe(
        df_filtered.head(10), 
        striped=True, borderless=True, hover=True, responsive=True, 
        className="mb-0 align-middle",
        style={"fontSize": "0.85rem"}
    )
    
    final_output = html.Div([alert_msg, table]) if alert_msg else table

    return str(total), str(present_count), str(passed_count), str(failed_count), str(absent_count), rate, final_output