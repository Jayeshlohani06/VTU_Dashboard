# pages/ranking.py
# Full upgraded Ranking page: fixes + UI improvements + animations + top5 colors

import dash  # for dash.ctx in callbacks
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import re
from functools import lru_cache
from io import StringIO  # <--- Added for Pandas compatibility

# Register page
dash.register_page(__name__, path="/ranking", name="Ranking")

# ==================== Helpers ====================

def extract_numeric(roll):
    """Extract last numeric group from an ID like '1AY23IS001' -> 1."""
    digits = re.findall(r'\d+', str(roll))
    return int(digits[-1]) if digits else 0

def assign_section(roll_no, section_ranges):
    """
    Assign section based on numeric roll range mapping, e.g.
    {'A': ('...001', '...080'), 'B': ('...081', '...160')}
    """
    roll_num = extract_numeric(roll_no)
    if section_ranges:
        for sec_name, (start, end) in section_ranges.items():
            start_num = extract_numeric(start)
            end_num = extract_numeric(end)
            if start_num <= roll_num <= end_num:
                return sec_name
    return "Unassigned"

def _normalize_df(df, section_ranges):
    """
    Ensure consistent schema:
      - First column is 'Student_ID'
      - Add/compute 'Section'
      - Build 'Total_Marks' from any total-like columns
      - Compute 'Overall_Result' from existing Result* cols, else simple derived rule
      - Ensure 'Name' column exists (helpful for searching)
    """
    # Ensure first col is Student_ID
    if df.columns[0] != 'Student_ID':
        df = df.rename(columns={df.columns[0]: 'Student_ID'})

    # Compute Section from ranges
    df['Section'] = df['Student_ID'].apply(lambda x: assign_section(str(x), section_ranges))

    # Detect columns that look like totals/scores (exclude the one we add)
    total_cols = [c for c in df.columns if any(k in c.lower() for k in ['total', 'marks', 'score'])]
    total_cols = [c for c in total_cols if c != 'Total_Marks']
    if total_cols:
        df[total_cols] = df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
        df['Total_Marks'] = df[total_cols].sum(axis=1)
    else:
        df['Total_Marks'] = 0

    # Prefer explicit Result* columns; otherwise derive a simple pass/fail
    result_cols = [c for c in df.columns if 'result' in c.lower()]
    if result_cols:
        df['Overall_Result'] = (
            df[result_cols]
            .apply(lambda row: 'P' if all(str(v).strip().upper() == 'P' for v in row if pd.notna(v)) else 'F', axis=1)
        )
    else:
        pass_mark = 18
        if total_cols:
            df['Overall_Result'] = df.apply(
                lambda row: 'F' if any(row[c] < pass_mark for c in total_cols) else 'P', axis=1
            )
        else:
            df['Overall_Result'] = 'P'

    # Ensure Name exists (even if blank) for search UX parity
    if 'Name' not in df.columns:
        df['Name'] = ""

    return df

@lru_cache(maxsize=32)
def _prepare_base(json_str, section_key):
    # FIX: Wrapped in StringIO
    df = pd.read_json(StringIO(json_str), orient='split')
    section_ranges = None
    if section_key not in (None, "None"):
        try:
            section_ranges = ast.literal_eval(section_key)
        except Exception:
            section_ranges = None

    df = _normalize_df(df, section_ranges)
    return df

def _section_key(section_ranges):
    """Convert section mapping dict to a stable string for lru_cache keying."""
    try:
        return repr(section_ranges)
    except Exception:
        return "None"


# ==================== Themes (CSS injected via <style>) ====================

