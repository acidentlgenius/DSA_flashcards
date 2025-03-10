from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache

# Configure SQLAlchemy with connection pooling settings
db = SQLAlchemy(engine_options={
    'pool_pre_ping': True,  # Verify connections before use
    'pool_recycle': 3600,   # Recycle connections after 1 hour
    'pool_timeout': 30,     # Connection timeout after 30 seconds
    'max_overflow': 10,     # Maximum number of connections to overflow
    'pool_size': 10         # Increased base pool size from 5 to 10
})

# Improved caching configuration
cache = Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 600,  # Increased from 300 to 600 seconds (10 minutes)
    'CACHE_THRESHOLD': 1000,       # Maximum number of items the cache will store
    'CACHE_KEY_PREFIX': 'dsa_flashcards_'
})
