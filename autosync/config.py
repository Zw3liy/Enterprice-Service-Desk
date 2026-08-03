"""
autosync/config.py

Enterprise Configuration System

Part 1/3

Provides:
- Global configuration model
- Default settings
- Environment variable support
- Path management
- Configuration validation

Used by:
- engine.py
- scanner.py
- sync_engine.py
- backup.py
- logger.py
- utils.py

Author:
Enterprise AutoSync System
"""

from __future__ import annotations

import os

from dataclasses import (
    dataclass,
    field,
)

from pathlib import Path

from typing import (
    Dict,
    List,
    Optional,
    Any,
)


# ============================================================
# APPLICATION CONSTANTS
# ============================================================

APP_NAME = "AutoSync"

APP_VERSION = "1.0.0"

CONFIG_FILENAME = "autosync.json"

ENV_PREFIX = "AUTOSYNC_"


# ============================================================
# DEFAULT DIRECTORIES
# ============================================================

DEFAULT_CONFIG_DIRECTORY = Path.home() / ".autosync"

DEFAULT_LOG_DIRECTORY = DEFAULT_CONFIG_DIRECTORY / "logs"

DEFAULT_BACKUP_DIRECTORY = DEFAULT_CONFIG_DIRECTORY / "backups"

DEFAULT_STATE_DIRECTORY = DEFAULT_CONFIG_DIRECTORY / "state"

DEFAULT_CACHE_DIRECTORY = DEFAULT_CONFIG_DIRECTORY / "cache"


# ============================================================
# DEFAULT CONFIGURATION
# ============================================================

DEFAULT_SCAN_INTERVAL = 60

DEFAULT_HASH_ALGORITHM = "sha256"

DEFAULT_ENCODING = "utf-8"

DEFAULT_LOG_LEVEL = "INFO"

DEFAULT_MAX_LOG_SIZE = 10 * 1024 * 1024

DEFAULT_LOG_BACKUPS = 10

DEFAULT_BACKUP_RETENTION = 30

DEFAULT_MAX_WORKERS = 4

DEFAULT_VERIFY_AFTER_SYNC = True

DEFAULT_FOLLOW_SYMLINKS = False

DEFAULT_DELETE_ORPHANS = False

DEFAULT_DRY_RUN = False

DEFAULT_IGNORE_HIDDEN = True


# ============================================================
# DEFAULT IGNORE PATTERNS
# ============================================================

DEFAULT_IGNORE_PATTERNS = [

    ".git",

    "__pycache__",

    ".pytest_cache",

    ".mypy_cache",

    ".venv",

    "venv",

    "node_modules",

    ".idea",

    ".vscode",

    "*.pyc",

    "*.pyo",

    "*.tmp",

    "*.log",

]


# ============================================================
# CONFIGURATION MODEL
# ============================================================

@dataclass
class AutoSyncConfig:
    """
    Enterprise AutoSync configuration.

    This object represents the entire runtime
    configuration used throughout the application.
    """

    source_directory: Optional[Path] = None

    destination_directory: Optional[Path] = None

    config_directory: Path = DEFAULT_CONFIG_DIRECTORY

    log_directory: Path = DEFAULT_LOG_DIRECTORY

    backup_directory: Path = DEFAULT_BACKUP_DIRECTORY

    state_directory: Path = DEFAULT_STATE_DIRECTORY

    cache_directory: Path = DEFAULT_CACHE_DIRECTORY

    log_level: str = DEFAULT_LOG_LEVEL

    max_log_size: int = DEFAULT_MAX_LOG_SIZE

    log_backups: int = DEFAULT_LOG_BACKUPS

    scan_interval: int = DEFAULT_SCAN_INTERVAL

    hash_algorithm: str = DEFAULT_HASH_ALGORITHM

    encoding: str = DEFAULT_ENCODING

    verify_after_sync: bool = DEFAULT_VERIFY_AFTER_SYNC

    follow_symlinks: bool = DEFAULT_FOLLOW_SYMLINKS

    delete_orphans: bool = DEFAULT_DELETE_ORPHANS

    dry_run: bool = DEFAULT_DRY_RUN

    ignore_hidden: bool = DEFAULT_IGNORE_HIDDEN

    backup_retention_days: int = DEFAULT_BACKUP_RETENTION

    max_workers: int = DEFAULT_MAX_WORKERS

    ignore_patterns: List[str] = field(
        default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS)
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================
# DIRECTORY INITIALIZATION
# ============================================================

