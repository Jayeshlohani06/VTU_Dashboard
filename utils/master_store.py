# utils/master_store.py
"""
Centralized state management for cross-page data sharing.
Provides a structured store with getter/setter/clear pattern
instead of raw global variables.
"""

import threading

_lock = threading.Lock()
_store = {
    "MASTER_BRANCH_DATA": None,
}

# Backward compatibility — keep module-level attribute access working
MASTER_BRANCH_DATA = None


def get(key, default=None):
    """Thread-safe getter for a store value."""
    with _lock:
        return _store.get(key, default)


def set(key, value):
    """Thread-safe setter for a store value."""
    global MASTER_BRANCH_DATA
    with _lock:
        _store[key] = value
        # Keep backward-compatible module-level attribute in sync
        if key == "MASTER_BRANCH_DATA":
            MASTER_BRANCH_DATA = value


def clear(key=None):
    """Clear a specific key or all store data."""
    global MASTER_BRANCH_DATA
    with _lock:
        if key:
            _store[key] = None
            if key == "MASTER_BRANCH_DATA":
                MASTER_BRANCH_DATA = None
        else:
            for k in _store:
                _store[k] = None
            MASTER_BRANCH_DATA = None


def keys():
    """List all keys in the store."""
    with _lock:
        return list(_store.keys())


def summary():
    """Return a summary of what's stored (types and sizes)."""
    with _lock:
        info = {}
        for k, v in _store.items():
            if v is None:
                info[k] = "None"
            elif hasattr(v, "shape"):
                info[k] = f"DataFrame{v.shape}"
            elif isinstance(v, (list, dict)):
                info[k] = f"{type(v).__name__}[{len(v)}]"
            else:
                info[k] = type(v).__name__
        return info
