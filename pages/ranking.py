import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd
import re
import numpy as np # Import numpy for pd.notna

dash.register_page(__name__, path="/ranking", name="Ranking")

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

layout = dbc.Container([
    html.H3([
        html.I(className="bi bi-trophy me-2 text-warning", style={"fontSize": "2rem"}),
        "Class & Section Ranking"
    ], className="mb-4 text-center fw-bold"),

    # Filters
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="filter-dropdown",
                options=[
                    {"label": "All Students", "value": "ALL"},
                    {"label": "Passed Students", "value": "PASS"},
                    {"label": "Failed Students", "value": "FAIL"},
                ],
                value="ALL",
                clearable=False,
                style={"width": "100%"},
                className="shadow-sm"
            ),
            md=6, xs=12
        ),
        dbc.Col(
            dcc.Dropdown(
                id="section-dropdown",
                options=[{"label": "All Sections", "value": "ALL"}],
                value="ALL",
                clearable=False,
                style={"width": "100%"},
                className="shadow-sm"
            ),
            md=6, xs=12
        )
    ], className="mb-4 justify-content-center align-items-end mx-auto", style={"maxWidth": "700px"}),

    # KPI cards + table
    dbc.Spinner(html.Div(id='ranking-content'), color="primary"),

    # Stores for data
    dcc.Store(id='stored-data', storage_type='session'),
    dcc.Store(id='section-data', storage_type='session'),
], fluid=True, className="pb-4")

@callback(
    Output('section-dropdown', 'options'),
    Input('stored-data', 'data'),
    State('section-data', 'data')
)
def update_section_options(json_data, section_ranges):
    if not json_data:
        return [{"label": "All Sections", "value": "ALL"}]
    try:
        df = pd.read_json(json_data, orient='split')
    except:
        return [{"label": "All Sections", "value": "ALL"}]
    if section_ranges:
        df['Section'] = df.iloc[:, 0].apply(lambda x: assign_section(str(x), section_ranges))
    else:
        df['Section'] = df.get('Section', "Not Assigned")
    sections = sorted(df['Section'].dropna().unique())
    options = [{"label": "All Sections", "value": "ALL"}] + [{"label": sec, "value": sec} for sec in sections]
    return options

