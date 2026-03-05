import dash
from dash import html, dcc, Input, Output, State, callback, ALL, MATCH, dash_table, no_update
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import utils.master_store as ms

dash.register_page(__name__, path="/branch-analysis", name="Branch Analysis")

# ==================== HELPERS ====================

def process_uploaded_excel(contents):
    """Parses raw Excel content into a clean DataFrame with robust error handling."""
    try:
        if not contents:
            return pd.DataFrame()

        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Determine header depth safely
        try:
            df_preview = pd.read_excel(io.BytesIO(decoded), header=None, nrows=10)
        except Exception as e:
            print(f"Error reading Excel preview: {e}")
            return pd.DataFrame()

        header_row_count = 2 # Default
        for i, row in df_preview.iterrows():
            row_str = row.astype(str).str.lower().tolist()
            if any("internal" in x for x in row_str) and any("external" in x for x in row_str):
                header_row_count = i + 1
                break
        
        header_indices = list(range(header_row_count))
        df_raw = pd.read_excel(io.BytesIO(decoded), header=header_indices)

        fixed_cols = []
        last_valid_code = None
        
        cols = df_raw.columns
        for col_tuple in cols:
            # Map column tuples based on dynamic depth
            if header_row_count == 3:
                h1 = str(col_tuple[0]).strip() # Code
                h2 = str(col_tuple[1]).strip() # Name
                h3 = str(col_tuple[2]).strip() # Component
                
                # Check empty
                is_empty = lambda h: str(h).lower() == "nan" or str(h).startswith("unnamed:")
                
                if not is_empty(h1):
                    last_valid_code = h1
                elif last_valid_code:
                    h1 = last_valid_code
                
                if is_empty(h3):
                     # Likely identity column
                     val = h1 if not is_empty(h1) else h2
                     fixed_cols.append("Name" if "name" in val.lower() else val)
                else:
                     # Include Name (h2) if available to match Overview logic
                     if not is_empty(h2) and h2.lower() not in ["internal", "external", "total", "result"]:
                         fixed_cols.append(f"{h1} - {h2} {h3}") # Code - Name Component
                     else:
                         fixed_cols.append(f"{h1} {h3}")
            else:
                # 2-Row fallback (Code -> Component)
                h1 = str(col_tuple[0]).strip()
                h2 = str(col_tuple[1]).strip()
                is_empty = lambda h: str(h).lower() == "nan" or str(h).startswith("unnamed:")

                if not is_empty(h1):
                    last_valid_code = h1
                elif last_valid_code:
                    h1 = last_valid_code
                
                if is_empty(h2):
                     fixed_cols.append("Name" if "name" in h1.lower() else h1)
                else:
                     fixed_cols.append(f"{h1} {h2}")

        df_raw.columns = fixed_cols
        
        # [CRITICAL FIX] Clean spaces off headers and filter structurally empty columns
        df = df_raw.loc[:, ~df_raw.columns.str.lower().str.contains('^unnamed')]
        df.columns = df.columns.astype(str).str.strip()
        df = df.loc[:, df.columns != ""]
        
        return df
    except Exception as e:
        print(f"Error parsing file: {e}")
        return pd.DataFrame()

