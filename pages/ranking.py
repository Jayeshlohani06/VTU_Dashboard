import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import re
from functools import lru_cache
import ast
from io import StringIO 

# Register page
dash.register_page(__name__, path="/ranking", name="Ranking")

# ==================== Helpers ====================

def extract_numeric(roll):
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges):
    roll_num = extract_numeric(roll_no)
    if section_ranges:
        for sec_name, (start, end) in section_ranges.items():
            start_num = extract_numeric(start)
            end_num = extract_numeric(end)
            if start_num <= roll_num <= end_num:
                return sec_name
    return "Unassigned"

def get_grade_point(percentage_score):
    score = pd.to_numeric(percentage_score, errors='coerce')
    if pd.isna(score): return 0
    score = float(score)
    if 90 <= score <= 100: return 10
    elif 80 <= score < 90: return 9
    elif 70 <= score < 80: return 8
    elif 60 <= score < 70: return 7
    elif 55 <= score < 60: return 6
    elif 50 <= score < 55: return 5
    else: return 0

def _normalize_df(df, section_ranges):
    if df.columns[0] != 'Student_ID':
        df = df.rename(columns={df.columns[0]: 'Student_ID'})
    df['Section'] = df['Student_ID'].apply(lambda x: assign_section(str(x), section_ranges))
    total_cols = [c for c in df.columns if any(k in c.lower() for k in ['total', 'marks', 'score'])]
    total_cols = [c for c in total_cols if c != 'Total_Marks']
    if total_cols:
        df[total_cols] = df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        df['Total_Marks'] = df[total_cols].sum(axis=1)
    else:
        df['Total_Marks'] = 0
    result_cols = [c for c in df.columns if 'result' in c.lower()]
    if result_cols:
        df['Overall_Result'] = df[result_cols].apply(lambda row: 'P' if all(str(v).strip().upper() == 'P' for v in row if pd.notna(v)) else 'F', axis=1)
    else:
        pass_mark = 18
        if total_cols:
            df['Overall_Result'] = df.apply(lambda row: 'F' if any(row[c] < pass_mark for c in total_cols) else 'P', axis=1)
        else:
            df['Overall_Result'] = 'P'
    if 'Name' not in df.columns: df['Name'] = ""
    return df

@lru_cache(maxsize=32)
def _prepare_base(json_str, section_key):
    df = pd.read_json(StringIO(json_str), orient='split')
    section_ranges = None
    if section_key not in (None, "None"):
        try: section_ranges = ast.literal_eval(section_key)
        except: section_ranges = None
    df = _normalize_df(df, section_ranges)
    return df

