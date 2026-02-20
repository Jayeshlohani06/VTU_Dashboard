from flask_caching import Cache

# Define cache here to avoid circular imports.
# We will init_app(server) in app.py
cache = Cache(config={
    'CACHE_TYPE': 'FileSystemCache',
    'CACHE_DIR': 'cache-directory',
    'CACHE_DEFAULT_TIMEOUT': 3600,
    'CACHE_THRESHOLD': 50
})