def normalize_branch_data(df, branch_name):
    """
    Standardizes the DF: computes Results, Total, Percentage, and Categories.
    Matches the logic from ranking.py/overview.py.
    """
    if df.empty: return df

    # --- FIXED: Aggressively identify USN/ID and Name columns ---
    usn_candidates = [c for c in df.columns if 'usn' in str(c).lower() or 'id' in str(c).lower()]
    id_col = usn_candidates[0] if usn_candidates else df.columns[0]
    if id_col != 'Student_ID':
        df = df.rename(columns={id_col: 'Student_ID'})
    
    name_candidates = [c for c in df.columns if 'name' in str(c).lower() and c != 'Student_ID']
    if name_candidates:
        df = df.rename(columns={name_candidates[0]: 'Name'})
    elif 'Name' not in df.columns:
        df['Name'] = "-"

    # Subject Columns Detection
    total_cols = [c for c in df.columns if any(k in c.lower() for k in ['total', 'marks', 'score']) and c != 'Total_Marks']
    
    # Calculate Total Marks if missing
    if 'Total_Marks' not in df.columns:
        if total_cols:
            df[total_cols] = df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
            df['Total_Marks'] = df[total_cols].sum(axis=1)
        else:
            df['Total_Marks'] = 0

    # Result Logic
    result_cols = [c for c in df.columns if c.endswith('Result')]
    
    if result_cols:
        def calc_overall(row):
            subject_status = []
            for res_col in result_cols:
                # Find corresponding External safely
                base_name = res_col.replace(' Result', '').replace('Result', '').strip()
                ext_col = f"{base_name} External"
                if ext_col not in df.columns:
                     ext_candidates = [c for c in df.columns if base_name in c and "External" in c]
                     ext_col = ext_candidates[0] if ext_candidates else None
                
                e_val = 0
                if ext_col:
                     e_val = pd.to_numeric(row.get(ext_col, 0), errors='coerce')
                     if pd.isna(e_val): e_val = 0
                
                # Result value
                r = str(row.get(res_col, "")).strip().upper()

                if (e_val == 0) and (r in ['A', 'ABSENT']):
                    subject_status.append('A')
                elif r in ['F', 'FAIL']:
                    subject_status.append('F')
                else:
                    subject_status.append('P')

            absent_count = subject_status.count('A')
            fail_count = subject_status.count('F')

            if not subject_status: res = 'P'
            elif absent_count == len(subject_status): res = 'A' 
            elif fail_count > 0 or absent_count > 0: res = 'F' 
            else: res = 'P'
            
            return res

        df['Overall_Result'] = df.apply(calc_overall, axis=1)
    else:
        df['Overall_Result'] = 'P'

    # === FIXED Percentage & Category Logic ===
    def count_active_subjects(row):
        count = 0
        for col in total_cols:
            val = pd.to_numeric(row.get(col), errors='coerce')
            if pd.notna(val) and val > 0:
                count += 1
                continue
            
            # Check result if total marks are 0 or NA
            base = col.replace(' Total', '')
            res_col = f"{base} Result"
            if res_col in df.columns:
                res = str(row.get(res_col, "")).strip().upper()
                if res and res not in ['NAN', 'NONE', '']:
                    count += 1
        return count

    if total_cols:
        df['__Active_Subjects'] = df.apply(count_active_subjects, axis=1)
        # [CRITICAL FIX] Protect against empty series arrays causing IndexError crashes
        mode_series = df['__Active_Subjects'].mode()
        if not mode_series.empty and int(mode_series.iloc[0]) > 0:
            std_subjects = int(mode_series.iloc[0])
        else:
            std_subjects = 1
    else:
        df['__Active_Subjects'] = 0
        std_subjects = 1
    
    def calculate_student_percentage(row):
        active = row.get('__Active_Subjects', 0)
        # Apply the dynamic standard denominator 
        max_subjects = max(std_subjects, active) 
        
        if max_subjects == 0:
            return 0.0
            
        max_marks = max_subjects * 100
        return round((row.get('Total_Marks', 0) / max_marks) * 100, 2)

    df['Percentage'] = df.apply(calculate_student_percentage, axis=1)

    def get_category(row):
        if row['Overall_Result'] != 'P':
            return row['Overall_Result'] 
        
        pct = row.get('Percentage', 0)
        if pct >= 70: return 'FCD'
        elif 60 <= pct < 70: return 'FC'
        elif 50 <= pct < 60: return 'SC'
        else: return 'Pass Class'

    df['Category'] = df.apply(get_category, axis=1)
    df['Branch'] = str(branch_name).strip()
    
    return df

# ==================== LAYOUT ====================