def ensure_directories(
    config: AutoSyncConfig,
) -> None:
    """
    Ensure all required application
    directories exist.
    """

    directories = [

        config.config_directory,

        config.log_directory,

        config.backup_directory,

        config.state_directory,

        config.cache_directory,

    ]


    for directory in directories:

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================
# ENVIRONMENT SUPPORT
# ============================================================

def env(
    key: str,
    default: Optional[str] = None,
) -> Optional[str]:
    """
    Read environment variable.

    Example:

        AUTOSYNC_LOG_LEVEL

        AUTOSYNC_SCAN_INTERVAL
    """

    return os.getenv(
        ENV_PREFIX + key.upper(),
        default,
    )


# ============================================================
# CONFIGURATION VALIDATION
# ============================================================

def validate_config(
    config: AutoSyncConfig,
) -> List[str]:
    """
    Validate configuration.

    Returns:
        List of validation errors.
    """

    errors: List[str] = []


    if config.scan_interval <= 0:

        errors.append(
            "scan_interval must be greater than zero."
        )


    if config.max_workers <= 0:

        errors.append(
            "max_workers must be greater than zero."
        )


    if config.max_log_size <= 0:

        errors.append(
            "max_log_size must be greater than zero."
        )


    if config.log_backups < 0:

        errors.append(
            "log_backups cannot be negative."
        )


    if (
        config.source_directory
        and
        not config.source_directory.exists()
    ):

        errors.append(
            f"Source directory does not exist: "
            f"{config.source_directory}"
        )


    if (
        config.destination_directory
        and
        not config.destination_directory.exists()
    ):

        errors.append(
            f"Destination directory does not exist: "
            f"{config.destination_directory}"
        )


    return errors


# ============================================================
# DEFAULT CONFIGURATION FACTORY
# ============================================================

def default_config() -> AutoSyncConfig:
    """
    Create a default AutoSync configuration.
    """

    config = AutoSyncConfig()

    ensure_directories(config)

    return config

# ============================================================
# IMPORTS REQUIRED FOR PART 2
# ============================================================

import json
from dataclasses import asdict


# ============================================================
# PATH NORMALIZATION
# ============================================================

def expand_path(
    value: Optional[str | Path],
) -> Optional[Path]:
    """
    Expand environment variables and user home.

    Examples:
        ~/project
        %USERPROFILE%\\project
        $HOME/project
    """

    if value is None:
        return None

    return Path(
        os.path.expandvars(
            os.path.expanduser(
                str(value)
            )
        )
    ).resolve()


def normalize_config_paths(
    config: AutoSyncConfig,
) -> AutoSyncConfig:
    """
    Normalize every path stored in the configuration.
    """

    config.source_directory = expand_path(
        config.source_directory
    )

    config.destination_directory = expand_path(
        config.destination_directory
    )

    config.config_directory = expand_path(
        config.config_directory
    )

    config.log_directory = expand_path(
        config.log_directory
    )

    config.backup_directory = expand_path(
        config.backup_directory
    )

    config.state_directory = expand_path(
        config.state_directory
    )

    config.cache_directory = expand_path(
        config.cache_directory
    )

    return config


# ============================================================
# SERIALIZATION
# ============================================================

def config_to_dict(
    config: AutoSyncConfig,
) -> Dict[str, Any]:
    """
    Convert configuration into a JSON-safe dictionary.
    """

    data = asdict(config)

    for key, value in list(data.items()):

        if isinstance(value, Path):
            data[key] = str(value)

    return data


