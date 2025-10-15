# pages/ranking.py

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import pandas as pd

# Register the page
dash.register_page(__name__, path="/ranking", name="Ranking")

# ---------- Layout ----------
layout = dbc.Container([
    html.H4("🏆 Class & Section Ranking", className="mb-4 text-center"),

    # Store component to hold uploaded data
    dcc.Store(id='stored-data'),

    # Filter Dropdown
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
            ),
            md=4,
        ),
    ], justify="center", className="mb-4"),

    # KPI cards and Table
    dbc.Spinner(html.Div(id='ranking-content', className="mt-3"), color="primary"),
], fluid=True)


# ---------- Callback ----------
@callback(
    Output('ranking-content', 'children'),
    Input('filter-dropdown', 'value'),
    State('stored-data', 'data'),  # Use State, not Input
    prevent_initial_call=False
)
def display_ranking(filter_value, json_data):
    # ---------------- Handle No Data ----------------
    if not json_data:
        # Display placeholder message when no data is uploaded
        return html.Div([
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("🎓 Total Students", className="text-muted"),
                        html.H4("0", className="fw-bold text-primary")
                    ])
                ], className="shadow-sm border-0 bg-light"), md=3),

                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("✅ Passed", className="text-muted"),
                        html.H4("0", className="fw-bold text-success")
                    ])
                ], className="shadow-sm border-0 bg-light"), md=3),

                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("❌ Failed", className="text-muted"),
                        html.H4("0", className="fw-bold text-danger")
                    ])
                ], className="shadow-sm border-0 bg-light"), md=3),

                dbc.Col(dbc.Card([
                    dbc.CardBody([
                        html.H6("📈 Pass %", className="text-muted"),
                        html.H4("0%", className="fw-bold text-info")
                    ])
                ], className="shadow-sm border-0 bg-light"), md=3),
            ], className="mb-4 g-3 justify-content-center"),

            html.P(
                "Please upload data first on the Overview page.",
                className="text-muted text-center"
            )
        ])

    # ---------------- Load DataFrame ----------------
    try:
        df = pd.read_json(json_data, orient='split')
    except Exception:
        return html.P("Error reading data. Please re-upload.", className="text-center text-danger")

    if df.empty:
        return html.P("No data available.", className="text-center text-muted")

    # ---------------- Rename Student ID Column ----------------
    df.rename(columns={df.columns[0]: 'Student_ID'}, inplace=True)
    meta_col = 'Student_ID'

    # ---------------- Detect Total/Marks Columns ----------------
    total_cols = [c for c in df.columns if 'Total' in c or 'Marks' in c or 'Score' in c]
    if not total_cols:
        total_cols = df.select_dtypes(include='number').columns.tolist()
        if 'Total_Marks' in total_cols:
            total_cols.remove('Total_Marks')

    if len(total_cols) == 0:
        return html.P("No numeric marks columns found.", className="text-center text-muted")

    df[total_cols] = df[total_cols].apply(pd.to_numeric, errors='coerce').fillna(0)

    # ---------------- Compute Overall_Result ----------------
    def compute_overall(row):
        result_cols = [c for c in df.columns if 'Result' in c]
        if result_cols:
            return 'F' if any(str(row[c]).strip().upper() == 'F' for c in result_cols) else 'P'
        else:
            pass_mark = 18
            return 'F' if any(row[c] < pass_mark for c in total_cols) else 'P'

    df['Overall_Result'] = df.apply(compute_overall, axis=1)

    # ---------------- Compute Total Marks ----------------
    df['Total_Marks'] = df[total_cols].sum(axis=1)

    # ---------------- Ranking Logic ----------------
    df_pass = df[df['Overall_Result'] == 'P'].copy()
    df_fail = df[df['Overall_Result'] == 'F'].copy()

    df_pass['Class_Rank'] = df_pass['Total_Marks'].rank(method='min', ascending=False).astype(int)
    df_fail['Class_Rank'] = None

    df_combined = pd.concat([df_pass, df_fail]).reset_index(drop=True)

    df_combined['Result_Sort'] = df_combined['Overall_Result'].map({'P': 1, 'F': 2})
    df_combined = df_combined.sort_values(by=['Result_Sort', 'Total_Marks'], ascending=[True, False])
    df_combined.drop(columns=['Result_Sort'], inplace=True)

    if 'Section' in df_combined.columns:
        df_combined['Section_Rank'] = (
            df_combined.groupby('Section')['Total_Marks']
            .rank(method='min', ascending=False)
            .astype('Int64')
        )
    else:
        df_combined['Section_Rank'] = None

    # ---------------- Filtering ----------------
    df_filtered = df_combined.copy()
    if filter_value == "PASS":
        df_filtered = df_filtered[df_filtered["Overall_Result"] == "P"]
    elif filter_value == "FAIL":
        df_filtered = df_filtered[df_filtered["Overall_Result"] == "F"]

    # ---------------- KPI CALCULATIONS ----------------
    total_students = len(df_combined)
    passed_students = (df_combined['Overall_Result'] == 'P').sum()
    failed_students = (df_combined['Overall_Result'] == 'F').sum()
    pass_percentage = round((passed_students / total_students) * 100, 2) if total_students else 0

    kpi_cards = dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("🎓 Total Students", className="text-muted"),
                html.H4(f"{total_students}", className="fw-bold text-primary")
            ])
        ], className="shadow-sm border-0 bg-light"), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("✅ Passed", className="text-muted"),
                html.H4(f"{passed_students}", className="fw-bold text-success")
            ])
        ], className="shadow-sm border-0 bg-light"), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("❌ Failed", className="text-muted"),
                html.H4(f"{failed_students}", className="fw-bold text-danger")
            ])
        ], className="shadow-sm border-0 bg-light"), md=3),

        dbc.Col(dbc.Card([
            dbc.CardBody([
                html.H6("📈 Pass %", className="text-muted"),
                html.H4(f"{pass_percentage}%", className="fw-bold text-info")
            ])
        ], className="shadow-sm border-0 bg-light"), md=3),
    ], className="mb-4 g-3 justify-content-center")

    # ---------------- Table Formatting ----------------
    display_cols = ['Class_Rank', 'Section_Rank', meta_col, 'Total_Marks', 'Overall_Result']
    display_cols = [col for col in display_cols if col in df_filtered.columns]

    def style_rows(row):
        if row['Overall_Result'] == 'F':
            return {'backgroundColor': '#f8d7da', 'color': 'black', 'fontWeight': 'bold'}
        elif pd.notna(row['Class_Rank']) and row['Class_Rank'] <= 10:
            return {'backgroundColor': '#d4edda', 'color': 'black', 'fontWeight': 'bold'}
        return {}

    table_rows = []
    for _, row in df_filtered.iterrows():
        style = style_rows(row)
        table_rows.append(html.Tr([html.Td(row[col]) for col in display_cols], style=style))

    table = dbc.Table(
        [html.Thead(html.Tr([html.Th(col.replace("_", " ")) for col in display_cols]))] +
        [html.Tbody(table_rows)],
        striped=True, bordered=True, hover=True, className="shadow-sm"
    )

    return dbc.Container([
        kpi_cards,
        html.H5("📋 Class Ranking Table", className="text-center mb-3"),
        table
    ])