PAGE_CSS_LIGHT = r"""
:root{
  --bg: #f5f7fb;
  --card: #ffffff;
  --text: #111827;
  --muted:#6b7280;
  --primary:#1f2937;
  --brand:#3b82f6;
  --shadow: 0 8px 24px rgba(16,24,40,.08);

  --k1:#fff7e6; /* rank1 chip */
  --k2:#eef2ff; /* rank2 chip */
  --k3:#fef3c7; /* rank3 chip */
  --k45:#f1f5f9; /* rank4/5 chip */
  --fail:#fee2e2; /* soft red */
}

/* page wrapper */
.rnk-wrap{ background: var(--bg); padding: 18px; border-radius: 14px; }

/* section cards */
.rnk-card{
  background: var(--card);
  border: 0 !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow);
  transition: transform .2s ease, box-shadow .2s ease;
}
.rnk-card:hover{ transform: translateY(-1px); box-shadow: 0 12px 28px rgba(16,24,40,.12); }

/* header */
.rnk-title{ color: var(--primary); letter-spacing:.5px; }

/* sticky controls */
.rnk-controls-wrap{ position: sticky; top: 0; z-index: 10; }

/* control row */
.rnk-controls .btn, .rnk-controls .form-select, .rnk-controls .form-control{
  border-radius: 10px !important;
}

/* KPI */
.kpi-card{ border-left: 6px solid transparent; }
.kpi-label{ color: var(--muted); font-size:.9rem; }
.kpi-value{ font-weight:800; transition: transform .3s ease; }
.kpi-card:hover .kpi-value{ transform: scale(1.03); }

/* chips */
.rank-chip{ display:inline-block; padding:.35rem .6rem; border-radius: 9999px; font-weight:700; }
.rank-1{ background:var(--k1); }
.rank-2{ background:var(--k2); }
.rank-3{ background:var(--k3); }
.rank-4,.rank-5{ background:var(--k45); }

.badge-pass{ background:#ecfdf5; color:#065f46; padding:.2rem .5rem; border-radius:9999px; font-weight:700; }
.badge-fail{ background:#fee2e2; color:#7f1d1d; padding:.2rem .5rem; border-radius:9999px; font-weight:700; }

/* lists */
.bullet{ margin:0; padding-left: 1rem; }
.bullet li{ margin:.35rem 0; }

/* datatable polish */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td,
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th{
  border-color:#e5e7eb !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td{
  background:#f8fafc !important;
}
"""

PAGE_CSS_DARK = r"""
:root{
  --bg: #0b1220;
  --card: #0f172a;
  --text: #e5e7eb;
  --muted:#9ca3af;
  --primary:#e5e7eb;
  --brand:#60a5fa;
  --shadow: 0 8px 24px rgba(0,0,0,.45);

  --k1:#1f2937;
  --k2:#111827;
  --k3:#1f2937;
  --k45:#0b1220;
  --fail:#3b0d0d;
}

.rnk-wrap{ background: var(--bg); padding: 18px; border-radius: 14px; }
.rnk-card{
  background: var(--card);
  border: 0 !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow);
  transition: transform .2s ease, box-shadow .2s ease;
}
.rnk-card:hover{ transform: translateY(-1px); box-shadow: 0 12px 28px rgba(0,0,0,.6); }
.rnk-title{ color: var(--primary); letter-spacing:.5px; }
.rnk-controls-wrap{ position: sticky; top: 0; z-index: 10; }

.kpi-card{ border-left: 6px solid transparent; }
.kpi-label{ color: var(--muted); font-size:.9rem; }
.kpi-value{ font-weight:800; transition: transform .3s ease; }
.kpi-card:hover .kpi-value{ transform: scale(1.03); }
.rank-chip{ display:inline-block; padding:.35rem .6rem; border-radius: 9999px; font-weight:700; }
.rank-1{ background:var(--k1); color:#fde68a; }
.rank-2{ background:var(--k2); color:#c7d2fe; }
.rank-3{ background:var(--k3); color:#fde68a; }
.rank-4,.rank-5{ background:var(--k45); color:#e5e7eb; }

.badge-pass{ background:#064e3b; color:#ecfdf5; padding:.2rem .5rem; border-radius:9999px; font-weight:7E00; }
.badge-fail{ background:#7f1d1d; color:#fee2e2; padding:.2rem .5rem; border-radius:9999px; font-weight:700; }

.bullet{ margin:0; padding-left: 1rem; }
.bullet li{ margin:.35rem 0; }

.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td,
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th{
  border-color:#334155 !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td{
  background:#0b1220 !important;
}
"""

