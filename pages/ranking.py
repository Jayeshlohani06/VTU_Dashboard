# pages/ranking.py
# Clean, aligned, modern light-theme UI for Ranking page

import dash  # for dash.ctx in callbacks
from dash import html, dcc, Input, Output, State, callback, dash_table, no_update
import dash_bootstrap_components as dbc
import pandas as pd
import re
from functools import lru_cache
import ast  # safe parsing for section ranges

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
    """
    Cached base prep to speed up repeated interactions when filters change.
    The `section_key` must be hashable; we pass a repr string and parse safely.
    """
    df = pd.read_json(json_str, orient='split')

    # Safely parse the section ranges repr into a dict (or None)
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


# ==================== Styles (light theme only) ====================

PAGE_CSS = """
:root{
  --bg: #f5f7fb;
  --card: #ffffff;
  --text: #111827;
  --muted:#6b7280;
  --primary:#1f2937;
  --brand:#3b82f6;
  --shadow: 0 8px 24px rgba(16,24,40,.08);
}

/* page wrapper */
.rnk-wrap{
  background: var(--bg);
  padding: 18px;
  border-radius: 14px;
}

/* section cards */
.rnk-card{
  background: var(--card);
  border: 0 !important;
  border-radius: 14px !important;
  box-shadow: var(--shadow);
}

/* header */
.rnk-title{
  color: var(--primary);
  letter-spacing:.5px;
}

/* control row */
.rnk-controls .btn, .rnk-controls .form-select, .rnk-controls .form-control{
  border-radius: 10px !important;
}

/* KPI */
.kpi-card{
  border-left: 6px solid transparent;
}
.kpi-label{ color: var(--muted); font-size:.9rem; }
.kpi-value{ font-weight:800; }

/* toppers & bottom lists */
.bullet{
  margin: 0;
  padding-left: 1rem;
}
.bullet li{
  margin: .25rem 0;
}

/* datatable polish */
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner td,
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner th{
  border-color:#e5e7eb !important;
}
.dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner tr:hover td{
  background:#f8fafc !important;
}
"""


# ==================== Layout ====================

layout = dbc.Container([
    # Bootstrap Icons (for bi- classes)
    html.Link(rel="stylesheet",
              href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"),
    
    

    # Title
    html.Div([
        html.H3(["🏆 Class & Section Ranking"], className="rnk-title text-center fw-bold mb-2"),
        html.P("Track class-wide and section-wise performance at a glance.",
               className="text-center text-muted mb-4")
    ], className="rnk-wrap mb-3 rnk-card p-3"),

    # Controls
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
        ], className="g-2 rnk-controls")
    ]), className="rnk-card mb-3"),

    # KPIs
    dbc.Card(dbc.CardBody(
        html.Div(dbc.Spinner(html.Div(id='kpi-cards'), color="primary"), className="py-1")
    ), className="rnk-card mb-3"),

    # Toppers + Bottom 5
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody(
            html.Div(id="section-toppers")
        ), className="rnk-card"), md=7, xs=12),

        dbc.Col(dbc.Card(dbc.CardBody(
            html.Div(id="bottom-five")
        ), className="rnk-card"), md=5, xs=12),
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


# ==================== Callbacks ====================

# Section dropdown options
@callback(
    Output('section-dropdown', 'options'),
    Input('stored-data', 'data'),
    State('section-data', 'data')
)
def update_section_options(json_data, section_ranges):
    """Rebuild section dropdown options from current data & mapping."""
    if not json_data:
        return [{"label": "All Sections", "value": "ALL"}]
    df = pd.read_json(json_data, orient='split')
    df = _normalize_df(df, section_ranges)
    sections = sorted(df['Section'].dropna().unique())
    return [{"label": "All Sections", "value": "ALL"}] + [{"label": s, "value": s} for s in sections]

# Reset filters
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

