"""CSV import and export."""

from __future__ import annotations

from fastapi import APIRouter, File, Response, UploadFile

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.api.v1.students import Filters
from app.core.errors import bad_request
from app.schemas.prediction import ImportResult
from app.services import data_service

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/import", response_model=ImportResult)
def import_csv(
    admin: AdminUser,
    session: DbSession,
    file: UploadFile = File(description="CSV file; see docs/data-format.md for the columns"),
    dry_run: bool = True,
    skip_invalid: bool = False,
) -> ImportResult:
    """Validate a CSV and, when `dryRun` is false, import it. Per-row problems are returned."""
    content = file.file.read(data_service.MAX_BYTES + 1)
    if len(content) > data_service.MAX_BYTES:
        raise bad_request("The file is larger than 5 MB. Split it into smaller files.")
    return data_service.import_csv(session, admin, content, dry_run, skip_invalid)


@router.get("/export")
def export_csv(user: CurrentUser, session: DbSession, filters: Filters) -> Response:
    """Download the students matching the filters as CSV."""
    text, _ = data_service.export_csv(session, user, filters)
    return Response(
        content=text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pathway-students.csv"'},
    )