def themed_style_block(theme: str):
    css = PAGE_CSS_DARK if theme == "dark" else PAGE_CSS_LIGHT
    return dcc.Markdown(f"<style>{css}</style>", dangerously_allow_html=True)


# ==================== Layout ====================

layout = dbc.Container([
    # Theme CSS injector (updated by callback)
    html.Div(id="theme-style"),

    # Bootstrap Icons (for bi- classes)
    html.Link(rel="stylesheet",
              href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"),

    # Title
    html.Div([
        html.H3(["🏆 Class & Section Ranking"], className="rnk-title text-center fw-bold mb-2"),
        html.P("Track class-wide and section-wise performance at a glance.",
               className="text-center text-muted mb-4")
    ], className="rnk-wrap mb-3 rnk-card p-3"),

    # Controls (sticky)
    html.Div(
        dbc.Card(dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Dropdown(
                    id="filter-dropdown",
                    options=[
                        {"label": "All Students", "value": "ALL"},
                        {"label": "Passed Students", "value": "PASS"},
                        {"label": "Failed Students", "value": "FAIL"},
                    ],
                    value="ALL", clearable=False, className="shadow-sm"
                ), md=3, xs=12),

                dbc.Col(dcc.Dropdown(
                    id="section-dropdown",
                    options=[{"label": "All Sections", "value": "ALL"}],
                    value="ALL", clearable=False, className="shadow-sm"
                ), md=3, xs=12),

                dbc.Col(
                    dbc.InputGroup([
                        dbc.InputGroupText(html.I(className="bi bi-search")),
                        dbc.Input(id="search-input",
                                  placeholder="Search by Student ID / Name / Section…",
                                  type="text")
                    ], className="shadow-sm"),
                md=4, xs=12),

                dbc.Col(
                    dbc.ButtonGroup([
                        dbc.Button("Reset", id="reset-btn", color="secondary", outline=True, className="me-1"),
                        dbc.Button("Export CSV", id="export-csv", color="primary", outline=True, className="me-1"),
                        dbc.Button("Export Excel", id="export-xlsx", color="success", outline=True),
                    ], className="w-100 d-flex justify-content-end"),
                md=2, xs=12),
            ], className="g-2 rnk-controls"),

            # Theme toggle row
            dbc.Row([
                dbc.Col(
                    dbc.Checklist(
                        id="theme-toggle",
                        options=[{"label": "🌙 Dark Mode", "value": "dark"}],
                        value=[],
                        switch=True,
                    ), width="auto"
                )
            ], className="mt-2")
        ]), className="rnk-card"),
        className="rnk-controls-wrap mb-3"
    ),

    # KPIs
    dbc.Card(dbc.CardBody(
        html.Div(dbc.Spinner(html.Div(id='kpi-cards'), color="primary"), className="py-1")
    ), className="rnk-card mb-3"),

    # Overview row: Top5 + Section-wise toppers + Bottom 5
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(
            html.Div([
                html.Div(
                    [html.H6("🥇 Top 5 Overall", className="fw-bold mb-2 me-auto")],
                    className="d-flex align-items-center"
                ),
                html.Div(id="overall-top5", className="mb-1")
            ])
        ), className="rnk-card"), md=4, xs=12),

        dbc.Col(dbc.Card(dbc.CardBody(
            html.Div(id="section-toppers")
        ), className="rnk-card"), md=4, xs=12),

        dbc.Col(dbc.Card(dbc.CardBody(
            html.Div(id="bottom-five")
        ), className="rnk-card"), md=4, xs=12),
    ], className="g-3 mb-3"),

    # DataTable
    dbc.Card(dbc.CardBody([
        html.H6([html.I(className="bi bi-clipboard2-data me-2 text-primary"), "Class Ranking Table"],
                className="fw-bold mb-3"),
        dash_table.DataTable(
            id='ranking-table',
            columns=[], data=[],
            page_size=25,
            sort_action='native',
            filter_action='none',
            style_table={'height': '620px', 'overflowY': 'auto'},
            fixed_rows={'headers': True},
            style_cell={
                'textAlign': 'center',
                'fontFamily': 'Inter, Segoe UI, system-ui, -apple-system, Arial',
                'fontSize': 13,
                'padding': '8px',
                'minWidth': '80px', 'width': '80px', 'maxWidth': '300px',
                'whiteSpace': 'normal'
            },
            style_header={
                'backgroundColor': '#1f2937',
                'color': 'white',
                'fontWeight': '700',
                'padding': '10px',
                'border': '0'
            },
            style_data_conditional=[
                {'if': {'row_index': 'odd'}, 'backgroundColor': '#f9fafb'},
                {'if': {'filter_query': '{Overall_Result} = "F"'}, 'backgroundColor': '#ffe4e6'},
                {'if': {'filter_query': '{Class_Rank} = 1'}, 'backgroundColor': '#fff8dc', 'fontWeight': 'bold'},
                {'if': {'filter_query': '{Class_Rank} = 2'}, 'backgroundColor': '#f3f4f6', 'fontWeight': 'bold'},
                {'if': {'filter_query': '{Class_Rank} = 3'}, 'backgroundColor': '#fff4e6', 'fontWeight': 'bold'},
            ],
            row_selectable=False,
            cell_selectable=True,
            style_as_list_view=True
        )
    ]), className="rnk-card"),

    # Student modal
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Student Profile")),
        dbc.ModalBody(id="student-modal-body"),
        dbc.ModalFooter(dbc.Button("Close", id="close-modal", className="ms-auto", color="secondary"))
    ], id="student-modal", is_open=False, size="lg"),

    # Hidden downloads
    dcc.Download(id="download-csv"),
    dcc.Download(id="download-xlsx"),

    # Stores (provided by app.py / Overview)
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session'),
], fluid=True, className="pb-4")


