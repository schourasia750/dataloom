"""Transformation API endpoints for project operations.

All transformations are handled through a single unified /transform endpoint.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import database, models, schemas
from app.api.dependencies import get_project_or_404
from app.services import transformation_service as ts
from app.services.project_service import log_transformation
from app.utils.logging import get_logger
from app.utils.pandas_helpers import dataframe_to_response, read_csv_safe, save_csv_safe

logger = get_logger(__name__)

router = APIRouter()

COMPLEX_OPERATIONS = {"dropDuplicate", "advQueryFilter", "pivotTables", "dropNa"}


def _serialize_transform_steps(steps: list[schemas.TransformationInput]) -> list[dict]:
    """Convert validated transformation steps into JSON-serializable payloads."""
    return [step.model_dump(mode="json") for step in steps]


def _handle_basic_transform(df, transformation_input, materialize_read_only=False):
    """Apply a basic transformation and optionally persist changes.

    For operations that modify data (addRow, delRow, addCol, delCol, changeCellValue, fillEmpty),
    saves to disk and logs the transformation. For read-only operations (filter, sort),
    only returns the result.

    Returns:
        Tuple of (result_df, should_save).
    """
    op = transformation_input.operation_type

    if op == "filter":
        if not transformation_input.parameters:
            raise HTTPException(status_code=400, detail="Filter parameters required")
        p = transformation_input.parameters
        return ts.apply_filter(df, p.column, p.condition, p.value), materialize_read_only

    elif op == "sort":
        if not transformation_input.sort_params:
            raise HTTPException(status_code=400, detail="Sort parameters required")
        p = transformation_input.sort_params
        return ts.apply_sort(df, p.column, p.ascending), materialize_read_only

    elif op == "addRow":
        if not transformation_input.row_params:
            raise HTTPException(status_code=400, detail="Row parameters required")
        return ts.add_row(df, transformation_input.row_params.index), True

    elif op == "delRow":
        if not transformation_input.row_params:
            raise HTTPException(status_code=400, detail="Row parameters required")
        return ts.delete_row(df, transformation_input.row_params.index), True

    elif op == "addCol":
        if not transformation_input.add_col_params:
            raise HTTPException(status_code=400, detail="Column parameters required")
        p = transformation_input.add_col_params
        return ts.add_column(df, p.index, p.name), True

    elif op == "delCol":
        if not transformation_input.del_col_params:
            raise HTTPException(status_code=400, detail="Column index required")
        return ts.delete_column(df, transformation_input.del_col_params.index), True

    elif op == "changeCellValue":
        if not transformation_input.change_cell_value:
            raise HTTPException(status_code=400, detail="Cell value parameters required")
        p = transformation_input.change_cell_value
        return ts.change_cell_value(df, p.row_index, p.col_index, p.fill_value), True

    elif op == "fillEmpty":
        if not transformation_input.fill_empty_params:
            raise HTTPException(status_code=400, detail="Fill parameters required")
        p = transformation_input.fill_empty_params
        return ts.fill_empty(df, p.fill_value, p.index), True

    elif op == "renameCol":
        if not transformation_input.rename_col_params:
            raise HTTPException(status_code=400, detail="Rename column parameters required")
        p = transformation_input.rename_col_params
        return ts.rename_column(df, p.col_index, p.new_name), True

    elif op == "castDataType":
        if not transformation_input.cast_data_type_params:
            raise HTTPException(status_code=400, detail="Cast data type parameters required")
        p = transformation_input.cast_data_type_params
        return ts.cast_data_type(df, p.column, p.target_type), True

    elif op == "trimWhitespace":
        if not transformation_input.trim_whitespace_params:
            raise HTTPException(status_code=400, detail="Trim whitespace parameters required")
        p = transformation_input.trim_whitespace_params
        return ts.trim_whitespace(df, p.column), True

    elif op == "computedFormula":
        if not transformation_input.computed_formula_params:
            raise HTTPException(status_code=400, detail="Computed formula parameters required")
        p = transformation_input.computed_formula_params
        return ts.compute_formula_column(df, p.new_column, p.formula, p.insert_index), True

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported operation: {op}")


def _handle_complex_transform(df, transformation_input, materialize_read_only=False):
    """Apply a complex transformation.

    Returns:
        Tuple of (result_df, should_save).
    """
    op = transformation_input.operation_type

    if op == "dropDuplicate":
        if not transformation_input.drop_duplicate:
            raise HTTPException(status_code=400, detail="Drop duplicate parameters required")
        p = transformation_input.drop_duplicate
        return ts.drop_duplicates(df, p.columns, p.keep), True

    elif op == "advQueryFilter":
        if not transformation_input.adv_query:
            raise HTTPException(status_code=400, detail="Query parameter required")
        return ts.advanced_query(df, transformation_input.adv_query.query), materialize_read_only

    elif op == "pivotTables":
        if not transformation_input.pivot_query:
            raise HTTPException(status_code=400, detail="Pivot parameters required")
        p = transformation_input.pivot_query
        return ts.pivot_table(df, p.index, p.value, p.column, p.aggfun), materialize_read_only

    elif op == "dropNa":
        columns = None
        if transformation_input.drop_na_params:
            columns = transformation_input.drop_na_params.columns
        return ts.drop_na(df, columns), True

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported operation: {op}")


def _run_transform(df, transformation_input, materialize_read_only=False):
    """Dispatch a transformation and optionally materialize preview-only operations."""
    op = transformation_input.operation_type
    if op in COMPLEX_OPERATIONS:
        return _handle_complex_transform(df, transformation_input, materialize_read_only=materialize_read_only)
    return _handle_basic_transform(df, transformation_input, materialize_read_only=materialize_read_only)


@router.post("/{project_id}/transform", response_model=schemas.BasicQueryResponse)
async def transform_project(
    project_id: uuid.UUID,
    transformation_input: schemas.TransformationInput,
    db: Session = Depends(database.get_db),
):
    """Apply a transformation to a project.

    Routes to the appropriate internal handler based on operation_type.
    """
    project = get_project_or_404(project_id, db)
    df = read_csv_safe(project.file_path)

    op = transformation_input.operation_type

    try:
        result_df, should_save = _run_transform(df, transformation_input)
    except ts.TransformationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if should_save:
        save_csv_safe(result_df, project.file_path)
        log_transformation(
            db,
            project_id,
            transformation_input.operation_type,
            transformation_input.model_dump(mode="json"),
        )

    resp = dataframe_to_response(result_df)
    return {
        "project_id": project_id,
        "operation_type": transformation_input.operation_type,
        **resp,
    }


@router.get("/{project_id}/pipelines", response_model=list[schemas.TransformationPipelineResponse])
def list_pipelines(project_id: uuid.UUID, db: Session = Depends(database.get_db)):
    """List reusable transformation pipelines for a project."""
    get_project_or_404(project_id, db)
    pipelines = (
        db.query(models.TransformationPipeline)
        .filter(models.TransformationPipeline.project_id == project_id)
        .order_by(models.TransformationPipeline.created_at.desc())
        .all()
    )
    return pipelines


@router.post("/{project_id}/pipelines", response_model=schemas.TransformationPipelineResponse)
def create_pipeline(
    project_id: uuid.UUID,
    pipeline_input: schemas.TransformationPipelineCreate,
    db: Session = Depends(database.get_db),
):
    """Save a reusable transformation pipeline for a project."""
    get_project_or_404(project_id, db)

    serialized_steps = (
        _serialize_transform_steps(pipeline_input.steps)
        if pipeline_input.steps
        else [
            log.action_details
            for log in db.query(models.ProjectChangeLog)
            .filter(models.ProjectChangeLog.project_id == project_id)
            .order_by(models.ProjectChangeLog.timestamp)
            .all()
        ]
    )

    if not serialized_steps:
        raise HTTPException(status_code=400, detail="No transformations available to save as a pipeline")

    pipeline = models.TransformationPipeline(
        project_id=project_id,
        name=pipeline_input.name,
        description=pipeline_input.description,
        steps=serialized_steps,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return pipeline


@router.post("/{project_id}/pipelines/{pipeline_id}/apply", response_model=schemas.BasicQueryResponse)
def apply_pipeline(
    project_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    db: Session = Depends(database.get_db),
):
    """Apply a saved pipeline to the current project and persist the result."""
    project = get_project_or_404(project_id, db)
    pipeline = (
        db.query(models.TransformationPipeline)
        .filter(
            models.TransformationPipeline.id == pipeline_id,
            models.TransformationPipeline.project_id == project_id,
        )
        .first()
    )
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    df = read_csv_safe(project.file_path)

    try:
        result_df = df
        for raw_step in pipeline.steps:
            step = schemas.TransformationInput.model_validate(raw_step)
            result_df, _ = _run_transform(result_df, step, materialize_read_only=True)
    except ts.TransformationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    save_csv_safe(result_df, project.file_path)
    log_transformation(
        db,
        project_id,
        schemas.OperationType.applyPipeline,
        {
            "pipeline_id": str(pipeline.id),
            "pipeline_name": pipeline.name,
            "steps": pipeline.steps,
        },
    )

    resp = dataframe_to_response(result_df)
    return {
        "project_id": project_id,
        "operation_type": schemas.OperationType.applyPipeline,
        **resp,
    }
