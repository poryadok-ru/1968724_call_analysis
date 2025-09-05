from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from callq.models.call import Call
from callq.models.transcription import Transcription


@dataclass
class CallRecord:
    call: Call

    transcription: Optional[Transcription] = None
    processed_at: Optional[datetime] = None
    
    @property
    def segment_id(self) -> int:
        return self.call.segmentId
    
    @property
    def has_transcription(self) -> bool:
        return self.transcription is not None
    
    @property
    def operator_info(self) -> str:
        return f"{self.call.operatorUserFullName or 'N/A'} ({self.call.operatorUserLogin or 'N/A'})"
    
    @property
    def transcription_text(self) -> str:
        if not self.transcription or not self.transcription.phrases:
            return ""
        
        return " ".join([phrase.text for phrase in self.transcription.phrases])
    
    @property
    def call_duration(self) -> int:
        return self.call.duration
    
    @property
    def phone_number(self) -> Optional[str]:
        return self.call.phoneNumber
    
    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "operator_id": self.call.operatorUserId,
            "operator_login": self.call.operatorUserLogin,
            "operator_name": self.call.operatorUserFullName,
            "phone_number": self.phone_number,
            "call_direction": self.call.callDirection,
            "start_date": self.call.startDate,
            "end_date": self.call.endDate,
            "duration": self.call_duration,
            "has_transcription": self.has_transcription,
            "transcription_text": self.transcription_text,
            "phrases_count": len(self.transcription.phrases) if self.transcription else 0,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }