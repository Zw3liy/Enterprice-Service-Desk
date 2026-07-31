"""
Enterprise Service Desk
Generator Configuration
"""

from pathlib import Path


# ======================================================
# PROJECT ROOT
# ======================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ======================================================
# LIBRARIES
# ======================================================

CODE_LIBRARY = PROJECT_ROOT / "code_library"

CSS_LIBRARY = CODE_LIBRARY / "css"

TEMPLATE_LIBRARY = CODE_LIBRARY / "templates"

JS_LIBRARY = CODE_LIBRARY / "javascript"

PYTHON_LIBRARY = CODE_LIBRARY / "python"


# ======================================================
# DESTINATIONS
# ======================================================

STATIC_DIR = PROJECT_ROOT / "static"

CSS_OUTPUT = STATIC_DIR / "css"

JS_OUTPUT = STATIC_DIR / "js"

TEMPLATE_OUTPUT = PROJECT_ROOT / "templates"


# ======================================================
# OPTIONS
# ======================================================

OVERWRITE = True

VERBOSE = True

CREATE_MISSING_DIRECTORIES = True