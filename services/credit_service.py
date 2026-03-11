import json
import os
import re

# Use absolute path based on this file's location so it works regardless of CWD
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_PATH = os.path.join(_PROJECT_ROOT, "utils", "credit_database")


def load_credit_map(scheme, semester, cycle=None):
    """
    Load credit JSON file for given scheme, semester, and optional cycle.
    For 2025 scheme sem1, cycle can be 'physics' or 'chemistry'.
    """
    if cycle:
        cycle_path = os.path.join(BASE_PATH, f"{scheme}_scheme", f"sem{semester}_{cycle}.json")
        if os.path.exists(cycle_path):
            with open(cycle_path, "r") as f:
                data = json.load(f)
                print(f"[CreditService] Loaded {len(data)} credits from sem{semester}_{cycle}.json")
                return data
            
    path = os.path.join(BASE_PATH, f"{scheme}_scheme", f"sem{semester}.json")

    if not os.path.exists(path):
        print(f"[CreditService] Credit file not found: {path}")
        return {}

    with open(path, "r") as f:
        data = json.load(f)
        print(f"[CreditService] Loaded {len(data)} credits from sem{semester}.json")
        return data


def extract_course_number(subject_code):
    """
    Extract numeric course number from subject code
    Example:
    BCS501 -> 501
    BECL504 -> 504
    """
    match = re.search(r"\d{3}", str(subject_code))
    return match.group() if match else None


def get_credit(subject_code, credit_map):
    """
    Return credit for a subject
    """
    number = extract_course_number(subject_code)

    if number and number in credit_map:
        return credit_map[number]

    print(f"⚠ Credit mapping missing for {subject_code}")
    return 0