# ==================== Theme callback ====================

@callback(
    Output("theme-style", "children"),
    Input("theme-toggle", "value")
)
def apply_theme(toggle_values):
    theme = "dark" if ("dark" in (toggle_values or [])) else "light"
    return themed_style_block(theme)

@callback(Output('section-dropdown', 'options'), Input('stored-data', 'data'), State('section-data', 'data'))
def update_section_options(json_data, section_ranges):
    if not json_data: return [{"label": "All Sections", "value": "ALL"}]
    df = pd.read_json(StringIO(json_data), orient='split') # FIX: StringIO
    df = _normalize_df(df, section_ranges)
    sections = sorted(df['Section'].dropna().unique())
    return [{"label": "All Sections", "value": "ALL"}] + [{"label": s, "value": s} for s in sections]

# ==================== Callbacks ====================

# Section dropdown options
@callback(
    Output('section-dropdown', 'options'),
    Input('stored-data', 'data'),
    State('section-data', 'data')
)
def generate_credit_panel(json_data, ranking_type, section_ranges):
    if ranking_type != 'sgpa': return html.Div()
    if not json_data: return ""
    
    df = pd.read_json(StringIO(json_data), orient='split') # FIX: StringIO
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
    Output('filter-dropdown', 'value'),
    Output('section-dropdown', 'value'),
    Output('search-input', 'value'),
    Input('reset-btn', 'n_clicks'),
    prevent_initial_call=True
)
def reset_filters(n_clicks):
    """Reset all filter controls to defaults."""
    return "ALL", "ALL", ""

