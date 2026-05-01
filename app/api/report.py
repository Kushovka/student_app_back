from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.services.report_service import (
    build_behavior_excel,
    build_behavior_docx,
    build_behavior_pdf,
    get_behavior_class_report_data,
)

from app.api.deps import get_current_user
from app.db.deps import get_db
from app.models.user import User
from app.schemas.report import (
    BehaviorClassReportRequest,
    BehaviorClassReportResponse,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


def build_export_filename(
    data: BehaviorClassReportRequest,
    extension: str,
) -> str:
    class_letter_map = str.maketrans(
        {
            "А": "A",
            "В": "B",
            "Е": "E",
            "К": "K",
            "М": "M",
            "Н": "N",
            "О": "O",
            "Р": "P",
            "С": "S",
            "Т": "T",
            "У": "Y",
            "Х": "X",
        }
    )
    class_letter = data.class_letter.strip().upper().translate(class_letter_map)
    class_name = f"{data.grade}{class_letter}"
    return (
        f"otchet_o_povedenii_{class_name}_"
        f"s_{data.date_from}_po_{data.date_to}.{extension}"
    )


@router.post("/behavior/export", response_model=BehaviorClassReportResponse)
def export_behavior_class_report(
    data: BehaviorClassReportRequest,
    format: Literal["json", "xlsx", "docx", "pdf"] = Query(default="json"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report_data = get_behavior_class_report_data(db, current_user, data)

    if format == "xlsx":
        output = build_behavior_excel(report_data)
        filename = build_export_filename(data, "xlsx")

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    if format == "docx":
        output = build_behavior_docx(report_data)
        filename = build_export_filename(data, "docx")

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if format == "pdf":
        output = build_behavior_pdf(report_data)
        filename = build_export_filename(data, "pdf")

        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return report_data
