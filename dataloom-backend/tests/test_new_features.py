"""Tests for new features: rename column, cast data type, export, and delete project."""

import csv

import pandas as pd
import pytest

from app.services.transformation_service import (
    TransformationError,
    apply_logged_transformation,
    cast_data_type,
    join_projects,
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


class TestJoinProjects:
    def test_join_projects_inner(self):
        left_df = pd.DataFrame({"employee_id": [1, 2], "name": ["Alice", "Bob"]})
        right_df = pd.DataFrame({"employee_id": [1, 3], "team": ["Sales", "Ops"]})

        result = join_projects(left_df, right_df, "employee_id", "employee_id", "inner", "team")

        assert result.columns.tolist() == ["employee_id", "name", "team"]
        assert result.values.tolist() == [[1, "Alice", "Sales"]]

    def test_join_projects_with_duplicate_column_suffix(self):
        left_df = pd.DataFrame({"employee_id": [1], "name": ["Alice"]})
        right_df = pd.DataFrame({"employee_id": [1], "name": ["Alicia"]})

        result = join_projects(left_df, right_df, "employee_id", "employee_id", "inner", "directory")

        assert "name" in result.columns
        assert "name_directory" in result.columns

    def test_join_projects_missing_column(self, sample_df):
        right_df = pd.DataFrame({"id": [1], "team": ["Sales"]})
        with pytest.raises(TransformationError, match="not found"):
            join_projects(sample_df, right_df, "missing", "id", "inner", None)


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

    def test_replay_join_projects(self, sample_df):
        details = {
            "join_projects_params": {
                "left_on": "name",
                "right_on": "name",
                "join_type": "left",
                "suffix": "directory",
                "right_project_snapshot_columns": ["name", "department"],
                "right_project_snapshot_rows": [["Alice", "Sales"], ["Bob", "Support"]],
            }
        }

        result = apply_logged_transformation(sample_df, "joinProjects", details)

        assert "department" in result.columns
        assert result.iloc[0]["department"] == "Sales"


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
    def test_export_project(self, client, sample_csv, db):
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
        export_response = client.get(f"/projects/{project_id}/export")
        assert export_response.status_code == 200
        assert export_response.headers["content-type"] == "text/csv; charset=utf-8"

        # Verify content is valid CSV
        content = export_response.content.decode("utf-8")
        reader = csv.reader(content.strip().splitlines())
        rows = list(reader)
        assert rows[0] == ["name", "age", "city"]
        assert len(rows) == 5  # header + 4 data rows

    def test_export_nonexistent_project(self, client):
        response = client.get("/projects/00000000-0000-0000-0000-000000000000/export")
        assert response.status_code == 404


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

    def test_join_projects_transform_and_log_snapshot(self, client, db, tmp_path):
        left_csv = tmp_path / "left.csv"
        left_csv.write_text("employee_id,name\n1,Alice\n2,Bob\n", encoding="utf-8")
        right_csv = tmp_path / "right.csv"
        right_csv.write_text("employee_id,department\n1,Sales\n3,Support\n", encoding="utf-8")

        with open(left_csv, "rb") as left_file:
            left_response = client.post(
                "/projects/upload",
                files={"file": ("left.csv", left_file, "text/csv")},
                data={"projectName": "Left Project", "projectDescription": "Left side"},
            )
        with open(right_csv, "rb") as right_file:
            right_response = client.post(
                "/projects/upload",
                files={"file": ("right.csv", right_file, "text/csv")},
                data={"projectName": "Right Project", "projectDescription": "Right side"},
            )

        left_project_id = left_response.json()["project_id"]
        right_project_id = right_response.json()["project_id"]

        transform_response = client.post(
            f"/projects/{left_project_id}/transform",
            json={
                "operation_type": "joinProjects",
                "join_projects_params": {
                    "right_project_id": right_project_id,
                    "left_on": "employee_id",
                    "right_on": "employee_id",
                    "join_type": "left",
                    "suffix": "hr",
                },
            },
        )

        assert transform_response.status_code == 200
        payload = transform_response.json()
        assert payload["columns"] == ["employee_id", "name", "department"]
        assert payload["rows"][0] == [1, "Alice", "Sales"]

        logs_response = client.get(f"/logs/{left_project_id}")
        assert logs_response.status_code == 200
        join_log = logs_response.json()[0]
        assert join_log["action_type"] == "joinProjects"
        assert join_log["action_details"]["join_projects_params"]["right_project_snapshot_columns"] == [
            "employee_id",
            "department",
        ]


class TestProjectsEndpoint:
    def test_list_projects_returns_all_projects(self, client, tmp_path):
        first_csv = tmp_path / "first.csv"
        first_csv.write_text("id,value\n1,alpha\n", encoding="utf-8")
        second_csv = tmp_path / "second.csv"
        second_csv.write_text("id,value\n2,beta\n", encoding="utf-8")

        for name, path in (("Project One", first_csv), ("Project Two", second_csv)):
            with open(path, "rb") as upload_file:
                response = client.post(
                    "/projects/upload",
                    files={"file": (path.name, upload_file, "text/csv")},
                    data={"projectName": name, "projectDescription": "List test"},
                )
            assert response.status_code == 200

        response = client.get("/projects")
        assert response.status_code == 200
        assert len(response.json()) == 2
