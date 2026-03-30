"""Tests for new features: rename column, cast data type, export, and delete project."""

import csv
import json
from io import BytesIO

import pandas as pd
import pytest

from app.services.transformation_service import (
    TransformationError,
    apply_logged_transformation,
    cast_data_type,
    rename_column,
)


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [30, 25, 35],
            "city": ["New York", "Los Angeles", "Chicago"],
        }
    )


@pytest.fixture
def uploaded_project(client, sample_csv, db):
    with open(sample_csv, "rb") as f:
        response = client.post(
            "/projects/upload",
            files={"file": ("test.csv", f, "text/csv")},
            data={
                "projectName": "Test Project",
                "projectDescription": "Regression fixture upload",
            },
        )
    assert response.status_code == 200, f"Project upload failed with {response.status_code}: {response.text}"
    return response.json()["project_id"]


# --- Rename Column Tests ---


class TestRenameColumn:
    def test_rename_column_basic(self, sample_df):
        result = rename_column(sample_df, 0, "full_name")
        assert "full_name" in result.columns
        assert "name" not in result.columns
        assert result.iloc[0]["full_name"] == "Alice"

    def test_rename_column_middle(self, sample_df):
        result = rename_column(sample_df, 1, "years")
        assert list(result.columns) == ["name", "years", "city"]

    def test_rename_column_index_out_of_range(self, sample_df):
        with pytest.raises(TransformationError, match="out of range"):
            rename_column(sample_df, 5, "new")

    def test_rename_column_negative_index(self, sample_df):
        with pytest.raises(TransformationError, match="out of range"):
            rename_column(sample_df, -1, "new")

    def test_rename_column_empty_name(self, sample_df):
        with pytest.raises(TransformationError, match="empty"):
            rename_column(sample_df, 0, "")

    def test_rename_column_whitespace_name(self, sample_df):
        with pytest.raises(TransformationError, match="empty"):
            rename_column(sample_df, 0, "   ")


# --- Cast Data Type Tests ---


class TestCastDataType:
    def test_cast_to_string(self, sample_df):
        result = cast_data_type(sample_df, "age", "string")
        assert str(result.iloc[0]["age"]) == "30"

    def test_cast_to_integer(self):
        df = pd.DataFrame({"val": ["10", "20", "30"]})
        result = cast_data_type(df, "val", "integer")
        assert result["val"].dtype == "Int64"
        assert result.iloc[0]["val"] == 10

    def test_cast_to_integer_with_nan(self):
        df = pd.DataFrame({"val": ["10", "abc", "30"]})
        result = cast_data_type(df, "val", "integer")
        assert pd.isna(result.iloc[1]["val"])
        assert result.iloc[0]["val"] == 10

    def test_cast_to_float(self):
        df = pd.DataFrame({"val": ["1.5", "2.7", "3.14"]})
        result = cast_data_type(df, "val", "float")
        assert result["val"].dtype == float
        assert result.iloc[2]["val"] == pytest.approx(3.14)

    def test_cast_to_boolean(self):
        df = pd.DataFrame({"val": ["true", "false", "yes", "no"]})
        result = cast_data_type(df, "val", "boolean")
        assert bool(result.iloc[0]["val"]) is True
        assert bool(result.iloc[1]["val"]) is False
        assert bool(result.iloc[2]["val"]) is True
        assert bool(result.iloc[3]["val"]) is False

    def test_cast_to_datetime(self):
        df = pd.DataFrame({"val": ["2024-01-01", "2024-06-15"]})
        result = cast_data_type(df, "val", "datetime")
        assert pd.api.types.is_datetime64_any_dtype(result["val"])

    def test_cast_invalid_column(self, sample_df):
        with pytest.raises(TransformationError, match="not found"):
            cast_data_type(sample_df, "nonexistent", "string")


# --- Log Replay Tests ---


class TestLogReplay:
    def test_replay_rename_column(self, sample_df):
        details = {"rename_col_params": {"col_index": 0, "new_name": "full_name"}}
        result = apply_logged_transformation(sample_df, "renameCol", details)
        assert "full_name" in result.columns

    def test_replay_cast_data_type(self, sample_df):
        details = {"cast_data_type_params": {"column": "age", "target_type": "string"}}
        result = apply_logged_transformation(sample_df, "castDataType", details)
        assert str(result.iloc[0]["age"]) == "30"


