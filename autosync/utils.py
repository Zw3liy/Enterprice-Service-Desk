"""
autosync/utils.py

Enterprise Utility Library
Part 1/3

Core utilities:
- Imports
- Constants
- Timestamp helpers
- Path normalization
- Safe path operations
- Project path discovery

Used by:
- autosync engine
- scanner
- synchronizer
- logger
- backup manager

Author: Enterprise AutoSync System
"""

from __future__ import annotations

import os
import re
import json
import shutil
import hashlib
import subprocess

from pathlib import Path
from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    Iterable,
    Generator,
)


# ============================================================
# CONSTANTS
# ============================================================

APP_NAME = "AutoSync"

VERSION = "1.0.0"

DEFAULT_ENCODING = "utf-8"

DEFAULT_HASH_ALGORITHM = "sha256"


# Supported text file types
TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".scss",
    ".xml",
    ".ini",
    ".cfg",
}


# Files/directories normally ignored
DEFAULT_IGNORE_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    ".idea",
    ".vscode",
}


# ============================================================
# TIMESTAMP UTILITIES
# ============================================================

def utc_now() -> datetime:
    """
    Return current UTC datetime.

    Returns:
        datetime object with UTC timezone.
    """

    return datetime.now(timezone.utc)



def local_now() -> datetime:
    """
    Return current local datetime.
    """

    return datetime.now()



def timestamp(
    value: Optional[datetime] = None,
    format_string: str = "%Y-%m-%d %H:%M:%S",
) -> str:
    """
    Generate formatted timestamp.

    Args:
        value:
            Optional datetime object.

        format_string:
            Output format.

    Returns:
        Formatted timestamp string.
    """

    if value is None:
        value = utc_now()

    return value.strftime(format_string)



def iso_timestamp(
    value: Optional[datetime] = None,
) -> str:
    """
    Generate ISO 8601 timestamp.
    """

    if value is None:
        value = utc_now()

    return value.isoformat()



def unix_timestamp() -> int:
    """
    Return UNIX timestamp.
    """

    return int(datetime.now(timezone.utc).timestamp())



# ============================================================
# PATH UTILITIES
# ============================================================

def normalize_path(
    path: Union[str, Path],
) -> Path:
    """
    Normalize filesystem path.

    Handles:
    - strings
    - pathlib objects
    - relative paths
    - Windows separators

    Returns:
        pathlib.Path
    """

    if isinstance(path, str):
        path = path.strip()

    return Path(path).expanduser().resolve()



def safe_path(
    *parts: Union[str, Path],
) -> Path:
    """
    Safely combine path components.

    Example:

        safe_path("project", "data", "file.json")

    """

    cleaned = []

    for part in parts:

        if part:

            cleaned.append(
                str(part)
            )

    return normalize_path(
        os.path.join(*cleaned)
    )