PAGE_CSS = """
.ba-stat-card {
    background: white; border-radius: 12px; padding: 20px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    transition: transform 0.2s;
    height: 100%;
}
.ba-stat-card:hover { transform: translateY(-3px); }
.ba-label { color: #64748b; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.ba-value { color: #1e293b; font-size: 2rem; font-weight: 800; }

/* Keep tables scrollable on screen */
.print-scroll-area { max-height: 500px; overflow-y: auto; overflow-x: hidden; }

/* 1. CRITICAL FIX: Place @page OUTSIDE @media print for Chrome/Edge to respect it */
@page { 
    size: landscape; 
    margin: 10mm; 
}

@media print {
    body, html { 
        -webkit-print-color-adjust: exact !important; 
        print-color-adjust: exact !important; 
        background-color: #ffffff !important; 
        padding: 0 !important; 
        margin: 0 !important; 
    }
    
    /* 2. AGGRESSIVELY NUKE ALL MENUS AND FIXED NAVBARS */
    nav, header, footer, aside, .navbar, .sidebar, 
    .fixed-top, .fixed-bottom, .sticky-top,
    div[style*="position: fixed"], 
    div[style*="position: sticky"] { 
        display: none !important; 
        opacity: 0 !important;
        visibility: hidden !important;
    }
    
    /* Hide config setup and buttons */
    #ba-config-card, #ba-print-btn-container, .d-print-none { 
        display: none !important; 
    }
    
    /* Remove shadows for cleaner print */
    .shadow-sm, .card { box-shadow: none !important; border: 1px solid #e2e8f0 !important; }
    ::-webkit-scrollbar { display: none; }
    
    /* 3. Ensure layouts don't stack awkwardly */
    .container-fluid { padding: 0 !important; margin: 0 !important; }
    .row { display: flex !important; flex-wrap: wrap !important; width: 100%; }
    .col-md-6 { width: 50% !important; float: left; }
    .card { page-break-inside: avoid !important; margin-bottom: 25px !important; display: block !important; }
    
    /* 4. FLATTEN TABLES: Strip absolutely positioned cells in Dash */
    .print-scroll-area { max-height: none !important; height: auto !important; overflow: visible !important; }
    
    .dash-table-container, 
    .dash-spreadsheet-container, 
    .dash-spreadsheet-inner, 
    .dash-spreadsheet-container .dash-spreadsheet-inner * {
        max-height: none !important; 
        height: auto !important; 
        overflow: visible !important;
        position: static !important; /* Forces Dash table to stop floating cells */
    }
}
"""

layout = dbc.Container([
    dcc.Markdown(f"<style>{PAGE_CSS}</style>", dangerously_allow_html=True),
    
    # --- Header ---
    html.Div([
        html.H2("🏛️ University Level Branch Analysis", className="fw-bold text-center mb-2"),
        html.P("Compare performance across multiple branches with centralized intelligence.", className="text-center text-muted")
    ], className="mb-5 mt-5 pt-3 d-print-none"),

    # --- Print Only Header ---
    html.Div([
        html.H2("🏛️ University Level Branch Analysis Report", className="fw-bold text-center mb-4 d-none d-print-block"),
    ]),

    # --- Setup Section ---
    dbc.Card([
        dbc.CardHeader("⚙️ Dashboard Configuration", className="fw-bold bg-light"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Number of Branches to Compare"),
                    dbc.Input(id="ba-branch-count", type="number", min=1, max=10, value=2, className="mb-2"),
                    dbc.Button("Generate Inputs", id="ba-generate-btn", color="primary", size="sm")
                ], md=4),
                dbc.Col([
                    html.Div(id="ba-input-container", className="mt-3 mt-md-0")
                ], md=8)
            ]),
            html.Hr(),
            html.Div(
                dbc.Button("🚀 Analyze & Generate Dashboard", id="ba-analyze-btn", color="success", size="lg", className="w-100 fw-bold"),
                id="ba-analyze-container", style={"display": "none"} # Hidden until inputs generated
            )
        ])
    ], id="ba-config-card", className="shadow-sm mb-5 d-print-none", style={"border": "none", "borderRadius": "12px"}),

    # --- DASHBOARD CONTENT (Hidden until analyzed) ---
    dcc.Loading(
        id="ba-loading",
        type="cube",
        color="#3b82f6",
        children=html.Div(id="ba-dashboard-view")
    )

], fluid=True, className="pb-5 pt-4")


# ==================== CALLBACKS ====================

