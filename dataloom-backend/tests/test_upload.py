"""Tests for dataset upload functionality."""

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from fastapi import HTTPException

from app.services.file_service import get_original_path
from app.utils.security import validate_upload_file


class MockUploadFile:
    """Mock for FastAPI UploadFile."""

    def __init__(self, filename, content=b"col1,col2\n1,2\n"):
        self.filename = filename
        self.file = BytesIO(content)


class TestValidateUploadFile:
    @pytest.mark.parametrize("filename", ["data.csv", "data.tsv", "data.json", "data.xlsx", "data.parquet"])
    def test_supported_file_types_accepted(self, filename):
        file = MockUploadFile(filename)
        validate_upload_file(file)

    def test_unsupported_file_type_rejected(self):
        file = MockUploadFile("data.pdf")
        with pytest.raises(HTTPException, match="not allowed"):
            validate_upload_file(file)

    def test_exe_rejected(self):
        file = MockUploadFile("malware.exe")
        with pytest.raises(HTTPException, match="not allowed"):
            validate_upload_file(file)

    def test_no_extension_rejected(self):
        file = MockUploadFile("noextension")
        with pytest.raises(HTTPException, match="not allowed"):
            validate_upload_file(file)


def _write_dataset(path: Path) -> None:
    df = pd.DataFrame(
        [
            {"name": "Alice", "age": 30, "city": "New York"},
            {"name": "Bob", "age": 25, "city": "Los Angeles"},
        ]
    )

    if path.suffix == ".csv":
        df.to_csv(path, index=False)
    elif path.suffix == ".tsv":
        df.to_csv(path, sep="\t", index=False)
    elif path.suffix == ".json":
        df.to_json(path, orient="records")
    elif path.suffix == ".xlsx":
        df.to_excel(path, index=False)
    elif path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported test dataset extension: {path.suffix}")


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("data.csv", "text/csv"),
        ("data.tsv", "text/tab-separated-values"),
        ("data.json", "application/json"),
        ("data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("data.parquet", "application/octet-stream"),
    ],
)
def test_upload_endpoint_accepts_supported_formats(client, tmp_path, filename, content_type):
    dataset_path = tmp_path / filename
    _write_dataset(dataset_path)

    with open(dataset_path, "rb") as f:
        response = client.post(
            "/projects/upload",
            files={"file": (filename, f, content_type)},
            data={"projectName": "Supported Format", "projectDescription": "upload coverage"},
        )

    assert response.status_code == 200, response.text

    payload = response.json()
    assert payload["columns"] == ["name", "age", "city"]
    assert payload["rows"] == [["Alice", 30, "New York"], ["Bob", 25, "Los Angeles"]]
    assert payload["row_count"] == 2
    assert Path(payload["file_path"]).name.endswith("_copy.csv")
    assert get_original_path(payload["file_path"]).suffix.lower() == dataset_path.suffix.lower()
