"""Export endpoints for shortlist and candidate reports."""

from __future__ import annotations

import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.services.export_service import ExportOptions, export_candidates


router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    includeScores: bool = True
    includeSkills: bool = True
    includeExperience: bool = True
    includeEducation: bool = True
    sortBy: str = "score"
    criteria_id: Optional[int] = None


@router.post("/{export_format}")
def export_candidates_endpoint(export_format: str, payload: ExportRequest, db: Session = Depends(get_db)):
    options = ExportOptions.from_payload(payload)
    try:
        body, media_type, filename = export_candidates(db, export_format, options)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return StreamingResponse(
        io.BytesIO(body),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