# 1. Generate Upload Inputs
@callback(
    Output("ba-input-container", "children"),
    Output("ba-analyze-container", "style"),
    Input("ba-generate-btn", "n_clicks"),
    State("ba-branch-count", "value"),
    prevent_initial_call=True
)
def generate_inputs(n, count):
    if not count: return no_update, no_update
    
    inputs = []
    for i in range(count):
        inputs.append(dbc.Row([
            dbc.Col(dbc.Input(
                id={'type': 'ba-name-input', 'index': i},
                placeholder=f"Branch {i+1} Name (e.g., CSE)",
                type="text"
            ), md=4, className="mb-2"),
            dbc.Col(dcc.Upload(
                id={'type': 'ba-file-upload', 'index': i},
                children=html.Div([
                    'Drag & Drop or ', html.A('Select Excel File')
                ], className="text-muted small"),
                style={
                    'width': '100%', 'height': '38px', 'lineHeight': '38px',
                    'borderWidth': '1px', 'borderStyle': 'dashed',
                    'borderRadius': '5px', 'textAlign': 'center', 'borderColor': '#cbd5e1'
                },
                multiple=False
            ), md=8, className="mb-2")
        ], className="mb-2"))
    
    return inputs, {"display": "block"}

# 2. Upload Feedback (Immediate)
@callback(
    Output({'type': 'ba-file-upload', 'index': MATCH}, 'children'),
    Output({'type': 'ba-file-upload', 'index': MATCH}, 'style'),
    Input({'type': 'ba-file-upload', 'index': MATCH}, 'contents'),
    State({'type': 'ba-file-upload', 'index': MATCH}, 'filename'),
    prevent_initial_call=True
)
def update_upload_status(contents, filename):
    if contents:
        return html.Div([
            html.I(className="bi bi-check-circle-fill text-success me-2"),
            str(filename)
        ], className="text-success fw-bold small"), {
            'width': '100%', 'height': '38px', 'lineHeight': '38px',
            'borderWidth': '1px', 'borderStyle': 'solid',
            'borderRadius': '5px', 'textAlign': 'center', 
            'borderColor': '#22c55e', 'backgroundColor': '#f0fdf4'
        }
    return no_update, no_update

