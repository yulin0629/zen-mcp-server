"""
File type definitions and constants for file processing

This module centralizes all file type and extension definitions used
throughout the MCP server for consistent file handling.
"""

# Programming language file extensions - core code files
PROGRAMMING_LANGUAGES = {
    ".py",  # Python
    ".js",  # JavaScript
    ".ts",  # TypeScript
    ".jsx",  # React JavaScript
    ".tsx",  # React TypeScript
    ".java",  # Java
    ".cpp",  # C++
    ".c",  # C
    ".h",  # C/C++ Header
    ".hpp",  # C++ Header
    ".cs",  # C#
    ".go",  # Go
    ".rs",  # Rust
    ".rb",  # Ruby
    ".php",  # PHP
    ".swift",  # Swift
    ".kt",  # Kotlin
    ".scala",  # Scala
    ".r",  # R
    ".m",  # Objective-C
    ".mm",  # Objective-C++
}

# Script and shell file extensions
SCRIPTS = {
    ".sql",  # SQL
    ".sh",  # Shell
    ".bash",  # Bash
    ".zsh",  # Zsh
    ".fish",  # Fish shell
    ".ps1",  # PowerShell
    ".bat",  # Batch
    ".cmd",  # Command
}

# Configuration and data file extensions
CONFIGS = {
    ".yml",  # YAML
    ".yaml",  # YAML
    ".json",  # JSON
    ".xml",  # XML
    ".toml",  # TOML
    ".ini",  # INI
    ".cfg",  # Config
    ".conf",  # Config
    ".properties",  # Properties
    ".env",  # Environment
}

# Documentation and markup file extensions
DOCS = {
    ".txt",  # Text
    ".md",  # Markdown
    ".rst",  # reStructuredText
    ".tex",  # LaTeX
}

# Web development file extensions
WEB = {
    ".html",  # HTML
    ".css",  # CSS
    ".scss",  # Sass
    ".sass",  # Sass
    ".less",  # Less
}

# Additional text file extensions for logs and data
TEXT_DATA = {
    ".log",  # Log files
    ".csv",  # CSV
    ".tsv",  # TSV
    ".gitignore",  # Git ignore
    ".dockerfile",  # Docker
    ".makefile",  # Make
    ".cmake",  # CMake
    ".gradle",  # Gradle
    ".sbt",  # SBT
    ".pom",  # Maven POM
    ".lock",  # Lock files
}

# Image file extensions - limited to what AI models actually support
# Based on OpenAI and Gemini supported formats: PNG, JPEG, GIF, WebP
IMAGES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Binary executable and library extensions
BINARIES = {
    ".exe",  # Windows executable
    ".dll",  # Windows library
    ".so",  # Linux shared object
    ".dylib",  # macOS dynamic library
    ".bin",  # Binary
    ".class",  # Java class
}

# Archive and package file extensions
ARCHIVES = {
    ".jar",
    ".war",
    ".ear",  # Java archives
    ".zip",
    ".tar",
    ".gz",  # General archives
    ".7z",
    ".rar",  # Compression
    ".deb",
    ".rpm",  # Linux packages
    ".dmg",
    ".pkg",  # macOS packages
}

# Derived sets for different use cases
CODE_EXTENSIONS = PROGRAMMING_LANGUAGES | SCRIPTS | CONFIGS | DOCS | WEB
PROGRAMMING_EXTENSIONS = PROGRAMMING_LANGUAGES  # For line numbering
TEXT_EXTENSIONS = CODE_EXTENSIONS | TEXT_DATA
IMAGE_EXTENSIONS = IMAGES
BINARY_EXTENSIONS = BINARIES | ARCHIVES

# All extensions by category for easy access
FILE_CATEGORIES = {
    "programming": PROGRAMMING_LANGUAGES,
    "scripts": SCRIPTS,
    "configs": CONFIGS,
    "docs": DOCS,
    "web": WEB,
    "text_data": TEXT_DATA,
    "images": IMAGES,
    "binaries": BINARIES,
    "archives": ARCHIVES,
}


def get_file_category(file_path: str) -> str:
    """
    Determine the category of a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        Category name or "unknown" if not recognized
    """
    from pathlib import Path

    extension = Path(file_path).suffix.lower()

    for category, extensions in FILE_CATEGORIES.items():
        if extension in extensions:
            return category

    return "unknown"


def is_code_file(file_path: str) -> bool:
    """Check if a file is a code file (programming language)."""
    from pathlib import Path

    return Path(file_path).suffix.lower() in PROGRAMMING_LANGUAGES


