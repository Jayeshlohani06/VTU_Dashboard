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
                is_empty = lambda h: str(h).lower() == "nan" or str(h).startswith("Unnamed:")
                
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
                is_empty = lambda h: str(h).lower() == "nan" or str(h).startswith("Unnamed:")

                if not is_empty(h1):
                    last_valid_code = h1
                elif last_valid_code:
                    h1 = last_valid_code
                
                if is_empty(h2):
                     fixed_cols.append("Name" if "name" in h1.lower() else h1)
                else:
                     fixed_cols.append(f"{h1} {h2}")

        df_raw.columns = fixed_cols
        # Remove empty columns
        df = df_raw.loc[:, ~df_raw.columns.str.contains('^Unnamed')]
        df = df.loc[:, df.columns.str.strip() != ""]
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

    # Standardize ID column
    if df.columns[0] != 'Student_ID':
        df = df.rename(columns={df.columns[0]: 'Student_ID'})
    
    if 'Name' not in df.columns:
        df['Name'] = ""

    # Subject Columns Detection
    total_cols = [c for c in df.columns if any(k in c.lower() for k in ['total', 'marks', 'score']) and c != 'Total_Marks']
    # Filter to only "Subject Total" columns (usually ending in "Total")
    # Strict VTU format: "SUBCODE Total"
    subject_total_cols = [c for c in df.columns if c.endswith(' Total')]
    
    # Calculate Total Marks if missing
    if 'Total_Marks' not in df.columns:
        if subject_total_cols:
            df[subject_total_cols] = df[subject_total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
            df['Total_Marks'] = df[subject_total_cols].sum(axis=1)
        else:
            df['Total_Marks'] = 0

    # Result Logic
    result_cols = [c for c in df.columns if c.endswith('Result')]
    
    if result_cols:
        def calc_overall(row):
            subject_status = []
            for res_col in result_cols:
                # Find corresponding External
                base_name = res_col.replace(' Result', '').replace('Result', '').strip()
                # Try specific variations
                ext_col = f"{base_name} External"
                if ext_col not in df.columns:
                     # Fallback check
                     ext_candidates = [c for c in df.columns if base_name in c and "External" in c]
                     ext_col = ext_candidates[0] if ext_candidates else None
                
                e_val = 0
                if ext_col:
                     e_val = pd.to_numeric(row.get(ext_col, 0), errors='coerce')
                     if pd.isna(e_val): e_val = 0
                
                # Result value
                r = str(row.get(res_col, "")).strip().upper()

                # Logic: Absent if (Ext=0 AND Result=A)
                if (e_val == 0) and (r in ['A', 'ABSENT']):
                    subject_status.append('A')
                elif r in ['F', 'FAIL']:
                    subject_status.append('F')
                else:
                    subject_status.append('P')

            absent_count = subject_status.count('A')
            fail_count = subject_status.count('F')

            if not subject_status: res = 'P'
            elif absent_count == len(subject_status): res = 'A' # All absent
            elif fail_count > 0 or absent_count > 0: res = 'F' # Any fail/absent (but not all absent)
            else: res = 'P'
            
            return res

        df['Overall_Result'] = df.apply(calc_overall, axis=1)
    else:
        # Fallback if no result columns (unlikely for VTU)
        df['Overall_Result'] = 'P'

    # Percentage & Category Logic
    # Assume Max Marks = 100 per subject
    
    def calculate_student_percentage(row):
        subjects_attempted = 0
        for col in subject_total_cols:
            val = pd.to_numeric(row.get(col), errors='coerce')
            if pd.notna(val) and val > 0:
                subjects_attempted += 1
        
        if subjects_attempted == 0:
            return 0.0
            
        max_marks = subjects_attempted * 100
        return round((row.get('Total_Marks', 0) / max_marks) * 100, 2)

    df['Percentage'] = df.apply(calculate_student_percentage, axis=1)

    def get_category(row):
        if row['Overall_Result'] != 'P':
            return row['Overall_Result'] # Return 'F' or 'A'
        
        pct = row['Percentage']
        if pct >= 70: return 'FCD'
        elif 60 <= pct < 70: return 'FC'
        elif 50 <= pct < 60: return 'SC'
        else: return 'Pass Class'

    df['Category'] = df.apply(get_category, axis=1)
    df['Branch'] = branch_name
    
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
"""

layout = dbc.Container([
    dcc.Markdown(f"<style>{PAGE_CSS}</style>", dangerously_allow_html=True),
    
    # --- Header ---
    html.Div([
        html.H2("🏛️ University Level Branch Analysis", className="fw-bold text-center mb-2"),
        html.P("Compare performance across multiple branches with centralized intelligence.", className="text-center text-muted")
    ], className="mb-5 mt-4"),

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
    ], className="shadow-sm mb-5", style={"border": "none", "borderRadius": "12px"}),

    # --- DASHBOARD CONTENT (Hidden until analyzed) ---
    dcc.Loading(
        id="ba-loading",
        type="cube",
        color="#3b82f6",
        children=html.Div(id="ba-dashboard-view")
    )

], fluid=True, className="pb-5")


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

    university_df = pd.DataFrame()
    branch_stats = []

    # --- PROCESS FILES ---
    for content, name in zip(file_contents, branch_names):
        if not content: continue # Skip empty
        b_name = name if name else "Unknown"
        
        df = process_uploaded_excel(content)
        if df.empty: continue
        
        # Normalize Data
        df = normalize_branch_data(df, b_name)
        university_df = pd.concat([university_df, df], ignore_index=True)

    if university_df.empty:
        return dbc.Alert("No valid data found in uploaded files.", color="warning")

    # --- UPDATE MASTER STORE FOR BRANCH INTELLIGENCE ---
    # Convert Wide Format (University DF) -> Long Format (Master Store)
    long_data = []
    result_cols_all = [c for c in university_df.columns if 'Result' in c and c != 'Overall_Result']
    
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
    uni_pass_pct = round((uni_passed / uni_total) * 100, 2)
    
    uni_topper_row = university_df[university_df['Overall_Result'] == 'P'].sort_values('Percentage', ascending=False).iloc[0] if uni_passed > 0 else None
    
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
        
        top_scorer = b_df[b_df['Overall_Result'] == 'P'].sort_values('Percentage', ascending=False).iloc[0] if passed > 0 else None
        
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
            "Topper": top_scorer['Name'] if top_scorer is not None else "-",
            "Topper %": f"{top_scorer['Percentage']}%" if top_scorer is not None else "-"
        })

    stats_df = pd.DataFrame(branch_stats).sort_values("Pass %", ascending=False)
    best_branch = stats_df.iloc[0]['Branch'] if not stats_df.empty else "-"

    # --- SUBJECT PERFORMANCE ANALYSIS (BRANCH WISE) ---
    subject_stats_list = []
    
    # Identify Result columns to find subjects
    result_cols = [c for c in university_df.columns if 'Result' in c and c != 'Overall_Result']
    
    for r_col in result_cols:
        subject = r_col.replace(' Result', '').strip()
        if not subject: continue
        if subject.endswith('Total'): subject = subject.replace('Total', '').strip()

        sub_df = university_df[university_df[r_col].notna()]
        if sub_df.empty: continue
        
        # Group by Branch
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
            # Highlight Branch Column
            {'if': {'column_id': 'BRANCH'}, 'fontWeight': 'bold', 'color': '#3b82f6'},
            # Color logic for PASS %
            {
                'if': {'filter_query': '{PASS %} >= 95', 'column_id': 'PASS %'},
                'color': '#16a34a', 'fontWeight': 'bold'
            },
            {
                'if': {'filter_query': '{PASS %} >= 80 && {PASS %} < 95', 'column_id': 'PASS %'},
                'color': '#059669', 'fontWeight': 'bold'
            },
            {
                'if': {'filter_query': '{PASS %} < 50', 'column_id': 'PASS %'},
                'color': '#dc2626', 'fontWeight': 'bold'
            },
        ],
        sort_action="native",
        page_size=20,
        style_table={'borderRadius': '10px', 'overflow': 'hidden', 'boxShadow': '0 4px 6px -1px rgba(0,0,0,0.1)'}
    )

    # --- BUILD VISUALS ---

    # 1. KPI Cards
    kpis = [
        {"label": "Total Students", "val": uni_total, "color": "#3b82f6", "icon": "bi-people-fill"},
        {"label": "Overall Pass %", "val": f"{uni_pass_pct}%", "color": "#10b981", "icon": "bi-graph-up-arrow"},
        {"label": "Best Branch", "val": best_branch, "color": "#8b5cf6", "icon": "bi-trophy-fill"},
        {"label": "University Topper", "val": uni_topper_row['Name'] if uni_topper_row is not None else "-", "color": "#f59e0b", "icon": "bi-award-fill", "sub": f"{uni_topper_row['Percentage']}%" if uni_topper_row is not None else ""}
    ]

    kpi_section = dbc.Row([
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.Div([
                        html.Div(
                            html.I(className=f"bi {k['icon']}", style={"color": k["color"], "fontSize": "1.5rem"}),
                            style={"minWidth": "48px", "width": "48px", "height": "48px", "borderRadius": "12px", "backgroundColor": f"{k['color']}15", "display": "flex", "alignItems": "center", "justifyContent": "center"}
                        ),
                        html.Div([
                            html.H6(k["label"], className="text-muted text-uppercase fw-bold mb-1", style={"fontSize": "0.7rem", "letterSpacing": "0.5px"}),
                            html.H3(str(k["val"]), className="fw-bold mb-0", style={"color": k["color"], "fontSize": "1.6rem"}),
                            # Subtitle for topper percentage
                            html.Small(k.get('sub', ''), className="text-success fw-bold d-block mt-1") if k.get('sub') else None
                        ], className="ms-3")
                    ], className="d-flex align-items-center h-100")
                ], className="p-3"),
                className="kpi-card shadow-sm h-100 border-0",
                style={"borderLeft": f"4px solid {k['color']}", "transition": "transform 0.2s ease-in-out"}
            ), md=3, sm=6, className="mb-4"
        ) for k in kpis
    ])

    # 2. Detailed Branch KPI Table
    branch_grid = dash_table.DataTable(
        data=stats_df.to_dict('records'),
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

    # 3. Charts
    # Pass % Bar Chart
    fig_pass = px.bar(
        stats_df, x="Branch", y="Pass %", text="Pass %",
        title="Pass Percentage by Branch",
        color="Pass %", color_continuous_scale="Viridis"
    )
    fig_pass.update_layout(template="plotly_white", coloraxis_showscale=False, title_x=0.5)
    fig_pass.update_traces(texttemplate='%{text:.1f}%', textposition='outside')

    # Category Stacked Bar
    fig_dist = go.Figure()
    for cat, color in [('FCD', '#059669'), ('FC', '#3b82f6'), ('SC', '#f59e0b'), ('F', '#ef4444')]:
        if cat == 'F':
            y_vals = stats_df['Failed']
            name = "Fail"
        else:
            y_vals = stats_df[cat]
            name = cat
            
        fig_dist.add_trace(go.Bar(name=name, x=stats_df['Branch'], y=y_vals, marker_color=color))

    fig_dist.update_layout(barmode='stack', title="Grade Distribution Analysis", template="plotly_white", title_x=0.5)

    # 4. Top Rankers Table
    top_10_df = university_df[university_df['Overall_Result'] == 'P'].sort_values('Percentage', ascending=False).head(10)
    top_10_df = top_10_df[['Student_ID', 'Name', 'Branch', 'Total_Marks', 'Percentage']]
    top_10_df.insert(0, 'Rank', range(1, 1 + len(top_10_df)))

    rank_table = dash_table.DataTable(
        data=top_10_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in top_10_df.columns],
        style_header={'backgroundColor': '#f59e0b', 'color': 'white', 'fontWeight': 'bold'},
        style_cell={'padding': '10px', 'textAlign': 'center'},
        style_table={'borderRadius': '10px', 'overflow': 'hidden', 'boxShadow': '0 4px 6px -1px rgba(0,0,0,0.1)'}
    )

    # --- ASSEMBLE VIEW (Clean Single Page) ---
    return html.Div([
        # KPIs
        kpi_section,
        
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
        ]),

        # Subject Performance
        dbc.Card([
            dbc.CardHeader([
                 html.I(className="bi bi-table me-2"),
                 "Subject Level Performance (Branch/Section Wise)"
            ], className="fw-bold bg-white", style={"fontSize": "1.1rem", "borderBottom": "2px solid #f1f5f9"}),
            dbc.CardBody(subject_table, className="p-0")
        ], className="shadow-sm border-0 mb-5", style={"overflow": "hidden", "borderRadius": "12px"}),

        # Top Rankers
        dbc.Row([
            dbc.Col([
                html.H5("👑 University Top Rankers", className="fw-bold mb-3 text-dark text-center"),
                rank_table
            ], width=12, className="mb-5")
        ])
    ])