# 3. Main Analysis Logic
@callback(
    Output("ba-dashboard-view", "children"),
    Input("ba-analyze-btn", "n_clicks"),
    State({'type': 'ba-file-upload', 'index': ALL}, 'contents'),
    State({'type': 'ba-name-input', 'index': ALL}, 'value'),
    prevent_initial_call=True
)
def analyze_branches(n, file_contents, branch_names):
    if not n or not file_contents:
        return dbc.Alert("Please upload files for all branches.", color="danger")
        
    try:
        university_df = pd.DataFrame()
        branch_stats = []

        # --- PROCESS FILES ---
        for content, name in zip(file_contents, branch_names):
            if not content: continue # Skip empty uploads
            b_name = name if name else "Unknown"
            
            df = process_uploaded_excel(content)
            if df.empty: continue
            
            # Normalize Data
            df = normalize_branch_data(df, b_name)
            if not df.empty:
                university_df = pd.concat([university_df, df], ignore_index=True)

        if university_df.empty:
            return dbc.Alert("No valid data found in uploaded files.", color="warning")

        # --- UPDATE MASTER STORE FOR BRANCH INTELLIGENCE ---
        long_data = []
        result_cols_all = [c for c in university_df.columns if 'Result' in str(c) and c != 'Overall_Result']
        
        for rc in result_cols_all:
            subject_name = rc.replace(' Result', '').strip()
            temp_df = university_df[['Student_ID', 'Name', 'Branch', rc]].copy()
            temp_df.columns = ['Student_ID', 'Name', 'Branch', 'Result']
            temp_df['Subject'] = subject_name
            long_data.append(temp_df)
        
        if long_data:
            ms.MASTER_BRANCH_DATA = pd.concat(long_data, ignore_index=True)
        else:
            ms.MASTER_BRANCH_DATA = pd.DataFrame(columns=["Student_ID", "Name", "Branch", "Subject", "Result"])

        # --- AGGREGATE STATS ---
        uni_total = len(university_df)
        uni_passed = len(university_df[university_df['Overall_Result'] == 'P'])
        uni_failed = len(university_df[university_df['Overall_Result'] == 'F'])
        uni_absent = len(university_df[university_df['Overall_Result'] == 'A'])
        uni_appeared = uni_total - uni_absent
        uni_pass_pct = round((uni_passed / uni_appeared) * 100, 2) if uni_appeared > 0 else 0
        
        # Branch-wise aggregation
        for branch in university_df['Branch'].unique():
            b_df = university_df[university_df['Branch'] == branch]
            
            total = len(b_df)
            passed = len(b_df[b_df['Overall_Result'] == 'P'])
            failed = len(b_df[b_df['Overall_Result'] == 'F'])
            absent = len(b_df[b_df['Overall_Result'] == 'A'])
            appeared = total - absent
            
            pass_pct = round((passed / appeared) * 100, 2) if appeared > 0 else 0
            avg_pct = round(b_df['Percentage'].mean(), 2)
            
            fcd = len(b_df[b_df['Category'] == 'FCD'])
            fc = len(b_df[b_df['Category'] == 'FC'])
            sc = len(b_df[b_df['Category'] == 'SC'])
            
            top_scorer = b_df[b_df['Overall_Result'] == 'P'].sort_values('Percentage', ascending=False)
            top_name = top_scorer.iloc[0]['Name'] if not top_scorer.empty else "-"
            top_pct = f"{top_scorer.iloc[0]['Percentage']}%" if not top_scorer.empty else "-"
            
            branch_stats.append({
                "Branch": branch,
                "Total Students": total,
                "Appeared": appeared,
                "Absent": absent,
                "Passed": passed,
                "Failed": failed,
                "Pass %": pass_pct,
                "Avg %": avg_pct,
                "FCD": fcd,
                "FC": fc,
                "SC": sc,
                "Topper": top_name,
                "Topper %": top_pct
            })

        stats_df = pd.DataFrame(branch_stats).sort_values("Pass %", ascending=False)
        best_branch = stats_df.iloc[0]['Branch'] if not stats_df.empty else "-"

        # --- SUBJECT PERFORMANCE ANALYSIS (BRANCH WISE) ---
        subject_stats_list = []
        
        for r_col in result_cols_all:
            subject = r_col.replace(' Result', '').strip()
            if not subject: continue
            if subject.endswith('Total'): subject = subject.replace('Total', '').strip()

            sub_df = university_df[university_df[r_col].notna()]
            if sub_df.empty: continue
            
            for branch_name, grp in sub_df.groupby('Branch'):
                results = grp[r_col].astype(str).str.strip().str.upper()
                total_students = len(results)
                absent_count = results.isin(['A', 'ABSENT', 'AB']).sum()
                fail_count = results.isin(['F', 'FAIL']).sum()
                pass_count = results.isin(['P', 'PASS']).sum()
                appeared = total_students - absent_count
                pass_pct = round((pass_count / appeared) * 100, 2) if appeared > 0 else 0.0
                
                subject_stats_list.append({
                    "BRANCH": branch_name,
                    "SUBJECT": subject,
                    "TOTAL": total_students,
                    "APPEARED": appeared,
                    "ABSENT": absent_count,
                    "PASSED": pass_count,
                    "FAILED": fail_count,
                    "PASS %": pass_pct
                })

        subject_df = pd.DataFrame(subject_stats_list)
        if not subject_df.empty:
            subject_df = subject_df.sort_values("SUBJECT")
        
        subject_table = dash_table.DataTable(
            data=subject_df.to_dict('records') if not subject_df.empty else [],
            columns=[
                {"name": i, "id": i} for i in ["SUBJECT", "BRANCH", "TOTAL", "APPEARED", "ABSENT", "PASSED", "FAILED", "PASS %"]
            ],
            style_header={
                'backgroundColor': '#1e293b', 
                'color': 'white', 
                'fontWeight': 'bold',
                'textAlign': 'center',
                'textTransform': 'uppercase',
                'fontSize': '13px'
            },
            style_cell={
                'padding': '12px', 
                'textAlign': 'center', 
                'fontFamily': 'Inter, sans-serif',
                'fontSize': '14px',
                'color': '#334155'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fafc'},
                {'if': {'row_index': 'even'}, 'backgroundColor': '#ffffff'},
                {'if': {'column_id': 'BRANCH'}, 'fontWeight': 'bold', 'color': '#3b82f6'},
                {'if': {'filter_query': '{PASS %} >= 95', 'column_id': 'PASS %'}, 'color': '#16a34a', 'fontWeight': 'bold'},
                {'if': {'filter_query': '{PASS %} >= 80 && {PASS %} < 95', 'column_id': 'PASS %'}, 'color': '#059669', 'fontWeight': 'bold'},
                {'if': {'filter_query': '{PASS %} < 50', 'column_id': 'PASS %'}, 'color': '#dc2626', 'fontWeight': 'bold'},
            ],
            sort_action="native",
            page_action="none",
            style_table={'borderRadius': '10px', 'boxShadow': '0 4px 6px -1px rgba(0,0,0,0.1)'}
        )

        # --- BUILD VISUALS ---
        
        fig_pass = px.bar(
            stats_df,
            x='Branch',
            y='Pass %',
            color='Pass %',
            color_continuous_scale='RdYlGn',
            title='Pass Rate by Branch',
            labels={'Pass %': 'Pass Percentage'},
            text='Pass %'
        )
        fig_pass.update_traces(textposition='auto')
        fig_pass.update_layout(
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='white',
            font=dict(family='Inter, sans-serif'),
            coloraxis_colorbar=dict(title='Pass %')
        )
        
        category_dist = university_df['Category'].value_counts().reset_index()
        category_dist.columns = ['Category', 'Count']
        fig_dist = px.pie(
            category_dist,
            names='Category',
            values='Count',
            title='Student Distribution by Category',
            color_discrete_map={'FCD': '#16a34a', 'FC': '#10b981', 'SC': '#60a5fa', 'Pass Class': '#f59e0b', 'F': '#ef4444', 'A': '#94a3b8'}
        )
        fig_dist.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='white',
            font=dict(family='Inter, sans-serif')
        )
        
        # Top Rankers Table (With Tie Breaker and updated sorting)
        sort_cols = ['Percentage', 'Total_Marks'] if 'Total_Marks' in university_df.columns else ['Percentage']
        sort_asc = [False, False] if 'Total_Marks' in university_df.columns else [False]
        
        required_cols = ['Student_ID', 'Name', 'Branch']
        if 'Total_Marks' in university_df.columns: required_cols.append('Total_Marks')
        required_cols.extend(['Percentage', 'Category'])

        top_rankers = university_df[university_df['Overall_Result'] == 'P'].sort_values(
            by=sort_cols, ascending=sort_asc
        ).head(10)[required_cols].copy()

        if not top_rankers.empty:
            top_rankers.insert(0, 'Rank', range(1, len(top_rankers) + 1))
            
        rank_table = dash_table.DataTable(
            data=top_rankers.to_dict('records') if not top_rankers.empty else [],
            columns=[{"name": str(i).replace('_', ' '), "id": i} for i in top_rankers.columns] if not top_rankers.empty else [],
            style_header={'backgroundColor': '#1e293b', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'},
            style_cell={'padding': '12px', 'textAlign': 'center', 'fontFamily': 'Inter', 'color': '#334155'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fafc'},
            ],
            style_table={'borderRadius': '10px', 'overflow': 'hidden', 'boxShadow': '0 4px 6px -1px rgba(0,0,0,0.1)'}
        )

        # 1. KPI Cards (Interactive Tabs for Overall vs Branch)
        def create_kpi_cards(kpi_data):
            return dbc.Row([
                dbc.Col(
                    html.Div(
                        dbc.CardBody([
                            html.Div([
                                html.Div(
                                    html.I(className=f"bi {k['icon']}", style={"color": k["color"], "fontSize": "1.4rem"}),
                                     className="d-flex align-items-center justify-content-center",
                                     style={"minWidth": "42px", "width": "42px", "height": "42px", "borderRadius": "10px", "backgroundColor": k["bg"]}
                                ),
                                html.Div([
                                    html.H6(k["label"], className="text-muted text-uppercase fw-bold mb-0", style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                                    # Font scale dynamic and truncated for long Topper Names
                                    html.H3(str(k["val"]), className="fw-bold mb-0 text-truncate", style={"color": k["color"], "fontSize": "1.4rem", "maxWidth": "120px"}),
                                ], className="ms-3")
                            ], className="d-flex align-items-center h-100")
                        ], className="p-3"),
                        className="card shadow-sm h-100 border-0 ba-stat-card",
                        style={"borderLeft": f"4px solid {k['color']}"}
                    )
                ) for k in kpi_data
            ], className="row-cols-2 row-cols-md-3 row-cols-lg-6 g-3 mt-1 pb-3")

        # Base Overview Tab
        overall_kpis = [
            {"label": "Total Students", "val": uni_total, "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
            {"label": "Appeared", "val": uni_appeared, "color": "#10b981", "bg": "#ecfdf5", "icon": "bi-person-circle"},
            {"label": "Passed", "val": uni_passed, "color": "#0ea5e9", "bg": "#f0f9ff", "icon": "bi-check-circle-fill"},
            {"label": "Failed", "val": uni_failed, "color": "#ef4444", "bg": "#fef2f2", "icon": "bi-x-circle-fill"},
            {"label": "Overall Pass %", "val": f"{uni_pass_pct}%", "color": "#8b5cf6", "bg": "#f5f3ff", "icon": "bi-percent"},
            {"label": "Best Branch", "val": best_branch, "color": "#f59e0b", "bg": "#fffbeb", "icon": "bi-trophy-fill"}
        ]

        kpi_tabs_list = [dbc.Tab(create_kpi_cards(overall_kpis), label="🌍 Overall Summary", tab_id="tab-overall", tab_style={"fontWeight": "bold", "color": "#0f172a", "padding": "8px 20px"})]
        
        # Tabs for Individual Branches dynamically generated
        for stat in branch_stats:
            # Extract just first name of Topper to fit nicely
            t_name = str(stat.get('Topper', '-')).split(' ')[0] if stat.get('Topper') and stat.get('Topper') != "-" else "-"
            
            b_kpis = [
                {"label": "Total Students", "val": stat['Total Students'], "color": "#3b82f6", "bg": "#eff6ff", "icon": "bi-people-fill"},
                {"label": "Appeared", "val": stat['Appeared'], "color": "#10b981", "bg": "#ecfdf5", "icon": "bi-person-circle"},
                {"label": "Passed", "val": stat['Passed'], "color": "#0ea5e9", "bg": "#f0f9ff", "icon": "bi-check-circle-fill"},
                {"label": "Failed", "val": stat['Failed'], "color": "#ef4444", "bg": "#fef2f2", "icon": "bi-x-circle-fill"},
                {"label": "Pass %", "val": f"{stat['Pass %']}%", "color": "#8b5cf6", "bg": "#f5f3ff", "icon": "bi-percent"},
                {"label": "Branch Topper", "val": t_name, "color": "#f59e0b", "bg": "#fffbeb", "icon": "bi-award-fill"}
            ]
            kpi_tabs_list.append(dbc.Tab(create_kpi_cards(b_kpis), label=f"📍 {stat['Branch']}", tab_id=f"tab-{stat['Branch']}", tab_style={"fontWeight": "600", "color": "#475569", "padding": "8px 20px"}))

        kpi_container = html.Div([
            dbc.Tabs(kpi_tabs_list, active_tab="tab-overall", className="mb-2 border-bottom"),
        ], className="mb-4")

        # 2. Detailed Branch KPI Table
        branch_grid = dash_table.DataTable(
            data=stats_df.to_dict('records') if not stats_df.empty else [],
            columns=[
                {"name": "Branch", "id": "Branch"},
                {"name": "Total", "id": "Total Students"},
                {"name": "Appeared", "id": "Appeared"},
                {"name": "Absent", "id": "Absent"},
                {"name": "Passed", "id": "Passed"},
                {"name": "Failed", "id": "Failed"},
                {"name": "Pass %", "id": "Pass %"},
                {"name": "Avg %", "id": "Avg %"},
                {"name": "FCD", "id": "FCD"},
                {"name": "Topper", "id": "Topper"},
                {"name": "%", "id": "Topper %"}
            ],
            style_header={'backgroundColor': '#0f172a', 'color': 'white', 'fontWeight': 'bold', 'textTransform': 'uppercase'},
            style_cell={'padding': '12px', 'textAlign': 'center', 'fontFamily': 'Inter'},
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fafc'},
                {'if': {'column_id': 'Pass %'}, 'fontWeight': 'bold', 'color': '#059669', 'backgroundColor': '#f0fdf4'},
                {'if': {'column_id': 'Failed', 'filter_query': '{Failed} > 0'}, 'color': '#ef4444', 'fontWeight': 'bold'},
            ],
            style_table={'borderRadius': '10px', 'overflow': 'hidden', 'boxShadow': '0 4px 6px -1px rgba(0,0,0,0.1)'}
        )

        # Print PDF Button Row
        print_container = html.Div([
            dbc.Button([html.I(className="bi bi-file-pdf-fill me-2"), "Download Full Report (PDF)"], id="ba-print-btn", color="danger", outline=True, className="fw-bold fw-sm shadow-sm")
        ], id="ba-print-btn-container", className="d-flex justify-content-end mb-4 d-print-none")

        # --- ASSEMBLE VIEW (Clean Single Page) ---
        return html.Div([
            # Print Button
            print_container,
            # Interactive KPIs (Updated)
            kpi_container,
            
            # Branch-wise KPIs (Priority Request)
            dbc.Card([
                dbc.CardHeader([
                     html.I(className="bi bi-grid-3x3-gap me-2"),
                     "Branch-wise KPI Summary"
                ], className="fw-bold bg-white", style={"fontSize": "1.1rem", "borderBottom": "2px solid #f1f5f9"}),
                dbc.CardBody(branch_grid, className="p-0")
            ], className="shadow-sm border-0 mb-4", style={"overflow": "hidden", "borderRadius": "12px"}),
            
            # Graphs
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardBody(dcc.Graph(figure=fig_pass))
                ], className="shadow-sm border-0 h-100"), md=6, className="mb-4"),
                dbc.Col(dbc.Card([
                    dbc.CardBody(dcc.Graph(figure=fig_dist))
                ], className="shadow-sm border-0 h-100"), md=6, className="mb-4")
            ], style={"pageBreakInside": "avoid"}),

            # Subject Performance
            dbc.Card([
                dbc.CardHeader([
                     html.I(className="bi bi-table me-2"),
                     "Subject Level Performance (Branch/Section Wise)"
                ], className="fw-bold bg-white", style={"fontSize": "1.1rem", "borderBottom": "2px solid #f1f5f9"}),
                dbc.CardBody(
                    html.Div(subject_table, className="print-scroll-area"), 
                    className="p-0"
                )
            ], className="shadow-sm border-0 mb-5", style={"overflow": "hidden", "borderRadius": "12px"}),

            # Top Rankers
            dbc.Row([
                dbc.Col([
                    html.H5("👑 University Top Rankers", className="fw-bold mb-3 text-dark text-center"),
                    rank_table
                ], width=12, className="mb-5")
            ])
        ])

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        return dbc.Alert([
            html.H5("An error occurred during calculation.", className="alert-heading"),
            html.Hr(),
            html.Pre(err_msg, style={"fontSize": "0.8rem", "whiteSpace": "pre-wrap"})
        ], color="danger", className="mt-4 shadow-sm")

# 4. Clientside Callback to trigger PDF Download/Print
dash.clientside_callback(
    "function(n_clicks) { if (n_clicks > 0) { window.print(); } return window.dash_clientside.no_update; }",
    Output("ba-print-btn", "n_clicks"),
    Input("ba-print-btn", "n_clicks"),
    prevent_initial_call=True
)