class TestAddDeleteColumnEndpoint:
    def test_add_column_with_name_returns_200(self, client, sample_csv, db):
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Add Column Success", "projectDescription": "Test add column success"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        response = client.post(
            f"/projects/{project_id}/transform",
            json={"operation_type": "addCol", "add_col_params": {"index": 1, "name": "country"}},
        )
        assert response.status_code == 200

    def test_delete_column_without_name_returns_200(self, client, sample_csv, db):
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Delete Column Test", "projectDescription": "Test delete column"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        response = client.post(
            f"/projects/{project_id}/transform",
            json={"operation_type": "delCol", "del_col_params": {"index": 1}},
        )
        assert response.status_code == 200

    def test_add_column_without_name_returns_422(self, client, sample_csv, db):
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Add Column Test", "projectDescription": "Test add column"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        response = client.post(
            f"/projects/{project_id}/transform",
            json={"operation_type": "addCol", "add_col_params": {"index": 1}},
        )
        assert response.status_code == 422

    def test_add_column_with_legacy_col_params_returns_400(self, client, sample_csv, db):
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Add Column Legacy", "projectDescription": "Test legacy add key"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        response = client.post(
            f"/projects/{project_id}/transform",
            json={"operation_type": "addCol", "col_params": {"index": 1, "name": "country"}},
        )
        assert response.status_code == 400

    def test_delete_column_with_legacy_col_params_returns_400(self, client, sample_csv, db):
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Delete Column Legacy", "projectDescription": "Test legacy delete key"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        response = client.post(
            f"/projects/{project_id}/transform",
            json={"operation_type": "delCol", "col_params": {"index": 1}},
        )
        assert response.status_code == 400


# --- Export Endpoint Tests ---


class TestExportEndpoint:
    @pytest.mark.parametrize(
        ("export_format", "expected_content_type"),
        [
            ("csv", "text/csv"),
            ("tsv", "text/tab-separated-values"),
            ("json", "application/json"),
            ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("parquet", "application/octet-stream"),
        ],
    )
    def test_export_project(self, client, sample_csv, db, export_format, expected_content_type):
        # Upload a project first
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Export Test", "projectDescription": "Test export"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        # Export the project
        export_response = client.get(f"/projects/{project_id}/export?format={export_format}")
        assert export_response.status_code == 200
        assert export_response.headers["content-type"].startswith(expected_content_type)

        if export_format in {"csv", "tsv"}:
            content = export_response.content.decode("utf-8")
            delimiter = "," if export_format == "csv" else "\t"
            reader = csv.reader(content.strip().splitlines(), delimiter=delimiter)
            rows = list(reader)
            assert rows[0] == ["name", "age", "city"]
            assert len(rows) == 5
        elif export_format == "json":
            payload = json.loads(export_response.content.decode("utf-8"))
            assert payload[0]["name"] == "Alice"
            assert len(payload) == 4
        elif export_format == "xlsx":
            df = pd.read_excel(BytesIO(export_response.content))
            assert list(df.columns) == ["name", "age", "city"]
            assert len(df) == 4
        elif export_format == "parquet":
            df = pd.read_parquet(BytesIO(export_response.content))
            assert list(df.columns) == ["name", "age", "city"]
            assert len(df) == 4

    def test_export_nonexistent_project(self, client):
        response = client.get("/projects/00000000-0000-0000-0000-000000000000/export")
        assert response.status_code == 404

    @pytest.mark.parametrize(
        ("report_format", "expected_content_type"),
        [
            ("html", "text/html"),
            ("pdf", "application/pdf"),
        ],
    )
    def test_quality_report_generation(self, client, sample_csv, db, report_format, expected_content_type):
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Quality Test", "projectDescription": "Test quality reports"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        report_response = client.get(f"/projects/{project_id}/quality-report?format={report_format}")
        assert report_response.status_code == 200
        assert report_response.headers["content-type"].startswith(expected_content_type)

        if report_format == "html":
            body = report_response.content.decode("utf-8")
            assert "Quality Test Quality Report" in body
            assert "Column Summary" in body
        else:
            assert report_response.content.startswith(b"%PDF")


# --- Delete Endpoint Tests ---


class TestDeleteEndpoint:
    def test_delete_project(self, client, sample_csv, db):
        # Upload a project first
        with open(sample_csv, "rb") as f:
            response = client.post(
                "/projects/upload",
                files={"file": ("test.csv", f, "text/csv")},
                data={"projectName": "Delete Test", "projectDescription": "Test delete"},
            )
        assert response.status_code == 200
        project_id = response.json()["project_id"]

        # Delete the project
        delete_response = client.delete(f"/projects/{project_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # Verify project is gone
        get_response = client.get(f"/projects/get/{project_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_project(self, client):
        response = client.delete("/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404


class TestTransformEndpoint:
    def test_delete_column_accepts_index_only_params(self, client, uploaded_project, sample_csv):
        original_columns = pd.read_csv(sample_csv).columns.tolist()
        expected_columns = original_columns[1:]

        response = client.post(
            f"/projects/{uploaded_project}/transform",
            json={
                "operation_type": "delCol",
                "del_col_params": {"index": 0},
                "col_params": {"index": 0},
            },
        )
        assert response.status_code == 200
        assert response.json()["columns"] == expected_columns

    @pytest.mark.parametrize(
        "col_params,expected_status",
        [
            ({"index": 99}, 400),
            ({}, 422),
        ],
    )
    def test_delete_column_invalid_params(
        self,
        client,
        uploaded_project,
        col_params,
        expected_status,
    ):
        response = client.post(
            f"/projects/{uploaded_project}/transform",
            json={
                "operation_type": "delCol",
                "del_col_params": col_params,
                "col_params": col_params,
            },
        )
        assert response.status_code == expected_status
