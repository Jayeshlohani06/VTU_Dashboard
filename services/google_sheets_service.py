import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import os

SHEET_URL = "https://docs.google.com/spreadsheets/d/1oVCBqYIUlZItZvG1sTWH5wuJ5j4smI2Mmis8xS8l65w"

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_credentials():
    # Priority 1: Environment variable (for Render / production)
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        return ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPES)
    # Priority 2: Local file (for development)
    return ServiceAccountCredentials.from_json_keyfile_name(
        "service_account.json", SCOPES
    )


def connect_feedback_sheet():
    creds = _get_credentials()
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1
    return sheet


def save_feedback(name, email, feedback_type, message, rating="N/A"):

    sheet = connect_feedback_sheet()

    sheet.append_row([
        str(datetime.now()),
        name,
        email,
        feedback_type,
        message,
        rating,
    ])