@callback(
    Output('ranking-content', 'children'),
    Input('filter-dropdown', 'value'),
    Input('section-dropdown', 'value'),
    State('stored-data', 'data'),
    State('section-data', 'data')
)
def display_ranking(filter_value, section_value, json_data, section_ranges):
    if not json_data:
        return html.P("Please upload data and define sections on the Overview page.",
                          className="text-muted text-center mt-3")
    try:
        df = pd.read_json(json_data, orient='split')
    except:
        return html.P("⚠️ Error reading data. Please re-upload.", className="text-center text-danger")
    if df.empty:
        return html.P("No data available.", className="text-center text-muted")

    df.rename(columns={df.columns[0]: 'Student_ID'}, inplace=True)
    meta_col = 'Student_ID'

    if section_ranges:
        df['Section'] = df[meta_col].apply(lambda x: assign_section(str(x), section_ranges))
    else:
        df['Section'] = df.get('Section', "Not Assigned")

    total_cols = [c for c in df.columns if 'Total' in c or 'Marks' in c or 'Score' in c]
    df[total_cols] = df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    df['Total_Marks'] = df[total_cols].sum(axis=1) if total_cols else 0

    result_cols = [c for c in df.columns if 'Result' in c]
    if result_cols:
        df['Overall_Result'] = df[result_cols].apply(
            lambda row: 'P' if all(str(v).strip().upper() == 'P' for v in row if pd.notna(v)) else 'F', axis=1)
    else:
        pass_mark = 18
        df['Overall_Result'] = df.apply(
            lambda row: 'F' if any(row[c] < pass_mark for c in total_cols) else 'P', axis=1
        )

    # Apply filters
    df_filtered = df.copy()
    if filter_value == "PASS":
        df_filtered = df_filtered[df_filtered["Overall_Result"] == "P"]
    elif filter_value == "FAIL":
        df_filtered = df_filtered[df_filtered["Overall_Result"] == "F"]
    if section_value != "ALL":
        df_filtered = df_filtered[df_filtered["Section"] == section_value]

    # Rankings
    df_filtered['Class_Rank'] = df_filtered[df_filtered['Overall_Result'] == 'P']['Total_Marks'].rank(method='min', ascending=False).astype('Int64')
    if 'Section' in df_filtered.columns:
        df_filtered['Section_Rank'] = (
            df_filtered.groupby('Section')['Total_Marks']
            .rank(method='min', ascending=False)
            .astype('Int64')
        )
    else:
        df_filtered['Section_Rank'] = None
    df_filtered['Class_Rank_Sort'] = df_filtered['Class_Rank'].fillna(9999)  # Failed at bottom
    df_filtered = df_filtered.sort_values(by='Class_Rank_Sort', ascending=True).drop(columns=['Class_Rank_Sort'])

    # KPI metrics/soft backgrounds/icons
    total_students = len(df_filtered)
    passed_students = (df_filtered['Overall_Result'] == 'P').sum()
    failed_students = (df_filtered['Overall_Result'] == 'F').sum()
    pass_percentage = round((passed_students / total_students) * 100, 2) if total_students else 0
    kpi_items = [
        {"label": "Total Students", "icon": "bi-people-fill", "value": total_students, "color": "#60a5fa", "bg": "#eff6ff"},
        {"label": "Passed", "icon": "bi-patch-check-fill", "value": passed_students, "color": "#34d399", "bg": "#ecfdf5"},
        {"label": "Failed", "icon": "bi-x-octagon-fill", "value": failed_students, "color": "#a15353ff", "bg": "#fef2f2"},
        {"label": "Pass %", "icon": "bi-bar-chart-fill", "value": f"{pass_percentage}%", "color": "#fbbe24c9", "bg": "#fffceb2d"}
    ]

    kpi_cards = dbc.Row([dbc.Col(
        dbc.Card(
            dbc.CardBody([
                html.Div([
                    html.I(className=f"bi {item['icon']} me-2", style={"fontSize": "2rem", "color": item["color"]}),
                    html.H6(item["label"], className="text-muted mb-0"),
                ], className="mb-1"),
                html.H2(item["value"], className="fw-bold", style={"color": item["color"], "transition": "all 0.5s"}),
            ]),
            style={
                "backgroundColor": item["bg"],
                "borderLeft": f"5px solid {item['color']}",
                "borderRadius": "12px",
                "boxShadow": "0 6px 20px 0 rgba(32,36,54,0.07)",
                "textAlign": "center",
                "padding": "17px",
                "transition": "all 0.6s"
            }
        ), md=3, xs=6, className="mb-2") for item in kpi_items
    ], className="mb-4 g-3 justify-content-center align-items-stretch")

    display_cols = ['Class_Rank', 'Section_Rank', meta_col, 'Section', 'Total_Marks', 'Overall_Result']
    display_cols = [col for col in display_cols if col in df_filtered.columns]

    # --- CORRECTED LOGIC FOR ROW STYLING ---
    table_rows = []
    for _, row in df_filtered.iterrows():
        row_class = ""  # Default row class
        style = {}      # Default style
        
        if row['Overall_Result'] == 'F':
            row_class = "table-danger"  # Use Bootstrap's built-in class prop for rows
            style = {'fontWeight': 'bold'}
        elif pd.notna(row['Class_Rank']) and row['Class_Rank'] <= 3:
            row_class = "table-warning" # Use Bootstrap's built-in class prop for rows
            style = {'fontWeight': 'bold'}
            
        table_rows.append(html.Tr([html.Td(row[col]) for col in display_cols], 
                                 className=row_class, 
                                 style=style))
    # -------------------------------------------

    table = dbc.Table(
        [html.Thead(html.Tr([html.Th(col.replace("_", " ")) for col in display_cols]))] +
        [html.Tbody(table_rows)],
        striped=True, bordered=True, hover=True, responsive=True,
        className="shadow-sm text-center align-middle table-lg"
    )

    return dbc.Container([
        kpi_cards,
        html.H5("📋 Class Ranking Table", className="text-center mb-3 fw-bold"),
        table
    ], fluid=True, style={"maxWidth": "1000px"})

