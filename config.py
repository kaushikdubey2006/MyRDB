from pathlib import Path


# =========================
# MyRDB Storage Configuration
# =========================

# Size of one database page in bytes
PAGE_SIZE = 4096

# Identifies a valid MyRDB page
PAGE_MAGIC = b"MYDB"

# Current binary storage format version
FORMAT_VERSION = 1


# =========================
# Directory Configuration
# =========================

# Main directory for persistent MyRDB data
DATA_DIR = Path("data")

# Directory for database files
DATABASE_DIR = DATA_DIR / "databases"

# Directory for backup files
BACKUP_DIR = DATA_DIR / "backups"

# Directory for checkpoint files
CHECKPOINT_DIR = DATA_DIR / "checkpoints"


# =========================
# File Extensions
# =========================

# Database file extension
DATABASE_EXTENSION = ".db"

# Index file extension
INDEX_EXTENSION = ".idx"


# =========================
# WAL Configuration
# =========================

# Write-Ahead Log file
WAL_FILE = DATA_DIR / "engine.wal"

