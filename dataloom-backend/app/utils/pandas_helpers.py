"""Pandas utility functions for safe dataframe operations and response building."""

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException


def read_dataframe_safe(path: Path) -> pd.DataFrame:
    """Read a supported dataset file safely with error handling.

    Args:
        path: Path to the dataset file.

    Returns:
        DataFrame with the file contents.

    Raises:
        HTTPException: If the file cannot be read.
    """
    path = Path(path)
    try:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix == ".tsv":
            return pd.read_csv(path, sep="\t")
        if suffix == ".xlsx":
            return pd.read_excel(path)
        if suffix == ".json":
            return pd.read_json(path)
        if suffix == ".parquet":
            return pd.read_parquet(path)
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {path}") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading dataset: {str(e)}") from e


def read_csv_safe(path: Path) -> pd.DataFrame:
    """Read a CSV file safely with error handling."""
    return read_dataframe_safe(path)


def save_csv_safe(df: pd.DataFrame, path: Path) -> None:
    """Save a DataFrame to CSV safely.

    Args:
        df: DataFrame to save.
        path: Destination file path.

    Raises:
        HTTPException: If the file cannot be saved.
    """
    try:
        df.to_csv(path, index=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving CSV: {str(e)}") from e


def dataframe_to_bytes(df: pd.DataFrame, export_format: str) -> bytes:
    """Serialize a DataFrame into a downloadable file payload."""
    try:
        if export_format == "csv":
            return df.to_csv(index=False).encode("utf-8")
        if export_format == "tsv":
            return df.to_csv(index=False, sep="\t").encode("utf-8")
        if export_format == "json":
            return df.to_json(orient="records", indent=2, date_format="iso").encode("utf-8")
        if export_format == "xlsx":
            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")
            return buffer.getvalue()
        if export_format == "parquet":
            buffer = BytesIO()
            df.to_parquet(buffer, index=False)
            return buffer.getvalue()
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {export_format}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting dataset: {str(e)}") from e


def _map_dtype(dtype) -> str:
    """Map a pandas dtype to a short label string."""
    kind = dtype.kind
    if kind == "i" or kind == "u":
        return "int"
    elif kind == "f":
        return "float"
    elif kind == "b":
        return "bool"
    elif kind == "M":
        return "datetime"
    elif kind == "O" or kind == "U" or kind == "S":
        return "str"
    else:
        return "unknown"


def dataframe_to_response(df: pd.DataFrame) -> dict[str, Any]:
    """Convert a DataFrame to an API response dict.

    Args:
        df: Source DataFrame.

    Returns:
        Dict with columns (list of str), rows (list of lists), row_count, and dtypes.
    """
    dtypes = {col: _map_dtype(dtype) for col, dtype in df.dtypes.items()}
    df = df.fillna("")
    df = df.replace([float("inf"), float("-inf")], "")
    columns = df.columns.tolist()
    rows = df.values.tolist()
    return {"columns": columns, "rows": rows, "row_count": len(rows), "dtypes": dtypes}


def validate_row_index(df: pd.DataFrame, index: int) -> None:
    """Validate that a row index is within DataFrame bounds.

    Args:
        df: Source DataFrame.
        index: Row index to validate.

    Raises:
        HTTPException: If index is out of range.
    """
    if index < 0 or index >= len(df):
        raise HTTPException(
            status_code=400,
            detail=f"Row index {index} out of range (0-{len(df) - 1})",
        )


def validate_column_index(df: pd.DataFrame, index: int) -> None:
    """Validate that a column index is within DataFrame bounds.

    Args:
        df: Source DataFrame.
        index: Column index to validate.

    Raises:
        HTTPException: If index is out of range.
    """
    if index < 0 or index >= len(df.columns):
        raise HTTPException(
            status_code=400,
            detail=f"Column index {index} out of range (0-{len(df.columns) - 1})",
        )