# Main build: KPIs, toppers/bottom, table
@callback(
    Output('kpi-cards', 'children'),
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
    """Build KPIs, toppers/bottom panes, and the main ranking table."""
    if not json_data:
        return (html.P("Upload data on Overview page.", className="text-muted"),
                html.Div(), html.Div(), [], [])

    # Cached normalized base
    base = _prepare_base(json_data, _section_key(section_ranges)).copy()

    # Filter by pass/fail
    if filter_value == "PASS":
        base = base[base["Overall_Result"] == "P"]
    elif filter_value == "FAIL":
        base = base[base["Overall_Result"] == "F"]

    # Filter by section
    if section_value != "ALL":
        base = base[base["Section"] == section_value]

    # Search
    if search_value:
        s = str(search_value).strip()
        mask = (
            base['Student_ID'].astype(str).str.contains(s, case=False, na=False) |
            base['Name'].astype(str).str.contains(s, case=False, na=False) |
            base['Section'].astype(str).str.contains(s, case=False, na=False)
        )
        base = base[mask]

    # Rankings
    base['Class_Rank'] = base[base['Overall_Result'] == 'P']['Total_Marks'].rank(
        method='min', ascending=False
    ).astype('Int64')

    base['Section_Rank'] = (
        base.groupby('Section')['Total_Marks']
        .rank(method='min', ascending=False)
        .astype('Int64')
    )

    # Sort (push fails to bottom)
    base['__rank_sort'] = base['Class_Rank'].fillna(10**9)
    base = base.sort_values(['__rank_sort', 'Total_Marks'], ascending=[True, False]).drop(columns='__rank_sort')

    # KPIs
    total_students = len(base)
    passed = (base['Overall_Result'] == 'P').sum()
    failed = (base['Overall_Result'] == 'F').sum()
    pass_pct = round((passed / total_students) * 100, 2) if total_students else 0

    kpi_items = [
        {"label": "Total Students", "icon": "bi-people-fill", "value": total_students,
         "color": "#3b82f6", "bg": "#eff6ff"},
        {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed,
         "color": "#10b981", "bg": "#ecfdf5"},
        {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed,
         "color": "#ef4444", "bg": "#fef2f2"},
        {"label": "Pass %", "icon": "bi-bar-chart-fill", "value": f"{pass_pct}%",
         "color": "#f59e0b", "bg": "#fffbeb"},
    ]
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
        }), md=3, xs=6, className="mb-2")
        for item in kpi_items
    ], className="g-3")

    # Section toppers (best Total_Marks per section)
    toppers_cards = []
    if len(base):
        idx = base.groupby('Section')['Total_Marks'].idxmax()
        toppers = base.loc[idx].sort_values('Section')
        cards = []
        for _, r in toppers.iterrows():
            cards.append(
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.Div([
                        html.I(className="bi bi-award-fill me-2", style={"color": "#8b5cf6"}),
                        html.Strong(f"Section {r['Section']} Topper")
                    ], className="mb-2 d-flex align-items-center"),
                    html.Div(f"Student ID: {r['Student_ID']}"),
                    html.Div(f"Total: {int(r['Total_Marks'])}"),
                    html.Div(f"Class Rank: {r['Class_Rank'] if pd.notna(r['Class_Rank']) else '—'}"),
                ]), className="rnk-card"), md=6, xs=12, className="mb-2")
            )
        toppers_cards = [
            html.H6("🏆 Section-wise Toppers", className="fw-bold mb-3"),
            dbc.Row(cards, className="g-3")
        ]

    # Bottom 5 (by Total_Marks asc)
    bottom_div = []
    if len(base):
        bottom = base.sort_values('Total_Marks', ascending=True).head(5)
        items = [html.Li(f"{r['Student_ID']} (Sec {r['Section']}) — {int(r['Total_Marks'])}") for _, r in bottom.iterrows()]
        bottom_div = [
            html.H6("⬇️ Bottom 5 (by Total Marks)", className="fw-bold mb-3"),
            html.Ul(items, className="bullet mb-0")
        ]

    # Table columns/data
    display_cols = ['Class_Rank', 'Section_Rank', 'Student_ID', 'Name', 'Section', 'Total_Marks', 'Overall_Result']
    table_cols = [{"name": c.replace("_", " "), "id": c} for c in display_cols if c in base.columns]
    table_data = base[[c for c in display_cols if c in base.columns]].to_dict('records')

    return kpi_cards, html.Div(toppers_cards), html.Div(bottom_div), table_cols, table_data


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
        ]), className="rnk-card border-0"), md=6),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Performance", className="text-muted mb-2"),
            html.Div(f"Total Marks: {row.get('Total_Marks', '')}"),
            html.Div(f"Class Rank: {row.get('Class_Rank', '—')}"),
            html.Div(f"Section Rank: {row.get('Section_Rank', '—')}"),
            html.Div(f"Overall Result: {row.get('Overall_Result', '')}"),
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
    # Use send_data_frame with to_excel to avoid non-JSON-serializable bytes
    return dcc.send_data_frame(df.to_excel, "ranking.xlsx", sheet_name="Ranking", index=False)