def is_text_file(file_path: str) -> bool:
    """Check if a file is a text file."""
    from pathlib import Path

    return Path(file_path).suffix.lower() in TEXT_EXTENSIONS


def is_binary_file(file_path: str) -> bool:
    """Check if a file is a binary file."""
    from pathlib import Path

    return Path(file_path).suffix.lower() in BINARY_EXTENSIONS


# File-type specific token-to-byte ratios for accurate token estimation
# Based on empirical analysis of file compression characteristics and tokenization patterns
TOKEN_ESTIMATION_RATIOS = {
    # Programming languages - INCREASED RATIOS FOR MORE GENEROUS ESTIMATES
    ".py": 4.0,  # Python - increased from 3.5 to 4.0
    ".js": 3.8,  # JavaScript - increased from 3.2 to 3.8
    ".ts": 3.9,  # TypeScript - increased from 3.3 to 3.9
    ".jsx": 3.7,  # React JSX - increased from 3.1 to 3.7
    ".tsx": 3.6,  # React TSX - increased from 3.0 to 3.6
    ".java": 4.2,  # Java - increased from 3.6 to 4.2
    ".cpp": 4.3,  # C++ - increased from 3.7 to 4.3
    ".c": 4.4,  # C - increased from 3.8 to 4.4
    ".go": 4.5,  # Go - increased from 3.9 to 4.5
    ".rs": 4.0,  # Rust - increased from 3.5 to 4.0
    ".php": 3.9,  # PHP - increased from 3.3 to 3.9
    ".rb": 4.2,  # Ruby - increased from 3.6 to 4.2
    ".swift": 4.0,  # Swift - increased from 3.4 to 4.0
    ".kt": 4.0,  # Kotlin - increased from 3.5 to 4.0
    ".scala": 3.8,  # Scala - increased from 3.2 to 3.8
    # Scripts and configuration - INCREASED RATIOS
    ".sh": 4.7,  # Shell scripts - increased from 4.1 to 4.7
    ".bat": 4.6,  # Batch files - increased from 4.0 to 4.6
    ".ps1": 4.4,  # PowerShell - increased from 3.8 to 4.4
    ".sql": 4.4,  # SQL - increased from 3.8 to 4.4
    # Data and configuration formats
    ".json": 3.0,  # JSON - increased from 2.5 to 3.0
    ".yaml": 3.5,  # YAML - increased from 3.0 to 3.5
    ".yml": 3.5,  # YAML (alternative extension) - increased from 3.0 to 3.5
    ".xml": 3.4,  # XML - increased from 2.8 to 3.4
    ".toml": 3.8,  # TOML - increased from 3.2 to 3.8
    # Documentation and text - INCREASED RATIOS
    ".md": 4.8,  # Markdown - increased from 4.2 to 4.8
    ".txt": 4.6,  # Plain text - increased from 4.0 to 4.6
    ".rst": 4.7,  # reStructuredText - increased from 4.1 to 4.7
    # Web technologies
    ".html": 3.5,  # HTML - increased from 2.9 to 3.5
    ".css": 4.0,  # CSS - increased from 3.4 to 4.0
    # Logs and data - INCREASED RATIOS
    ".log": 5.0,  # Log files - increased from 4.5 to 5.0
    ".csv": 3.7,  # CSV - increased from 3.1 to 3.7
    # Docker and infrastructure
    ".dockerfile": 4.3,  # Dockerfile - increased from 3.7 to 4.3
    ".tf": 4.0,  # Terraform - increased from 3.5 to 4.0
}


def get_token_estimation_ratio(file_path: str) -> float:
    """
    Get the token estimation ratio for a file based on its extension.

    Args:
        file_path: Path to the file

    Returns:
        Token-to-byte ratio for the file type (default: 3.5 for unknown types)
    """
    from pathlib import Path

    extension = Path(file_path).suffix.lower()
    return TOKEN_ESTIMATION_RATIOS.get(extension, 4.0)  # More generous default (was 3.5)


# MIME type mappings for image files - limited to what AI models actually support
# Based on OpenAI and Gemini supported formats: PNG, JPEG, GIF, WebP
IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def get_image_mime_type(extension: str) -> str:
    """
    Get the MIME type for an image file extension.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        MIME type string (default: image/jpeg for unknown extensions)
    """
    if not extension.startswith("."):
        extension = "." + extension
    extension = extension.lower()
    return IMAGE_MIME_TYPES.get(extension, "image/jpeg")
