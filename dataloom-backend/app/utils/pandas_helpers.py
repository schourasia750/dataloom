"""Pandas utility functions for safe CSV operations and response building."""

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import HTTPException
from pandas.api.types import is_bool_dtype, is_datetime64_any_dtype, is_numeric_dtype


def read_csv_safe(path: Path) -> pd.DataFrame:
    """Read a CSV file safely with error handling.

    Args:
        path: Path to the CSV file.

    Returns:
        DataFrame with the CSV contents.

    Raises:
        HTTPException: If the file cannot be read.
    """
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"CSV file not found: {path}") from None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading CSV: {str(e)}") from e


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


def _to_json_safe(value: Any) -> Any:
    """Convert pandas/numpy values into JSON-safe primitives."""
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if isinstance(value, float) and not pd.notna(value):
        return None

    return value


def _round_float(value: float | None) -> float | None:
    """Round floats for compact API responses."""
    if value is None:
        return None
    return round(float(value), 2)


def build_dataset_profile(df: pd.DataFrame, dtypes: dict[str, str] | None = None) -> dict[str, Any]:
    """Build dataset-level and per-column profiling facts."""
    dtype_map = dtypes or {col: _map_dtype(dtype) for col, dtype in df.dtypes.items()}
    row_count = int(len(df))
    column_profiles: list[dict[str, Any]] = []

    for column in df.columns:
        series = df[column]
        non_null_count = int(series.notna().sum())
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))
        sample_values = [_to_json_safe(value) for value in series.dropna().drop_duplicates().head(3).tolist()]

        profile: dict[str, Any] = {
            "name": str(column),
            "data_type": dtype_map.get(column, "unknown"),
            "non_null_count": non_null_count,
            "missing_count": missing_count,
            "missing_percent": _round_float((missing_count / row_count * 100) if row_count else 0.0),
            "unique_count": unique_count,
            "unique_percent": _round_float((unique_count / non_null_count * 100) if non_null_count else 0.0),
            "sample_values": sample_values,
            "mean": None,
            "min": None,
            "max": None,
        }

        if is_numeric_dtype(series) and not is_bool_dtype(series):
            numeric_series = pd.to_numeric(series, errors="coerce").dropna()
            if not numeric_series.empty:
                profile["mean"] = _round_float(numeric_series.mean())
                profile["min"] = _to_json_safe(numeric_series.min())
                profile["max"] = _to_json_safe(numeric_series.max())
        elif is_datetime64_any_dtype(series):
            datetime_series = series.dropna()
            if not datetime_series.empty:
                profile["min"] = _to_json_safe(datetime_series.min())
                profile["max"] = _to_json_safe(datetime_series.max())

        column_profiles.append(profile)

    return {
        "summary": {
            "row_count": row_count,
            "column_count": int(len(df.columns)),
            "missing_cells": int(df.isna().sum().sum()),
            "duplicate_rows": int(df.duplicated().sum()) if len(df.columns) > 0 else 0,
        },
        "columns": column_profiles,
    }


def dataframe_to_response(df: pd.DataFrame) -> dict[str, Any]:
    """Convert a DataFrame to an API response dict.

    Args:
        df: Source DataFrame.

    Returns:
        Dict with columns (list of str), rows (list of lists), row_count, and dtypes.
    """
    dtypes = {col: _map_dtype(dtype) for col, dtype in df.dtypes.items()}
    profile = build_dataset_profile(df, dtypes)
    df = df.fillna("")
    df = df.replace([float("inf"), float("-inf")], "")
    columns = df.columns.tolist()
    rows = df.values.tolist()
    return {"columns": columns, "rows": rows, "row_count": len(rows), "dtypes": dtypes, "profile": profile}


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
