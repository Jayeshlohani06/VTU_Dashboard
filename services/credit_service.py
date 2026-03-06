import json
import os
import re
from cache_config import cache

BASE_PATH = os.path.join("utils", "credit_database")

@cache.memoize(timeout=86400) # Cache for 1 day
def load_credit_map(scheme, semester):
    """
    Load credit JSON file for given scheme and semester
    """
    path = os.path.join(BASE_PATH, f"{scheme}_scheme", f"sem{semester}.json")

    if not os.path.exists(path):
        print(f"Credit file not found: {path} - Returning empty map.")
        return {}

    with open(path, "r") as f:
        return json.load(f)


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