def ensure_absolute(
    path: Union[str, Path],
    base: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Convert path into absolute path.

    If relative:
        attach base directory.
    """

    path = Path(path)

    if path.is_absolute():
        return path.resolve()

    if base:

        return (
            Path(base)
            .joinpath(path)
            .resolve()
        )

    return path.resolve()



def filename(
    path: Union[str, Path],
) -> str:
    """
    Return filename only.
    """

    return Path(path).name



def extension(
    path: Union[str, Path],
) -> str:
    """
    Return lowercase file extension.

    Example:
        ".py"
    """

    return Path(path).suffix.lower()



def stem(
    path: Union[str, Path],
) -> str:
    """
    Return filename without extension.
    """

    return Path(path).stem



def parent_directory(
    path: Union[str, Path],
) -> Path:
    """
    Return parent directory.
    """

    return Path(path).parent



def path_exists(
    path: Union[str, Path],
) -> bool:
    """
    Check whether path exists.
    """

    return Path(path).exists()



def is_file(
    path: Union[str, Path],
) -> bool:
    """
    Check if path is a file.
    """

    return Path(path).is_file()



def is_directory(
    path: Union[str, Path],
) -> bool:
    """
    Check if path is a directory.
    """

    return Path(path).is_dir()



# ============================================================
# PROJECT DISCOVERY
# ============================================================

def find_project_root(
    start: Optional[Union[str, Path]] = None,
    markers: Optional[List[str]] = None,
) -> Optional[Path]:
    """
    Search upward for project root.

    Looks for common project markers:

    - .git
    - pyproject.toml
    - requirements.txt
    - manage.py
    - package.json

    """

    if markers is None:

        markers = [
            ".git",
            "pyproject.toml",
            "requirements.txt",
            "manage.py",
            "package.json",
        ]


    if start:

        current = normalize_path(start)

    else:

        current = Path.cwd().resolve()



    if current.is_file():

        current = current.parent



    while True:

        for marker in markers:

            if (
                current / marker
            ).exists():

                return current



        parent = current.parent


        if parent == current:

            break


        current = parent



    return None



def relative_path(
    path: Union[str, Path],
    base: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Return path relative to base.

    """

    path = normalize_path(path)

    if base is None:

        base = Path.cwd()

    else:

        base = normalize_path(base)


    return path.relative_to(base)



# ============================================================
# FILE TYPE HELPERS
# ============================================================

def is_text_file(
    path: Union[str, Path],
) -> bool:
    """
    Detect common text files.
    """

    return extension(path) in TEXT_EXTENSIONS



def is_hidden(
    path: Union[str, Path],
) -> bool:
    """
    Check hidden files.

    Supports:
    - Unix dot files
    - Windows hidden attribute
    """

    p = Path(path)

    if p.name.startswith("."):

        return True


    try:

        return bool(
            os.stat(p).st_file_attributes
            &
            getattr(
                os,
                "FILE_ATTRIBUTE_HIDDEN",
                0
            )
        )

    except Exception:


        return False
# ============================================================
# HASHING UTILITIES
# ============================================================

def hash_file(
    path: Union[str, Path],
    algorithm: str = DEFAULT_HASH_ALGORITHM,
    chunk_size: int = 1024 * 1024,
) -> str:
    """
    Calculate file hash.

    Supports:
    - sha256
    - sha1
    - md5
    - any hashlib algorithm

    Args:
        path:
            File path.

        algorithm:
            Hash algorithm name.

        chunk_size:
            Read size.

    Returns:
        Hexadecimal hash string.
    """

    path = normalize_path(path)

    if not path.exists():

        raise FileNotFoundError(
            f"File does not exist: {path}"
        )


    try:

        hasher = hashlib.new(
            algorithm
        )

    except ValueError as exc:

        raise ValueError(
            f"Unsupported hash algorithm: {algorithm}"
        ) from exc



    with open(
        path,
        "rb",
    ) as file:

        while True:

            chunk = file.read(
                chunk_size
            )

            if not chunk:

                break


            hasher.update(
                chunk
            )


    return hasher.hexdigest()



def sha256_file(
    path: Union[str, Path],
) -> str:
    """
    Shortcut SHA256 hashing.
    """

    return hash_file(
        path,
        "sha256",
    )



def md5_file(
    path: Union[str, Path],
) -> str:
    """
    Shortcut MD5 hashing.
    """

    return hash_file(
        path,
        "md5",
    )



def files_equal(
    first: Union[str, Path],
    second: Union[str, Path],
) -> bool:
    """
    Compare two files using hashes.
    """

    first = normalize_path(first)
    second = normalize_path(second)


    if not first.exists() or not second.exists():

        return False


    if first.stat().st_size != second.stat().st_size:

        return False


    return hash_file(first) == hash_file(second)



# ============================================================
# JSON UTILITIES
# ============================================================

def read_json(
    path: Union[str, Path],
    default: Optional[Any] = None,
) -> Any:
    """
    Read JSON file safely.

    Returns default when:
    - file missing
    - invalid JSON
    """

    path = normalize_path(path)


    if not path.exists():

        return default


    try:

        with open(
            path,
            "r",
            encoding=DEFAULT_ENCODING,
        ) as file:

            return json.load(file)


    except (
        json.JSONDecodeError,
        OSError,
    ):

        return default



def write_json(
    path: Union[str, Path],
    data: Any,
    indent: int = 4,
) -> bool:
    """
    Write JSON data.

    Creates parent directories automatically.
    """

    path = normalize_path(path)


    ensure_directory(
        path.parent
    )


    try:

        with open(
            path,
            "w",
            encoding=DEFAULT_ENCODING,
        ) as file:

            json.dump(
                data,
                file,
                indent=indent,
                ensure_ascii=False,
            )


        return True


    except OSError:

        return False



def atomic_write_json(
    path: Union[str, Path],
    data: Any,
) -> bool:
    """
    Safely write JSON using temporary file.

    Prevents corrupted files during crashes.
    """

    path = normalize_path(path)

    temp_path = path.with_suffix(
        path.suffix + ".tmp"
    )


    if write_json(
        temp_path,
        data,
    ):

        temp_path.replace(path)

        return True


    return False



# ============================================================
# DIRECTORY MANAGEMENT
# ============================================================

def ensure_directory(
    path: Union[str, Path],
) -> Path:
    """
    Create directory if missing.
    """

    path = Path(path)

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path



def directory_size(
    path: Union[str, Path],
) -> int:
    """
    Calculate directory size in bytes.
    """

    total = 0

    path = normalize_path(path)


    if not path.exists():

        return 0



    for item in path.rglob("*"):

        if item.is_file():

            try:

                total += item.stat().st_size

            except OSError:

                pass


    return total



def empty_directory(
    path: Union[str, Path],
) -> bool:
    """
    Remove all contents inside directory.
    """

    path = normalize_path(path)


    if not path.exists():

        return False


    for item in path.iterdir():

        try:

            if item.is_dir():

                shutil.rmtree(item)

            else:

                item.unlink()


        except OSError:

            return False


    return True



# ============================================================
# FILE OPERATIONS
# ============================================================

def read_file(
    path: Union[str, Path],
    encoding: str = DEFAULT_ENCODING,
) -> str:
    """
    Read text file.
    """

    path = normalize_path(path)


    with open(
        path,
        "r",
        encoding=encoding,
    ) as file:

        return file.read()



def write_file(
    path: Union[str, Path],
    content: str,
    encoding: str = DEFAULT_ENCODING,
) -> bool:
    """
    Write text file.
    """

    path = normalize_path(path)


    ensure_directory(
        path.parent
    )


    try:

        with open(
            path,
            "w",
            encoding=encoding,
        ) as file:

            file.write(
                content
            )


        return True


    except OSError:

        return False



def copy_file(
    source: Union[str, Path],
    destination: Union[str, Path],
) -> bool:
    """
    Copy file safely.
    """

    source = normalize_path(source)
    destination = normalize_path(destination)


    ensure_directory(
        destination.parent
    )


    try:

        shutil.copy2(
            source,
            destination,
        )

        return True


    except OSError:

        return False



def move_file(
    source: Union[str, Path],
    destination: Union[str, Path],
) -> bool:
    """
    Move file safely.
    """

    source = normalize_path(source)
    destination = normalize_path(destination)


    ensure_directory(
        destination.parent
    )


    try:

        shutil.move(
            source,
            destination,
        )

        return True


    except OSError:

        return False



def delete_file(
    path: Union[str, Path],
) -> bool:
    """
    Delete file.
    """

    path = normalize_path(path)


    try:

        if path.exists():

            path.unlink()


        return True


    except OSError:

        return False



# ============================================================
# FILE SCANNING
# ============================================================

def scan_files(
    directory: Union[str, Path],
    recursive: bool = True,
) -> Generator[Path, None, None]:
    """
    Scan directory for files.

    Yields:
        Path objects.
    """

    directory = normalize_path(directory)


    if not directory.exists():

        return



    iterator = (
        directory.rglob("*")
        if recursive
        else directory.glob("*")
    )


    for item in iterator:

        if item.is_file():

            yield item



def count_files(
    directory: Union[str, Path],
) -> int:
    """
    Count files recursively.
    """

    return sum(
        1
        for _
        in scan_files(directory)
    )



def find_files(
    directory: Union[str, Path],
    pattern: str = "*",
) -> List[Path]:
    """
    Find files matching pattern.
    """

    directory = normalize_path(directory)


    return [
        file
        for file in directory.rglob(pattern)
        if file.is_file()
    ]



def newest_file(
    directory: Union[str, Path],
) -> Optional[Path]:
    """
    Return newest modified file.
    """

    files = list(
        scan_files(directory)
    )


    if not files:

        return None


    return max(
        files,
        key=lambda item: item.stat().st_mtime,
    )
# ============================================================
# IGNORE MANAGEMENT
# ============================================================

def should_ignore(
    path: Union[str, Path],
    ignore_patterns: Optional[Iterable[str]] = None,
) -> bool:
    """
    Determine whether a path should be ignored.

    Supports:
    - default ignored folders
    - wildcard patterns
    - filenames
    """

    path = Path(path)

    patterns = set(
        DEFAULT_IGNORE_NAMES
    )


    if ignore_patterns:

        patterns.update(
            ignore_patterns
        )


    path_parts = set(
        path.parts
    )


    for part in path_parts:

        if part in patterns:

            return True



    name = path.name


    for pattern in patterns:

        try:

            if re.fullmatch(
                pattern.replace("*", ".*"),
                name,
            ):

                return True


        except re.error:

            continue



    return False



def load_ignore_file(
    path: Union[str, Path],
) -> List[str]:
    """
    Load ignore patterns from file.

    Compatible with:
    - .gitignore
    - .autosyncignore
    """

    path = normalize_path(path)


    if not path.exists():

        return []


    patterns = []


    try:

        with open(
            path,
            "r",
            encoding=DEFAULT_ENCODING,
        ) as file:

            for line in file:

                line = line.strip()


                if not line:

                    continue


                if line.startswith("#"):

                    continue


                patterns.append(
                    line
                )


    except OSError:

        pass


    return patterns



def load_gitignore(
    directory: Union[str, Path],
) -> List[str]:
    """
    Load .gitignore patterns from directory.
    """

    directory = normalize_path(directory)

    return load_ignore_file(
        directory / ".gitignore"
    )



def filter_ignored(
    files: Iterable[Path],
    patterns: Optional[Iterable[str]] = None,
) -> List[Path]:
    """
    Remove ignored files.
    """

    return [
        file
        for file in files
        if not should_ignore(
            file,
            patterns,
        )
    ]



# ============================================================
# CHANGE DETECTION
# ============================================================

def file_metadata(
    path: Union[str, Path],
) -> Dict[str, Any]:
    """
    Return file metadata snapshot.
    """

    path = normalize_path(path)


    if not path.exists():

        return {
            "exists": False,
            "path": str(path),
        }



    stat = path.stat()


    return {
        "exists": True,
        "path": str(path),
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "hash": hash_file(path),
    }



def has_changed(
    old: Dict[str, Any],
    new: Dict[str, Any],
) -> bool:
    """
    Compare metadata snapshots.
    """

    return old != new



def directory_snapshot(
    directory: Union[str, Path],
    ignore_patterns: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Create complete directory state snapshot.
    """

    snapshot = {}


    files = scan_files(
        directory
    )


    for file in filter_ignored(
        files,
        ignore_patterns,
    ):

        snapshot[str(file)] = file_metadata(
            file
        )


    return snapshot



# ============================================================
# GIT HELPERS
# ============================================================

def run_git(
    args: List[str],
    cwd: Optional[Union[str, Path]] = None,
) -> Optional[str]:
    """
    Execute git command.

    Returns:
        command output
        None on failure
    """

    command = [
        "git"
    ] + args


    try:

        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )


        return result.stdout.strip()



    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):

        return None



def is_git_repository(
    directory: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Check if directory is Git repository.
    """

    result = run_git(
        [
            "rev-parse",
            "--is-inside-work-tree",
        ],
        cwd=directory,
    )


    return result == "true"



def git_root(
    directory: Optional[Union[str, Path]] = None,
) -> Optional[Path]:
    """
    Return Git repository root.
    """

    result = run_git(
        [
            "rev-parse",
            "--show-toplevel",
        ],
        cwd=directory,
    )


    if result:

        return Path(result).resolve()


    return None



def git_branch(
    directory: Optional[Union[str, Path]] = None,
) -> Optional[str]:
    """
    Return current Git branch.
    """

    return run_git(
        [
            "branch",
            "--show-current",
        ],
        cwd=directory,
    )



def git_status(
    directory: Optional[Union[str, Path]] = None,
) -> List[str]:
    """
    Return Git changed files.
    """

    result = run_git(
        [
            "status",
            "--short",
        ],
        cwd=directory,
    )


    if not result:

        return []


    return result.splitlines()



def git_add(
    files: Iterable[Union[str, Path]],
    directory: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Stage files in Git.
    """

    arguments = [
        "add"
    ]


    arguments.extend(
        str(file)
        for file in files
    )


    return (
        run_git(
            arguments,
            directory,
        )
        is not None
    )



def git_commit(
    message: str,
    directory: Optional[Union[str, Path]] = None,
) -> bool:
    """
    Create Git commit.
    """

    return (
        run_git(
            [
                "commit",
                "-m",
                message,
            ],
            directory,
        )
        is not None
    )



# ============================================================
# SYSTEM HELPERS
# ============================================================

def environment_info() -> Dict[str, str]:
    """
    Return runtime environment details.
    """

    return {
        "platform": os.name,
        "python": os.sys.version,
        "cwd": str(Path.cwd()),
    }



def safe_delete_directory(
    path: Union[str, Path],
) -> bool:
    """
    Delete directory safely.
    """

    path = normalize_path(path)


    if not path.exists():

        return True


    try:

        shutil.rmtree(
            path
        )

        return True


    except OSError:

        return False



def format_bytes(
    size: int,
) -> str:
    """
    Convert bytes into readable size.
    """

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]


    value = float(size)


    for unit in units:

        if value < 1024:

            return (
                f"{value:.2f} {unit}"
            )

        value /= 1024


    return (
        f"{value:.2f} PB"
    )



def ensure_list(
    value: Any,
) -> List[Any]:
    """
    Convert value into list.
    """

    if value is None:

        return []


    if isinstance(
        value,
        list,
    ):

        return value


    if isinstance(
        value,
        tuple,
    ):

        return list(value)


    return [value]



# ============================================================
# MODULE EXPORTS
# ============================================================

__all__ = [

    # timestamps
    "utc_now",
    "local_now",
    "timestamp",
    "iso_timestamp",
    "unix_timestamp",

    # paths
    "normalize_path",
    "safe_path",
    "find_project_root",
    "relative_path",

    # hashing
    "hash_file",
    "sha256_file",
    "md5_file",
    "files_equal",

    # json
    "read_json",
    "write_json",
    "atomic_write_json",

    # files
    "read_file",
    "write_file",
    "copy_file",
    "move_file",
    "delete_file",

    # scanning
    "scan_files",
    "find_files",
    "count_files",

    # ignore
    "should_ignore",
    "load_gitignore",
    "filter_ignored",

    # changes
    "file_metadata",
    "directory_snapshot",
    "has_changed",

    # git
    "is_git_repository",
    "git_root",
    "git_branch",
    "git_status",
    "git_add",
    "git_commit",

    # system
    "environment_info",
    "format_bytes",
]