def config_from_dict(
    data: Dict[str, Any],
) -> AutoSyncConfig:
    """
    Create configuration from dictionary.
    """

    config = AutoSyncConfig()

    for key, value in data.items():

        if not hasattr(config, key):
            continue

        if key.endswith("_directory"):

            value = expand_path(value)

        setattr(
            config,
            key,
            value,
        )

    return normalize_config_paths(
        config
    )


# ============================================================
# CONFIGURATION FILES
# ============================================================

def config_path(
    directory: Optional[Path] = None,
) -> Path:
    """
    Return full configuration filename.
    """

    if directory is None:

        directory = DEFAULT_CONFIG_DIRECTORY

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory / CONFIG_FILENAME


def save_config(
    config: AutoSyncConfig,
    filename: Optional[Path] = None,
) -> Path:
    """
    Save configuration to disk.
    """

    if filename is None:

        filename = config_path(
            config.config_directory
        )

    filename.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        filename,
        "w",
        encoding=DEFAULT_ENCODING,
    ) as file:

        json.dump(
            config_to_dict(config),
            file,
            indent=4,
            ensure_ascii=False,
        )

    return filename


def load_config(
    filename: Optional[Path] = None,
) -> AutoSyncConfig:
    """
    Load configuration.

    If missing, create defaults automatically.
    """

    if filename is None:

        filename = config_path()

    if not filename.exists():

        config = default_config()

        save_config(
            config,
            filename,
        )

        return config

    with open(
        filename,
        "r",
        encoding=DEFAULT_ENCODING,
    ) as file:

        data = json.load(file)

    config = config_from_dict(
        data
    )

    ensure_directories(config)

    return config


# ============================================================
# CONFIGURATION MERGING
# ============================================================

def merge_config(
    base: AutoSyncConfig,
    override: AutoSyncConfig,
) -> AutoSyncConfig:
    """
    Merge two configurations.

    Values from override replace base values.
    """

    merged = AutoSyncConfig()

    for field_name in merged.__dataclass_fields__:

        override_value = getattr(
            override,
            field_name,
        )

        base_value = getattr(
            base,
            field_name,
        )

        if override_value is not None:

            setattr(
                merged,
                field_name,
                override_value,
            )

        else:

            setattr(
                merged,
                field_name,
                base_value,
            )

    return merged


# ============================================================
# ENVIRONMENT OVERRIDES
# ============================================================

def apply_environment(
    config: AutoSyncConfig,
) -> AutoSyncConfig:
    """
    Override configuration using
    AUTOSYNC_* environment variables.
    """

    mapping = {

        "LOG_LEVEL":
            "log_level",

        "SCAN_INTERVAL":
            "scan_interval",

        "MAX_WORKERS":
            "max_workers",

        "SOURCE":
            "source_directory",

        "DESTINATION":
            "destination_directory",

        "VERIFY":
            "verify_after_sync",

        "DELETE_ORPHANS":
            "delete_orphans",

        "DRY_RUN":
            "dry_run",

    }

    for env_name, attribute in mapping.items():

        value = env(env_name)

        if value is None:
            continue

        current = getattr(
            config,
            attribute,
        )

        if isinstance(current, bool):

            value = value.lower() in (
                "1",
                "true",
                "yes",
                "on",
            )

        elif isinstance(current, int):

            value = int(value)

        elif isinstance(current, Path):

            value = expand_path(value)

        setattr(
            config,
            attribute,
            value,
        )

    return config


# ============================================================
# IMPORT / EXPORT HELPERS
# ============================================================

def export_config(
    config: AutoSyncConfig,
) -> str:
    """
    Export configuration as formatted JSON string.
    """

    return json.dumps(
        config_to_dict(config),
        indent=4,
        ensure_ascii=False,
    )


def import_config(
    payload: str,
) -> AutoSyncConfig:
    """
    Import configuration from JSON string.
    """

    return config_from_dict(
        json.loads(payload)
    )

# ============================================================
# CONFIGURATION MANAGER
# ============================================================

