import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

SHEET_URL = "https://docs.google.com/spreadsheets/d/1oVCBqYIUlZItZvG1sTWH5wuJ5j4smI2Mmis8xS8l65w"


def connect_feedback_sheet():

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json", scope
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_url(SHEET_URL).sheet1

    return sheet


def save_feedback(name, email, feedback_type, message):

    sheet = connect_feedback_sheet()

    sheet.append_row([
        str(datetime.now()),
        name,
        email,
        feedback_type,
        message
    ])