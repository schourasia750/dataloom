"""File storage and management service for dataset uploads."""

import shutil
from pathlib import Path

from app.utils.logging import get_logger
from app.utils.security import resolve_upload_path, sanitize_filename

logger = get_logger(__name__)


def store_upload(file) -> tuple[Path, Path]:
    """Store an uploaded file and determine the working copy path.

    Saves the original uploaded file with a sanitized name and returns the path
    for the CSV working copy used by transformation operations.

    Args:
        file: The FastAPI UploadFile object.

    Returns:
        Tuple of (original_path, copy_path).
    """
    safe_name = sanitize_filename(file.filename)
    original_path = resolve_upload_path(safe_name)

    with open(original_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)

    if original_path.suffix.lower() == ".csv":
        copy_name = f"{original_path.stem}_copy.csv"
    else:
        copy_name = f"{original_path.name}_copy.csv"
    copy_path = original_path.with_name(copy_name)

    logger.info("Stored upload: original=%s, working_copy=%s", original_path, copy_path)
    return original_path, copy_path


def get_original_path(copy_path: str) -> Path:
    """Derive the original file path from a working copy path.

    Args:
        copy_path: Path to the CSV working file.

    Returns:
        Path to the original uploaded file.
    """
    path = Path(copy_path)

    if not path.name.endswith("_copy.csv"):
        return path

    base_name = path.name.removesuffix("_copy.csv")
    if "." in base_name:
        return path.with_name(base_name)

    return path.with_name(f"{base_name}.csv")


def delete_project_files(copy_path: str) -> None:
    """Delete both the working copy and original file for a project.

    Args:
        copy_path: Path to the CSV working file.
    """
    original_path = get_original_path(copy_path)

    for path in [Path(copy_path), original_path]:
        try:
            path.unlink()
            logger.info("Deleted file: %s", path)
        except FileNotFoundError:
            logger.warning("File already missing: %s", path)
