from flask_sqlalchemy import SQLAlchemy

# Configure SQLAlchemy with connection pooling settings
db = SQLAlchemy(engine_options={
    'pool_pre_ping': True,  # Verify connections before use
    'pool_recycle': 3600,   # Recycle connections after 1 hour
    'pool_timeout': 30,     # Connection timeout after 30 seconds
    'max_overflow': 10,     # Maximum number of connections to overflow
    'pool_size': 5          # Base pool size
})
