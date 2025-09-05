from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from callq.models import CallRecord
from callq.models.analysis_result import Result


@dataclass
class CallAnalysisReport:
    call_record: CallRecord
    analysis_result: Optional[Result] = None
    department_id: int = 1
    
    @property
    def call_id(self) -> int:
        return self.call_record.call.segmentId
    
    @property
    def start_time(self) -> datetime:
        return datetime.fromisoformat(self.call_record.call.startDate.replace('Z', '+00:00'))
    
    @property
    def finish_time(self) -> Optional[datetime]:
        if self.call_record.call.endDate:
            return datetime.fromisoformat(self.call_record.call.endDate.replace('Z', '+00:00'))
        return None