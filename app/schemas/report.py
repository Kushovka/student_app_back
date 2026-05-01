from datetime import date

from pydantic import BaseModel


class BehaviorClassReportRequest(BaseModel):
    grade: int
    class_letter: str
    date_from: date
    date_to: date


class BehaviorReportRow(BaseModel):
    full_name: str
    class_name: str
    subject: str
    date: date
    violation: str


class BehaviorClassReportResponse(BaseModel):
    school_id: str
    grade: int
    class_letter: str
    date_from: date
    date_to: date
    total: int
    items: list[BehaviorReportRow]
