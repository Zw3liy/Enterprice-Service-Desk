"""
autosync/config.py

Enterprise AutoSync Configuration
"""

from pathlib import Path

# ==========================================================
# Project Paths
# ==========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

AUTOSYNC_DIR = PROJECT_ROOT / "autosync"

LOG_DIR = AUTOSYNC_DIR / "logs"

LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "autosync.log"

# ==========================================================
# Git Configuration
# ==========================================================

REMOTE = "origin"

BRANCH = "feature/ticket-form-redesign"

AUTO_PULL = False

AUTO_COMMIT = True

AUTO_PUSH = True

# ==========================================================
# Watcher Configuration
# ==========================================================

WATCH_INTERVAL = 2

DEBOUNCE_SECONDS = 5

RECURSIVE = True

# ==========================================================
# Commit Messages
# ==========================================================

COMMIT_PREFIX = "AutoSync"

COMMIT_FORMAT = "{prefix} {timestamp}"

# ==========================================================
# Logging
# ==========================================================

LOG_LEVEL = "INFO"

# ==========================================================
# Ignore Patterns
# ==========================================================

IGNORE_PATTERNS = {

    ".git",

    ".venv",

    "__pycache__",

    ".pytest_cache",

    ".mypy_cache",

    ".idea",

    ".vscode",

    "node_modules",

    "dist",

    "build",

    "htmlcov",

    "staticfiles",

    "media",

    "*.pyc",

    "*.pyo",

    "*.log",

    "*.tmp",

    "*.temp",

    ".DS_Store",

    "Thumbs.db",

    "autosync/logs",

}

# ==========================================================
# Git Ignore Extensions
# ==========================================================

IGNORE_EXTENSIONS = {

    ".pyc",

    ".log",

    ".tmp",

    ".temp",

}

# ==========================================================
# Safety
# ==========================================================

DRY_RUN = False

FAIL_ON_GIT_ERROR = False

# ==========================================================
# Status
# ==========================================================

SHOW_CONSOLE_OUTPUT = True

SHOW_GIT_OUTPUT = True