class ConfigManager:
    """
    Singleton configuration manager.

    Responsible for:
    - Loading configuration
    - Saving configuration
    - Runtime updates
    - Validation
    - Environment overrides
    """

    _instance = None

    def __new__(cls):

        if cls._instance is None:

            cls._instance = super().__new__(cls)

        return cls._instance


    def __init__(self):

        if getattr(self, "_initialized", False):

            return

        self._config: Optional[AutoSyncConfig] = None

        self._initialized = True


    # --------------------------------------------------------
    # Configuration Access
    # --------------------------------------------------------

    @property
    def config(self) -> AutoSyncConfig:

        if self._config is None:

            self.load()

        return self._config


    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    def load(
        self,
        filename: Optional[Path] = None,
    ) -> AutoSyncConfig:

        config = load_config(filename)

        config = apply_environment(config)

        errors = validate_config(config)

        if errors:

            raise ValueError(
                "\n".join(errors)
            )

        self._config = config

        return config


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    def save(
        self,
        filename: Optional[Path] = None,
    ) -> Path:

        if self._config is None:

            self.load()

        return save_config(
            self._config,
            filename,
        )


    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    def update(
        self,
        **kwargs,
    ) -> AutoSyncConfig:

        config = self.config

        for key, value in kwargs.items():

            if not hasattr(config, key):

                raise AttributeError(
                    f"Unknown configuration field: {key}"
                )

            setattr(
                config,
                key,
                value,
            )

        normalize_config_paths(config)

        errors = validate_config(config)

        if errors:

            raise ValueError(
                "\n".join(errors)
            )

        return config


    # --------------------------------------------------------
    # Reset
    # --------------------------------------------------------

    def reset(
        self,
    ) -> AutoSyncConfig:

        self._config = default_config()

        return self._config


    # --------------------------------------------------------
    # Reload
    # --------------------------------------------------------

    def reload(
        self,
        filename: Optional[Path] = None,
    ) -> AutoSyncConfig:

        return self.load(filename)


    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    def export(
        self,
    ) -> str:

        return export_config(
            self.config
        )


    # --------------------------------------------------------
    # Import
    # --------------------------------------------------------

    def import_json(
        self,
        payload: str,
    ) -> AutoSyncConfig:

        config = import_config(payload)

        errors = validate_config(config)

        if errors:

            raise ValueError(
                "\n".join(errors)
            )

        self._config = config

        return config


# ============================================================
# GLOBAL CONFIGURATION MANAGER
# ============================================================

config_manager = ConfigManager()


# ============================================================
# PUBLIC HELPERS
# ============================================================

def get_config() -> AutoSyncConfig:
    """
    Return active configuration.
    """

    return config_manager.config


def initialize_config(
    filename: Optional[Path] = None,
) -> AutoSyncConfig:
    """
    Initialize configuration system.
    """

    return config_manager.load(filename)


def reload_config(
    filename: Optional[Path] = None,
) -> AutoSyncConfig:
    """
    Reload configuration.
    """

    return config_manager.reload(filename)


def save_current_config() -> Path:
    """
    Save active configuration.
    """

    return config_manager.save()


def update_config(
    **kwargs,
) -> AutoSyncConfig:
    """
    Update configuration values.
    """

    return config_manager.update(
        **kwargs
    )


def reset_config() -> AutoSyncConfig:
    """
    Reset configuration to defaults.
    """

    return config_manager.reset()


# ============================================================
# MODULE EXPORTS
# ============================================================

__all__ = [

    # constants
    "APP_NAME",
    "APP_VERSION",
    "CONFIG_FILENAME",

    # configuration
    "AutoSyncConfig",

    # manager
    "ConfigManager",

    # global manager
    "config_manager",

    # helpers
    "get_config",
    "initialize_config",
    "reload_config",
    "save_current_config",
    "update_config",
    "reset_config",

    # persistence
    "load_config",
    "save_config",
    "export_config",
    "import_config",

    # validation
    "validate_config",

    # defaults
    "default_config",
]