# Main build: KPIs, Top5, toppers, bottom, table
@callback(
    Output('kpi-cards', 'children'),
    Output('overall-top5', 'children'),
    Output('section-toppers', 'children'),
    Output('bottom-five', 'children'),
    Output('ranking-table', 'columns'),
    Output('ranking-table', 'data'),
    Input('filter-dropdown', 'value'),
    Input('section-dropdown', 'value'),
    Input('search-input', 'value'),
    State('stored-data', 'data'),
    State('section-data', 'data')
)
def build_views(filter_value, section_value, search_value, json_data, section_ranges):
    """
    Build KPIs, Top 5 overall (always show 1–5), Section-wise toppers, Bottom 5, and table.
    KPI behavior:
      * ALL  -> show Total, Passed, Failed, Pass %
      * PASS -> show Total (in view) and Passed only
      * FAIL -> show Total (in view) and Failed only
    """
    if not json_data:
        empty = html.P("Upload data on Overview page.", className="text-muted")
        return empty, html.Div(), html.Div(), html.Div(), [], []

    # Cached normalized base
    base_full = _prepare_base(json_data, _section_key(section_ranges)).copy()
    base_pre = base_full.copy()
    if sgpa_json:
        try:
            sgpa_df = pd.read_json(StringIO(sgpa_json), orient='split') # FIX: StringIO
            base_full = base_full.merge(sgpa_df, how='left', on='Student_ID')
            if 'Section' not in base_full.columns or base_full['Section'].isna().all():
                if 'Section' in base_pre.columns: base_full['Section'] = base_pre['Section']
        except: base_full = base_pre.copy()

    # ---------- Apply Pass/Fail & Section filters to get "scope" ----------
    scope = base_full.copy()
    if filter_value == "PASS":
        scope = scope[scope["Overall_Result"] == "P"]
    elif filter_value == "FAIL":
        scope = scope[scope["Overall_Result"] == "F"]

    if section_value != "ALL":
        scope = scope[scope["Section"] == section_value]

    # ---------- Rankings ----------
    scope['Class_Rank'] = scope[scope['Overall_Result'] == 'P']['Total_Marks'].rank(
        method='min', ascending=False
    ).astype('Int64')

    scope['Section_Rank'] = (
        scope.groupby('Section')['Total_Marks']
        .rank(method='min', ascending=False)
        .astype('Int64')
    )

    # ---------- KPIs ----------
    total_in_scope = len(scope)
    passed_in_scope = (scope['Overall_Result'] == 'P').sum()
    failed_in_scope = (scope['Overall_Result'] == 'F').sum()
    pass_pct_scope = round((passed_in_scope / total_in_scope) * 100, 2) if total_in_scope else 0

    if filter_value == "ALL":
        kpi_items = [
            {"label": "Total Students", "icon": "bi-people-fill", "value": total_in_scope,
             "color": "#3b82f6", "bg": "#eff6ff"},
            {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed_in_scope,
             "color": "#10b981", "bg": "#ecfdf5"},
            {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed_in_scope,
             "color": "#ef4444", "bg": "#fef2f2"},
            {"label": "Pass %", "icon": "bi-bar-chart-fill", "value": f"{pass_pct_scope}%",
             "color": "#f59e0b", "bg": "#fffbeb"},
        ]
        col_md = 3
    elif filter_value == "PASS":
        kpi_items = [
            {"label": "Total (in view)", "icon": "bi-people-fill", "value": total_in_scope,
             "color": "#3b82f6", "bg": "#eff6ff"},
            {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed_in_scope,
             "color": "#10b981", "bg": "#ecfdf5"},
        ]
        col_md = 6
    else:  # FAIL
        kpi_items = [
            {"label": "Total (in view)", "icon": "bi-people-fill", "value": total_in_scope,
             "color": "#3b82f6", "bg": "#eff6ff"},
            {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed_in_scope,
             "color": "#ef4444", "bg": "#fef2f2"},
        ]
        col_md = 6

    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div([
                html.I(className=f"bi {item['icon']} me-2", style={"fontSize": "1.5rem", "color": item["color"]}),
                html.Span(item["label"], className="kpi-label")
            ], className="d-flex align-items-center justify-content-center"),
            html.Div(str(item["value"]), className="kpi-value display-6 text-center",
                     style={"color": item["color"], "lineHeight": "1.1"})
        ]), className="kpi-card", style={
            "backgroundColor": item["bg"],
            "borderLeftColor": item["color"]
        }), md=col_md, xs=6, className="mb-2")
        for item in kpi_items
    ], className="g-3")

    # ---------- Top 5 Overall (ALWAYS show 1..5; ignore search, but respect filters) ----------
    if len(scope):
        top5 = scope.sort_values('Total_Marks', ascending=False).head(5)
        chips = []
        for i, (_, r) in enumerate(top5.iterrows(), start=1):
            rank_cls = f"rank-chip rank-{i if i<=5 else 5}"
            res_badge = html.Span("P", className="badge-pass") if r['Overall_Result'] == 'P' else html.Span("F", className="badge-fail")
            chips.append(
                html.Li(
                    html.Span([
                        html.Span(f"#{i}", className=rank_cls),
                        html.Span(f"  {r['Student_ID']} (Sec {r['Section']}) — {int(r['Total_Marks'])}  "),
                        html.Span(" "), res_badge
                    ]),
                    className=""
                )
            )
        top5_children = html.Ul(chips, className="bullet mb-0")
    else:
        top5_children = html.P("No records in view.", className="text-muted mb-0")

    # ---------- Section-wise Toppers ----------
    if len(scope):
        cards = []
        by_sec = scope.groupby('Section', dropna=False)
        for sec, g in by_sec:
            if len(g) == 0:
                continue
            ridx = g['Total_Marks'].idxmax()
            r = scope.loc[ridx]
            cards.append(
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.Div([
                        html.I(className="bi bi-award-fill me-2", style={"color": "#8b5cf6"}),
                        html.Strong(f"Section {r['Section']} Topper")
                    ], className="mb-2 d-flex align-items-center"),
                    html.Div(f"Student ID: {r['Student_ID']}"),
                    html.Div(f"Total: {int(r['Total_Marks'])}"),
                    html.Div(f"Class Rank: {r['Class_Rank'] if pd.notna(r['Class_Rank']) else '—'}"),
                ]), className="rnk-card"), md=12, xs=12, className="mb-2")
            )
        section_toppers_children = [html.H6("🏆 Section-wise Toppers", className="fw-bold mb-2"), dbc.Row(cards, className="g-2")] if cards else html.P("No records.", className="text-muted mb-0")
    else:
        section_toppers_children = html.P("No records in view.", className="text-muted mb-0")

    # ---------- Bottom 5 (soft red background hint) ----------
    if len(scope):
        bottom = scope.sort_values('Total_Marks', ascending=True).head(5)
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
            
            # Format ID and Section nicely
            sec_txt = f" (Sec {r.get('Section')})" if r.get('Section') else ""
            
            items.append(html.Li([
                # Rank number
                html.Span(f"#{i}", className="fw-bold me-2 text-muted", style={"minWidth":"25px"}),
                # ID + Section
                html.Span([html.Strong(r.get('Student_ID')), html.Span(sec_txt, className="text-muted small")]),
                html.Span("—", className="mx-2 text-muted"),
                # Marks/SGPA
                html.Span(f"{val}", className="fw-bold me-2"),
                # Pass/Fail Badge
                html.Span(res_txt[0], className=res_cls) # Just P or F
            ], className="d-flex align-items-center mb-2 small"))
        return html.Ul(items, className="list-unstyled mb-0")

    sort_col = 'SGPA' if (rank_type == 'sgpa' and 'SGPA' in scope.columns) else 'Total_Marks'
    top5_html = make_list(scope, sort_col, False)
    bot_html = make_list(scope, sort_col, True)

    # ---------- Section-wise Toppers (Card Style) ----------
    sec_cards = []
    if 'Section' in scope.columns:
        for sec, g in sorted(scope.groupby('Section')):
            if g.empty: continue
            ridx = g[sort_col].idxmax()
            r = g.loc[ridx]
            
            # FIX 1: CRITICAL FIX FOR VALUE ERROR
            # Get rank column name based on type
            rank_col_name = 'SGPA_Class_Rank' if rank_type=='sgpa' else 'Class_Rank'
            
            # Safely get the value
            rank_val = r.get(rank_col_name)
            
            # Safely convert to int ONLY if numeric
            if pd.notna(rank_val) and str(rank_val).replace('.', '', 1).isdigit():
                rank_display = str(int(rank_val))
            else:
                rank_display = "-"
            
            card = html.Div([
                html.H6([
                    html.I(className="bi bi-trophy-fill me-2", style={"color":"#8b5cf6"}),
                    f"Section {sec} Topper"
                ], className="fw-bold mb-2", style={"color": "#4338ca", "fontSize": "0.95rem"}),
                
                html.Div([
                    html.Div(f"Student ID: {r.get('Student_ID')}", className="mb-1 text-muted small"),
                    html.Div([
                        html.Span(f"{'SGPA' if rank_type=='sgpa' else 'Total'}: ", className="text-muted small"),
                        html.Span(f"{r.get(sort_col)}", className="fw-bold text-dark")
                    ], className="mb-1"),
                    html.Div([
                        html.Span("Class Rank: ", className="text-muted small"),
                        html.Span(rank_display, className="fw-bold text-dark")
                    ])
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
        bottom_children = html.P("No records in view.", className="text-muted mb-0")

    # ---------- Table (search DOES apply here) ----------
    table_df = scope.copy()
    if search_value:
        s = str(search_value).strip()
        mask = (
            table_df['Student_ID'].astype(str).str.contains(s, case=False, na=False) |
            table_df['Name'].astype(str).str.contains(s, case=False, na=False) |
            table_df['Section'].astype(str).str.contains(s, case=False, na=False)
        )
        table_df = table_df[mask]

    # push fails to bottom for readability
    table_df['__rank_sort'] = table_df['Class_Rank'].fillna(10**9)
    table_df = table_df.sort_values(['__rank_sort', 'Total_Marks'], ascending=[True, False]).drop(columns='__rank_sort')

    display_cols = ['Class_Rank', 'Section_Rank', 'Student_ID', 'Name', 'Section', 'Total_Marks', 'Overall_Result']
    table_cols = [{"name": c.replace("_", " "), "id": c} for c in display_cols if c in table_df.columns]
    table_data = table_df[[c for c in display_cols if c in table_df.columns]].to_dict('records')


    return kpi_cards, top5_children, section_toppers_children, bottom_children, table_cols, table_data


# Open modal on cell click
@callback(
    Output("student-modal", "is_open"),
    Output("student-modal-body", "children"),
    Input("ranking-table", "active_cell"),
    State("ranking-table", "derived_viewport_data"),
    Input("close-modal", "n_clicks"),
    prevent_initial_call=True
)
def show_student_modal(active_cell, view_data, close_click):
    """
    Show modal with basic student details when user clicks any cell.
    Uses derived_viewport_data so sorting/pagination is respected.
    """
    trigger = dash.ctx.triggered_id
    if trigger == "close-modal":
        return False, no_update

    if not active_cell or not view_data:
        return no_update, no_update

    row = view_data[active_cell['row']]
    body = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Identity", className="text-muted mb-2"),
            html.Div(f"Student ID: {row.get('Student_ID', '')}"),
            html.Div(f"Name: {row.get('Name', '')}"),
            html.Div(f"Section: {row.get('Section', '')}"),
            html.Div([
                "Result: ",
                html.Span("P", className="badge-pass") if row.get('Overall_Result') == 'P'
                else html.Span("F", className="badge-fail")
            ])
        ]), className="rnk-card border-0"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Performance", className="text-muted mb-2"),
            html.Div(f"Total Marks: {row.get('Total_Marks', '')}"),
            html.Div(f"Class Rank: {row.get('Class_Rank', '—')}"),
            html.Div(f"Section Rank: {row.get('Section_Rank', '—')}"),
        ]), className="rnk-card border-0"), md=6),
    ], className="g-3")
    return True, body


# ==================== Exports (no timestamp; fixed Excel) ====================

@callback(
    Output("download-csv", "data"),
    Input("export-csv", "n_clicks"),
    State('ranking-table', 'data'),
    prevent_initial_call=True
)
def export_csv(n, table_data):
    """Export the visible table to CSV."""
    if not table_data:
        return no_update
    df = pd.DataFrame(table_data)
    return dcc.send_data_frame(df.to_csv, "ranking.csv", index=False)

@callback(
    Output("download-xlsx", "data"),
    Input("export-xlsx", "n_clicks"),
    State('ranking-table', 'data'),
    prevent_initial_call=True
)
def export_xlsx(n, table_data):
    """Export the visible table to Excel (no timestamp, light-only)."""
    if not table_data:
        return no_update
    df = pd.DataFrame(table_data)
    return dcc.send_data_frame(df.to_excel, "ranking.xlsx", sheet_name="Ranking", index=False)