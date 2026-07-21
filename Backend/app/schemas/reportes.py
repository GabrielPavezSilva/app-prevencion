from pydantic import BaseModel
from typing import Optional, List

class DateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None

class ReportConfigSchema(BaseModel):
    dateRange: Optional[DateRange] = None
    selectedColumns: List[str] = []
    format: str = "excel"
