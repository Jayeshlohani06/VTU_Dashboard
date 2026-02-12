import dash
from dash import html, dcc, Input, Output, State, callback, ALL, dash_table, no_update
import dash_bootstrap_components as dbc
import base64
import io
import pandas as pd
import re
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

dash.register_page(__name__, path="/branch-analysis", name="Branch Analysis")

# ==================== HELPERS ====================

def process_uploaded_excel(contents):
    """Parses raw Excel content into a clean DataFrame."""
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        # VTU format typically has 2 header rows
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
        # Remove empty columns
        df = df_raw.loc[:, df_raw.columns.str.strip() != ""]
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
    num_subjects = len(subject_total_cols) if subject_total_cols else 0
    max_possible = num_subjects * 100 if num_subjects > 0 else 100

    if num_subjects > 0:
        df['Percentage'] = (df['Total_Marks'] / max_possible * 100).round(2)
    else:
        df['Percentage'] = 0.0

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

# 2. Main Analysis Logic
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

    # --- BUILD VISUALS ---

    # 1. KPI Cards
    kpis = [
        {"label": "Total Students", "val": uni_total, "color": "#3b82f6"},
        {"label": "Overall Pass %", "val": f"{uni_pass_pct}%", "color": "#10b981"},
        {"label": "Best Branch", "val": best_branch, "color": "#8b5cf6"},
        {"label": "University Topper", "val": uni_topper_row['Name'] if uni_topper_row is not None else "-", "color": "#f59e0b", "sub": f"{uni_topper_row['Percentage']}% ({uni_topper_row['Branch']})" if uni_topper_row is not None else ""}
    ]

    kpi_section = dbc.Row([
        dbc.Col(html.Div([
            html.Div(k['label'], className="ba-label"),
            html.Div(k['val'], className="ba-value", style={"color": k['color']}),
            html.Div(k.get('sub', ''), className="text-muted small fw-bold")
        ], className="ba-stat-card"), md=3, className="mb-4") for k in kpis
    ])

    # 2. Charts
    # Pass % Bar Chart
    fig_pass = px.bar(
        stats_df, x="Branch", y="Pass %", text="Pass %",
        title="Pass Percentage by Branch",
        color="Pass %", color_continuous_scale="Greens"
    )
    fig_pass.update_layout(template="plotly_white", coloraxis_showscale=False)
    fig_pass.update_traces(texttemplate='%{text:.1f}%', textposition='outside')

    # Category Stacked Bar
    fig_dist = go.Figure()
    for cat, color in [('FCD', '#059669'), ('FC', '#3b82f6'), ('SC', '#f59e0b'), ('F', '#ef4444')]:
        # Map F to Failed count for visualization context
        if cat == 'F':
            y_vals = stats_df['Failed']
            name = "Fail"
        else:
            y_vals = stats_df[cat]
            name = cat
            
        fig_dist.add_trace(go.Bar(name=name, x=stats_df['Branch'], y=y_vals, marker_color=color))

    fig_dist.update_layout(barmode='stack', title="Grade Distribution Analysis", template="plotly_white")

    # 3. Main Data Table
    table = dash_table.DataTable(
        data=stats_df.to_dict('records'),
        columns=[{"name": i, "id": i} for i in ["Branch", "Total Students", "Passed", "Failed", "Pass %", "Avg %", "Topper", "Topper %"]],
        style_table={'borderRadius': '10px', 'overflow': 'hidden', 'boxShadow': '0 4px 6px -1px rgba(0,0,0,0.1)'},
        style_header={'backgroundColor': '#1e293b', 'color': 'white', 'fontWeight': 'bold'},
        style_cell={'padding': '12px', 'textAlign': 'center', 'fontFamily': 'Inter'},
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8fafc'},
            {'if': {'column_id': 'Pass %'}, 'fontWeight': 'bold', 'color': '#059669'}
        ]
    )

    # --- ASSEMBLE VIEW ---
    return html.Div([
        kpi_section,
        
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_pass), md=6),
            dbc.Col(dcc.Graph(figure=fig_dist), md=6)
        ], className="mb-4"),
        
        dbc.Card([
            dbc.CardHeader("📋 Detailed Branch Performance Report", className="fw-bold bg-white"),
            dbc.CardBody(table)
        ], className="shadow-sm border-0")
    ])
