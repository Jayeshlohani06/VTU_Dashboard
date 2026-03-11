from flask_caching import Cache

# Define cache here to avoid circular imports.
# We will init_app(server) in app.py
# Using SimpleCache (in-memory) instead of FileSystemCache for much faster access.
# FileSystemCache uses disk I/O (~500ms per read), SimpleCache uses RAM (~0.1ms).
cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 3600,
    'CACHE_THRESHOLD': 500
})
