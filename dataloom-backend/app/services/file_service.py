"""File storage and management service for dataset uploads."""

import shutil
from pathlib import Path

from app.utils.logging import get_logger
from app.utils.pandas_helpers import read_dataframe_safe, save_csv_safe
from app.utils.security import resolve_upload_path, sanitize_filename

logger = get_logger(__name__)


def store_upload(file) -> tuple[Path, Path]:
    """Store an uploaded file and create a working copy.

    Saves the original file with a sanitized name and creates a normalized
    _copy.csv working file for transformation operations, keeping the original
    pristine.

    Args:
        file: The FastAPI UploadFile object.

    Returns:
        Tuple of (original_path, copy_path).
    """
    safe_name = sanitize_filename(file.filename)
    original_path = resolve_upload_path(safe_name)

    with open(original_path, "wb+") as f:
        shutil.copyfileobj(file.file, f)

    copy_path = Path(f"{original_path}_copy.csv")
    df = read_dataframe_safe(original_path)
    save_csv_safe(df, copy_path)

    logger.info("Stored upload: original=%s, copy=%s", original_path, copy_path)
    return original_path, copy_path


def get_original_path(copy_path: str) -> Path:
    """Derive the original file path from a working copy path.

    Args:
        copy_path: Path to the _copy.csv working file.

    Returns:
        Path to the original CSV file.
    """
    path = Path(copy_path)
    if path.name.endswith("_copy.csv"):
        return path.with_name(path.name[: -len("_copy.csv")])
    return path


def delete_project_files(copy_path: str) -> None:
    """Delete both the working copy and original file for a project.

    Args:
        copy_path: Path to the _copy.csv working file.
    """
    original_path = get_original_path(copy_path)

    for path in [Path(copy_path), original_path]:
        try:
            path.unlink()
            logger.info("Deleted file: %s", path)
        except FileNotFoundError:
            logger.warning("File already missing: %s", path)