def _section_key(section_ranges):
    try: return repr(section_ranges)
    except: return "None"


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
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td{ border-color: #334155 !important; background-color: #1e293b !important; color: #f8fafc !important; }
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th{ border-color: #475569 !important; background-color: #0f172a !important; color: #f8fafc !important; }
.accordion-button:not(.collapsed){ background-color: #172554; color: #60a5fa; }
.accordion-button{ color: #f8fafc; background-color: #1e293b; border-color: #334155; }
.table { margin-bottom: 0; color: #f8fafc; }
.table tbody tr { border-bottom-color: #334155; }
.table tbody tr:hover { background-color: #334155 !important; }
.table thead { border-top-color: #475569; background-color: #0f172a; }
.table thead th { color: #f8fafc; }
"""

def themed_style_block(theme: str):
    css = PAGE_CSS_DARK if theme == "dark" else PAGE_CSS_LIGHT
    return dcc.Markdown(f"<style>{css}</style>", dangerously_allow_html=True)


# ==================== Layout ====================

layout = dbc.Container([
    html.Div(id="theme-style"),
    html.Link(rel="stylesheet", href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"),

    # Header
    html.Div([
        html.H3(["🏆 Class & Section Ranking"], className="rnk-title text-center fw-bold mb-2"),
        html.P("Analyze performance with precision. Toggle between Marks and SGPA modes.", className="text-center text-muted mb-0")
    ], className="rnk-wrap mb-4 rnk-card p-4"),

    # Controls
    html.Div(
        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Dropdown(
                    id="filter-dropdown",
                    options=[{"label": "All Students", "value": "ALL"}, {"label": "Passed Students", "value": "PASS"}, {"label": "Failed Students", "value": "FAIL"}],
                    value="ALL", clearable=False, className="shadow-sm"
                ), md=3, xs=12),
                dbc.Col(dcc.Dropdown(
                    id="section-dropdown",
                    options=[{"label": "All Sections", "value": "ALL"}],
                    value="ALL", clearable=False, className="shadow-sm"
                ), md=3, xs=12),
                dbc.Col(dbc.InputGroup([
                    dbc.InputGroupText(html.I(className="bi bi-search")),
                    dbc.Input(id="search-input", placeholder="Search ID / Name...", type="text")
                ], className="shadow-sm"), md=4, xs=12),
                dbc.Col(dbc.ButtonGroup([
                    dbc.Button("Reset", id="reset-btn", color="secondary", outline=True),
                    dbc.Button("CSV", id="export-csv", color="primary", outline=True),
                    dbc.Button("Excel", id="export-xlsx", color="success", outline=True),
                ], className="w-100 d-flex justify-content-end"), md=2, xs=12),
            ], className="g-2 rnk-controls mb-3"),

            dbc.Row([
                dbc.Col(dbc.Checklist(
                    id="theme-toggle", options=[{"label": "🌙 Dark Mode", "value": "dark"}], value=[], switch=True,
                ), width="auto", className="d-flex align-items-center"),
                dbc.Col(dcc.RadioItems(
                    id='ranking-type',
                    options=[{'label': 'Marks Based', 'value': 'marks'}, {'label': 'SGPA Based', 'value': 'sgpa'}],
                    value='marks', inline=True, labelClassName='px-3 py-1 border rounded-pill me-2 cursor-pointer', inputClassName="me-2"
                ), className='text-end')
            ])
        ]), className="rnk-card"), className="rnk-controls-wrap mb-4"
    ),

    # SGPA Panel
    html.Div(id='sgpa-credit-panel'),

    # KPIs (Cards)
    html.Div(dbc.Spinner(html.Div(id='kpi-cards'), color="primary"), className="mb-4"),

    # VTU Category Breakdown Table
    dbc.Card(dbc.CardBody([
        html.H6([html.I(className="bi bi-bar-chart me-2 text-success"), "VTU Category Breakdown"], className="fw-bold mb-3"),
        dcc.Loading(
            type="circle",
            children=html.Div(id='category-breakdown-container')
        )
    ]), className="rnk-card mb-4"),

    # Overview (Explicitly Ordered: Top 5 -> Section -> Bottom 5)
    dbc.Row([
        # Top 5 Overall (Left)
        dbc.Col(dbc.Card(dbc.CardBody(html.Div([
            html.Div([html.H6("🥇 Top 5 Overall", className="fw-bold mb-3 me-auto text-dark")], className="d-flex"),
            html.Div(id="overall-top5")
        ])), className="rnk-card h-100"), md=4, xs=12),
        
        # Section-wise Toppers (Middle)
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([html.H6("🏆 Section-wise Toppers", className="fw-bold mb-3 me-auto text-dark")], className="d-flex"),
            html.Div(id="section-toppers")
        ]), className="rnk-card h-100"), md=4, xs=12),
        
        # Bottom 5 (Right)
        dbc.Col(dbc.Card(dbc.CardBody(html.Div([
            html.Div([html.H6("⬇️ Bottom 5 (by Score)", className="fw-bold mb-3 me-auto text-dark")], className="d-flex"),
            html.Div(id="bottom-five")
        ])), className="rnk-card h-100"), md=4, xs=12),
    ], className="g-4 mb-4"),

    # Table
    dbc.Card(dbc.CardBody([
        html.H6([html.I(className="bi bi-table me-2 text-primary"), "Detailed Ranking Table"], className="fw-bold mb-3"),
        dcc.Loading(
            type="circle",
            children=dash_table.DataTable(
                id='ranking-table',
                columns=[], data=[],
                page_size=25, sort_action='native', filter_action='none',
                style_table={'height': '620px', 'overflowY': 'auto'}, fixed_rows={'headers': True},
                style_cell={'textAlign': 'center', 'fontFamily': 'Inter, sans-serif', 'fontSize': 13, 'padding': '12px', 'minWidth': '80px'},
                style_header={'backgroundColor': '#1f2937', 'color': 'white', 'fontWeight': '700', 'padding': '12px', 'border': '0'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgba(0,0,0,0.02)'},
                    # Fail Styles (Check both Marks 'F' and SGPA 'Fail')
                    {'if': {'filter_query': '{Overall_Result} = "F"'}, 'backgroundColor': '#fff1f2', 'color': '#991b1b'},
                    {'if': {'filter_query': '{Result_Selected} = "Fail"'}, 'backgroundColor': '#fff1f2', 'color': '#991b1b'},
                    
                    # Top Ranks (Marks)
                    {'if': {'filter_query': '{Class_Rank} = 1'}, 'backgroundColor': '#fffbeb', 'color': '#92400e', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{Class_Rank} = 2'}, 'backgroundColor': '#f0f9ff', 'color': '#075985', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{Class_Rank} = 3'}, 'backgroundColor': '#fff7ed', 'color': '#9a3412', 'fontWeight': 'bold'},
                    
                    # Top Ranks (SGPA)
                    {'if': {'filter_query': '{SGPA_Class_Rank} = 1'}, 'backgroundColor': '#fffbeb', 'color': '#92400e', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{SGPA_Class_Rank} = 2'}, 'backgroundColor': '#f0f9ff', 'color': '#075985', 'fontWeight': 'bold'},
                    {'if': {'filter_query': '{SGPA_Class_Rank} = 3'}, 'backgroundColor': '#fff7ed', 'color': '#9a3412', 'fontWeight': 'bold'},
                ],
                row_selectable=False, cell_selectable=True, style_as_list_view=True
            )
        )
    ]), className="rnk-card"),

    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Student Profile")),
        dbc.ModalBody(id="student-modal-body"),
        dbc.ModalFooter(dbc.Button("Close", id="close-modal", className="ms-auto", color="secondary"))
    ], id="student-modal", is_open=False, size="lg"),

    dcc.Download(id="download-csv"),
    dcc.Download(id="download-xlsx"),
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session'),
    dcc.Store(id='sgpa-store', storage_type='session'),
], fluid=True, className="pb-5")


# ==================== Callbacks ====================

@callback(Output("theme-style", "children"), Input("theme-toggle", "value"))
def apply_theme(v): return themed_style_block("dark" if "dark" in (v or []) else "light")

@callback(Output('section-dropdown', 'options'), Input('stored-data', 'data'), State('section-data', 'data'))
def update_section_options(json_data, section_ranges):
    if not json_data: return [{"label": "All Sections", "value": "ALL"}]
    df = pd.read_json(StringIO(json_data), orient='split') 
    df = _normalize_df(df, section_ranges)
    sections = sorted(df['Section'].dropna().unique())
    return [{"label": "All Sections", "value": "ALL"}] + [{"label": s, "value": s} for s in sections]

@callback([Output('filter-dropdown', 'value'), Output('section-dropdown', 'value'), Output('search-input', 'value')], Input('reset-btn', 'n_clicks'), prevent_initial_call=True)
def reset_filters(n): return "ALL", "ALL", ""

# ========== Grid UI for SGPA Panel ==========
@callback(
    Output('sgpa-credit-panel', 'children'),
    Input('stored-data', 'data'),
    Input('ranking-type', 'value'),
    State('section-data', 'data')
)
def generate_credit_panel(json_data, ranking_type, section_ranges):
    if ranking_type != 'sgpa': return html.Div()
    if not json_data: return ""
    
    df = pd.read_json(StringIO(json_data), orient='split')
    codes = set()
    for col in df.columns:
        m = re.match(r'^(.*?)\s+(Internal|External|Total)$', col, flags=re.IGNORECASE)
        if m: codes.add(m.group(1).strip())

    if not codes: return dbc.Alert("No recognizable subject columns found.", color='info')
    codes = sorted(codes)
    
    grid_items = []
    for code in codes:
        grid_items.append(dbc.Col(dbc.InputGroup([
            dbc.InputGroupText(code, className="fw-bold bg-light text-dark", style={"width": "85px", "justifyContent": "center", "fontSize": "0.8rem"}),
            dbc.Select(id={'type': 'credit-input', 'index': code}, options=[{'label': f'{i} Credits', 'value': str(i)} for i in [4,3,2,1,0]], value='3', className="form-select text-center")
        ], size="sm", className="shadow-sm mb-3"), xs=12, sm=6, md=4, lg=3))

    return dbc.Card([
        dbc.CardHeader(html.Div([html.I(className="bi bi-sliders me-2"), "SGPA Configuration"], className="fw-bold text-primary"), className="bg-white border-bottom-0 pt-3"),
        dbc.CardBody([
            html.P("Assign credits to subjects. The system will calculate SGPA based on these values.", className="text-muted small mb-4"),
            dbc.Row(grid_items, className="g-2 mb-2"),
            html.Hr(className="my-3 text-muted opacity-25"),
            dbc.Button([html.I(className="bi bi-calculator-fill me-2"), "Calculate SGPA"], id='calculate-sgpa-all', color='primary', size="lg", className='w-100 fw-bold shadow-sm mb-3'),
            # Status Container (starts empty)
            html.Div(id="sgpa-calc-status")
        ])
    ], className="rnk-card mb-4 border-start border-4 border-primary")

# ========== SGPA Calculation (FIXED PASS/FAIL LOGIC) ==========
@callback(
    Output('sgpa-store', 'data'),
    Output('sgpa-calc-status', 'children'),
    Input('calculate-sgpa-all', 'n_clicks'),
    State('stored-data', 'data'),
    State('section-data', 'data'),
    State({'type': 'credit-input', 'index': ALL}, 'id'),
    State({'type': 'credit-input', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def calculate_sgpa_all(n_clicks, json_data, section_ranges, credit_ids, credit_vals):
    if not n_clicks: return no_update, no_update
    if not json_data: return no_update, no_update
    base = _prepare_base(json_data, _section_key(section_ranges)).copy()
    credit_dict = {}
    for cid, val in zip(credit_ids, credit_vals):
        if val is not None:
            try: credit_dict[cid['index']] = int(val)
            except ValueError: credit_dict[cid['index']] = 0

    credit_dict_positive = {k: v for k, v in credit_dict.items() if v > 0}
    if not credit_dict_positive:
        return no_update, dbc.Alert("Please assign at least one credit > 0", color="warning", dismissable=True)

    sgpa_rows = []
    for _, row in base.iterrows():
        total_cp, total_cre, total_marks, fail_flag = 0, 0, 0, False
        for code, credit in credit_dict_positive.items():
            # 1. Get raw scores
            i = pd.to_numeric(row.get(f"{code} Internal"), errors='coerce') or 0
            e = pd.to_numeric(row.get(f"{code} External"), errors='coerce') or 0
            
            # 2. Get Total Score
            if f"{code} Total" in base.columns:
                score = pd.to_numeric(row.get(f"{code} Total"), errors='coerce') or 0
            else:
                score = (i + e) if (i and e) else (i or e or 0)
            
            # 3. --- REVISED FAIL LOGIC ---
            # Fail if both Internal and External < 18 (Strict rule)
            # BUT: If External is 0 (missing/absent/no exam), check Result Column override
            if (i < 18) or (e < 18):
                # Check for Result column override (e.g. 18CS51 Result)
                # If Result is 'P', ignore the low mark (trust the result)
                res_val = str(row.get(f"{code} Result", "")).strip().upper()
                if res_val != 'P':
                    fail_flag = True
            # -----------------------------

            total_cp += get_grade_point(score) * credit
            total_cre += credit
            total_marks += score
            
        sgpa = (total_cp / total_cre) if total_cre > 0 else 0.0
        res = 'Pass' if (not fail_flag and total_cre > 0) else 'Fail'
        sgpa_rows.append({'Student_ID': row['Student_ID'], 'SGPA': round(sgpa, 2), 'Total_Marks_Selected': round(total_marks, 2), 'Result_Selected': res})

    sgpa_df = pd.DataFrame(sgpa_rows)
    sgpa_df['SGPA_Class_Rank'] = sgpa_df[sgpa_df['Result_Selected'] == 'Pass']['SGPA'].rank(method='min', ascending=False).astype('Int64')
    section_map = base.set_index('Student_ID')['Section'].to_dict()
    sgpa_df['Section'] = sgpa_df['Student_ID'].map(section_map)
    sgpa_df['SGPA_Section_Rank'] = sgpa_df.groupby('Section')['SGPA'].rank(method='min', ascending=False).astype('Int64')

    msg = dbc.Alert([html.I(className="bi bi-check-circle-fill me-2"), "Calculation Successful! Dashboard Updated."], color="success", dismissable=True, is_open=True, fade=True)
    return sgpa_df.to_json(orient='split'), msg

# ========== Main View Builder (Dynamic KPIs + Fixed Layout Order) ==========
@callback(
    Output('kpi-cards', 'children'),
    Output('overall-top5', 'children'),
    Output('section-toppers', 'children'),
    Output('bottom-five', 'children'),
    Output('ranking-table', 'columns'),
    Output('ranking-table', 'data'),
    Output('category-breakdown-container', 'children'),
    Input('filter-dropdown', 'value'),
    Input('section-dropdown', 'value'),
    Input('search-input', 'value'),
    Input('ranking-type', 'value'),
    Input('sgpa-store', 'data'),
    State('stored-data', 'data'),
    State('section-data', 'data')
)
def build_views(filter_val, sec_val, search_val, rank_type, sgpa_json, json_data, section_ranges):
    if not json_data: return html.P("Upload data first.", className="text-center text-muted"), html.Div(), html.Div(), html.Div(), [], [], html.Div()

    base_full = _prepare_base(json_data, _section_key(section_ranges)).copy()
    base_pre = base_full.copy()
    if sgpa_json:
        try:
            sgpa_df = pd.read_json(StringIO(sgpa_json), orient='split')
            base_full = base_full.merge(sgpa_df, how='left', on='Student_ID')
            # Fix column conflict if merge creates duplicates
            if 'Section' not in base_full.columns or base_full['Section'].isna().all():
                if 'Section' in base_pre.columns: base_full['Section'] = base_pre['Section']
        except: base_full = base_pre.copy()

    scope = base_full.copy()

    # Dynamic Filtering
    target_res_col = "Overall_Result"
    pass_val = ["P", "PASS"]
    fail_val = ["F", "FAIL"]

    if rank_type == 'sgpa' and 'Result_Selected' in scope.columns:
        target_res_col = "Result_Selected"
        pass_val = ["PASS", "Pass"]
        fail_val = ["FAIL", "Fail"]

    if filter_val == "PASS":
        if target_res_col in scope.columns:
            scope = scope[scope[target_res_col].astype(str).str.upper().isin([p.upper() for p in pass_val])]
    elif filter_val == "FAIL":
        if target_res_col in scope.columns:
            scope = scope[scope[target_res_col].astype(str).str.upper().isin([f.upper() for f in fail_val])]
    
    if sec_val != "ALL" and 'Section' in scope.columns: scope = scope[scope["Section"] == sec_val]

    if 'Total_Marks' in scope.columns:
        scope['Class_Rank'] = scope[scope['Overall_Result'] == 'P']['Total_Marks'].rank(method='min', ascending=False).astype('Int64')
    if 'Section' in scope.columns and 'Total_Marks' in scope.columns:
        scope['Section_Rank'] = scope.groupby('Section')['Total_Marks'].rank(method='min', ascending=False).astype('Int64')

    # --- KPI Logic (Dynamic Visibility) ---
    total = len(scope)
    if rank_type == 'sgpa' and 'Result_Selected' in scope.columns:
        passed = (scope['Result_Selected'] == 'Pass').sum()
    else:
        passed = (scope['Overall_Result'] == 'P').sum() if 'Overall_Result' in scope.columns else 0
        
    failed = total - passed
    pass_pct = round((passed / total) * 100, 2) if total else 0
    
    # === CALCULATE VTU STANDARD CATEGORIES ===
    # Find all subject "Total" columns to determine max marks
    subject_total_cols = [c for c in base_full.columns if c.endswith(' Total') and c != 'Total_Marks']
    num_subjects = len(subject_total_cols) if subject_total_cols else 1
    max_marks_possible = num_subjects * 100 if num_subjects > 0 else 100
    
    # Calculate percentage for each student in scope
    scope_calc = scope.copy()
    scope_calc['percentage'] = (scope_calc['Total_Marks'] / max_marks_possible * 100).round(2)
    
    # Count VTU Categories
    fcd_count = (scope_calc['percentage'] >= 70).sum()  # First Class Distinction
    fc_count = ((scope_calc['percentage'] >= 60) & (scope_calc['percentage'] < 70)).sum()  # First Class
    sc_count = ((scope_calc['percentage'] >= 50) & (scope_calc['percentage'] < 60)).sum()  # Second Class
    fail_count = (scope_calc['Overall_Result'] == 'F').sum() if 'Overall_Result' in scope_calc.columns else 0
    
    # Define Base KPIs
    kpi_objs = [
        {"id": "total", "label": "Total Students", "value": total, "color": "#2563eb", "bg": "#eff6ff"},
        {"id": "pass", "label": "Passed", "value": passed, "color": "#059669", "bg": "#ecfdf5"},
        {"id": "fail", "label": "Failed", "value": fail_count, "color": "#dc2626", "bg": "#fef2f2"},
        {"id": "rate", "label": "Pass Rate", "value": f"{pass_pct}%", "color": "#d97706", "bg": "#fffbeb"},
    ]
    
    # Add VTU Category KPIs
    vtu_kpis = [
        {"id": "fcd", "label": "First Class Distinction (≥70%)", "value": fcd_count, "color": "#8b5cf6", "bg": "#faf5ff"},
        {"id": "fc", "label": "First Class (60-70%)", "value": fc_count, "color": "#0ea5e9", "bg": "#f0f9ff"},
        {"id": "sc", "label": "Second Class (50-60%)", "value": sc_count, "color": "#f59e0b", "bg": "#fffbf0"},
    ]
    
    # Append VTU KPIs to base KPIs
    kpi_objs.extend(vtu_kpis)
    
    if rank_type == 'sgpa' and 'SGPA' in scope.columns:
        avg = round(scope['SGPA'].mean(), 2) if not scope['SGPA'].isna().all() else 0
        kpi_objs.insert(0, {"id": "avg", "label": "Avg SGPA", "value": avg, "color": "#7c3aed", "bg": "#f5f3ff"})

    # Filter KPIs based on User Selection
    if filter_val == "PASS":
        # Show: Total, Passed, Avg, and VTU categories. Hide: Failed, Rate
        visible_kpis = [k for k in kpi_objs if k["id"] in ["avg", "total", "pass", "fcd", "fc", "sc"]]
    elif filter_val == "FAIL":
        # Show: Total, Failed, Avg. Hide: Passed, Rate, VTU categories
        visible_kpis = [k for k in kpi_objs if k["id"] in ["avg", "total", "fail"]]
    else:
        # Show All
        visible_kpis = kpi_objs

    # Dynamic column width based on count
    count = len(visible_kpis)
    row_cls = f"row-cols-2 row-cols-md-{min(count, 4)} row-cols-lg-{min(count, 5)} g-3"

    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div(x["label"], className="kpi-label mb-2"),
            html.Div(str(x["value"]), className="kpi-value", style={"color": x["color"]})
        ]), className="kpi-card", style={"backgroundColor": x["bg"], "borderLeftColor": x["color"]}))
        for x in visible_kpis
    ], className=row_cls)

    def make_list(df, val_col, is_asc=False):
        if df.empty: return html.P("No Data", className="text-muted small")
        sorted_df = df.sort_values(val_col, ascending=is_asc).head(5)
        items = []
        for i, (_, r) in enumerate(sorted_df.iterrows(), 1):
            val = r.get(val_col, 0)
            
            if rank_type == 'sgpa' and 'Result_Selected' in r:
                is_pass = (r['Result_Selected'] == 'Pass')
                res_txt = r['Result_Selected']
            else:
                is_pass = (r.get('Overall_Result') == 'P')
                res_txt = r.get('Overall_Result')

            res_cls = "badge-pass" if is_pass else "badge-fail"
            
            sec_txt = f" (Sec {r.get('Section')})" if r.get('Section') else ""
            
            items.append(html.Li([
                html.Span(f"#{i}", className="fw-bold me-2 text-muted", style={"minWidth":"25px"}),
                html.Span([html.Strong(r.get('Student_ID')), html.Span(sec_txt, className="text-muted small")]),
                html.Span("—", className="mx-2 text-muted"),
                html.Span(f"{val}", className="fw-bold me-2"),
                html.Span(res_txt[0], className=res_cls) # Just P or F
            ], className="d-flex align-items-center mb-2 small"))
        return html.Ul(items, className="list-unstyled mb-0")

    sort_col = 'SGPA' if (rank_type == 'sgpa' and 'SGPA' in scope.columns) else 'Total_Marks'
    top5_html = make_list(scope, sort_col, False)
    bot_html = make_list(scope, sort_col, True)

    sec_cards = []
    if 'Section' in scope.columns:
        for sec, g in sorted(scope.groupby('Section')):
            if g.empty: continue
            ridx = g[sort_col].idxmax()
            r = g.loc[ridx]
            
            rank_col_name = 'SGPA_Class_Rank' if rank_type=='sgpa' else 'Class_Rank'
            rank_val = r.get(rank_col_name)
            if pd.notna(rank_val) and str(rank_val).replace('.', '', 1).isdigit():
                rank_display = str(int(rank_val))
            else:
                rank_display = "-"
            
            card = html.Div([
                html.H6([html.I(className="bi bi-trophy-fill me-2", style={"color":"#8b5cf6"}), f"Section {sec} Topper"], className="fw-bold mb-2", style={"color": "#4338ca", "fontSize": "0.95rem"}),
                html.Div([
                    html.Div(f"Student ID: {r.get('Student_ID')}", className="mb-1 text-muted small"),
                    html.Div([html.Span(f"{'SGPA' if rank_type=='sgpa' else 'Total'}: ", className="text-muted small"), html.Span(f"{r.get(sort_col)}", className="fw-bold text-dark")], className="mb-1"),
                    html.Div([html.Span("Class Rank: ", className="text-muted small"), html.Span(rank_display, className="fw-bold text-dark")])
                ])
            ], className="p-3 mb-3 bg-white rounded shadow-sm border-start border-4 border-primary")
            sec_cards.append(card)
            
    sec_html = html.Div(sec_cards) if sec_cards else html.P("No Data", className="text-muted small")

    tdf = scope.copy()
    if search_val:
        s = str(search_val).strip()
        mask = tdf['Student_ID'].astype(str).str.contains(s, case=False) | tdf['Name'].astype(str).str.contains(s, case=False)
        tdf = tdf[mask]
    
    if rank_type == 'sgpa' and 'SGPA' in tdf.columns:
        tdf = tdf.sort_values('SGPA', ascending=False)
        cols = ['SGPA_Class_Rank', 'SGPA_Section_Rank', 'Student_ID', 'Name', 'Section', 'SGPA', 'Total_Marks_Selected', 'Result_Selected']
    else:
        tdf['__sort'] = tdf['Class_Rank'].fillna(9999)
        tdf = tdf.sort_values(['__sort', 'Total_Marks'], ascending=[True, False])
        cols = ['Class_Rank', 'Section_Rank', 'Student_ID', 'Name', 'Section', 'Total_Marks', 'Overall_Result']
    
    tcols = [{"name": c.replace("_", " "), "id": c} for c in cols if c in tdf.columns]
    # FIX: Send only relevant columns to table data
    tdata = tdf[cols].to_dict('records') 

    # === GENERATE VTU CATEGORY BREAKDOWN TABLE ===
    breakdown_data = []
    if 'Section' in scope.columns:
        sections = sorted(scope['Section'].unique())
    else:
        sections = ["Overall"]
    
    for section in sections:
        if section == "Overall":
            section_df = scope_calc
        else:
            section_df = scope_calc[scope_calc['Section'] == section]
        
        if section_df.empty:
            continue
        
        fcd = (section_df['percentage'] >= 70).sum()
        fc = ((section_df['percentage'] >= 60) & (section_df['percentage'] < 70)).sum()
        sc = ((section_df['percentage'] >= 50) & (section_df['percentage'] < 60)).sum()
        fail = (section_df['Overall_Result'] == 'F').sum()
        total_sec = len(section_df)
        
        breakdown_data.append({
            'Section': section,
            'First Class Distinction (≥70%)': fcd,
            'First Class (60-70%)': fc,
            'Second Class (50-60%)': sc,
            'Failed': fail,
            'Total': total_sec
        })
    
    # Add overall row
    if breakdown_data:
        overall_row = {
            'Section': 'Overall',
            'First Class Distinction (≥70%)': sum(row['First Class Distinction (≥70%)'] for row in breakdown_data),
            'First Class (60-70%)': sum(row['First Class (60-70%)'] for row in breakdown_data),
            'Second Class (50-60%)': sum(row['Second Class (50-60%)'] for row in breakdown_data),
            'Failed': sum(row['Failed'] for row in breakdown_data),
            'Total': sum(row['Total'] for row in breakdown_data)
        }
        breakdown_data.append(overall_row)
    
    # Create accordion items for each section
    accordion_items = []
    for bd_row in breakdown_data:
        section_name = bd_row['Section']
        if section_name == "Overall":
            section_df = scope_calc
        else:
            section_df = scope_calc[scope_calc['Section'] == section_name]
        
        # Create category breakdown rows
        category_items = []
        categories = [
            ('FCD (≥70%)', 'success', section_df[section_df['percentage'] >= 70]),
            ('First Class (60-70%)', 'info', section_df[(section_df['percentage'] >= 60) & (section_df['percentage'] < 70)]),
            ('Second Class (50-60%)', 'warning', section_df[(section_df['percentage'] >= 50) & (section_df['percentage'] < 60)]),
            ('Failed', 'danger', section_df[section_df['Overall_Result'] == 'F'])
        ]
        
        for cat_name, cat_color, cat_df in categories:
            if len(cat_df) > 0:
                # Create student list for this category
                student_items = []
                for _, student in cat_df.iterrows():
                    student_items.append(
                        html.Tr([
                            html.Td(student.get('Student_ID'), className="fw-bold"),
                            html.Td(student.get('Name')),
                            html.Td(f"{student.get('Total_Marks', 0)}", className="fw-bold"),
                            html.Td(f"{student.get('percentage', 0):.2f}%", className="fw-bold")
                        ])
                    )
                
                student_table = html.Table(
                    [
                        html.Thead(html.Tr([
                            html.Th("Student ID", className="fw-bold"),
                            html.Th("Name"),
                            html.Th("Marks"),
                            html.Th("Percentage")
                        ], style={'backgroundColor': '#e9ecef', 'borderBottom': '2px solid #dee2e6'})),
                        html.Tbody(student_items)
                    ],
                    className="table table-hover mb-0",
                    style={'fontSize': '0.9rem', 'marginBottom': '1rem'}
                )
                
                category_items.append(
                    dbc.AccordionItem([
                        student_table
                    ], title=f"📊 {cat_name} ({len(cat_df)} students)", className="mb-2")
                )
        
        # Main accordion item for section
        section_title = f"Section {section_name} - Total: {bd_row['Total']} | First Class Distinction: {bd_row['First Class Distinction (≥70%)']}" if section_name != "Overall" else f"📈 Overall Summary - Total: {bd_row['Total']}"
        
        accordion_items.append(
            dbc.AccordionItem(
                dbc.Accordion(category_items, always_open=True),
                title=section_title,
                className="mb-2"
            )
        )
    
    # Create main accordion
    breakdown_container = dbc.Accordion(accordion_items, always_open=False) if accordion_items else html.P("No data available", className="text-muted")

    return kpi_cards, top5_html, sec_html, bot_html, tcols, tdata, breakdown_container

@callback(Output("student-modal", "is_open"), Output("student-modal-body", "children"), Input("ranking-table", "active_cell"), State("ranking-table", "derived_viewport_data"), Input("close-modal", "n_clicks"), prevent_initial_call=True)
def show_modal(cell, data, close):
    if dash.ctx.triggered_id == "close-modal": return False, no_update
    if not cell or not data: return no_update, no_update
    r = data[cell['row']]
    body = dbc.Row([
        dbc.Col([html.H6("Identity", className="text-primary"), html.Div(f"ID: {r.get('Student_ID')}"), html.Div(f"Name: {r.get('Name')}")], md=6),
        dbc.Col([html.H6("Stats", className="text-primary"), html.Div(f"Marks: {r.get('Total_Marks')}"), html.Div(f"SGPA: {r.get('SGPA', '-')}")], md=6)
    ])
    return True, body

@callback(Output("download-csv", "data"), Input("export-csv", "n_clicks"), State('ranking-table', 'data'), prevent_initial_call=True)
def exp_csv(n, d): return dcc.send_data_frame(pd.DataFrame(d).to_csv, "rank.csv", index=False) if d else no_update

@callback(Output("download-xlsx", "data"), Input("export-xlsx", "n_clicks"), State('ranking-table', 'data'), prevent_initial_call=True)
def exp_xlsx(n, d): return dcc.send_data_frame(pd.DataFrame(d).to_excel, "rank.xlsx", index=False) if d else no_update