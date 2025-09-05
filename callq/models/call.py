from dataclasses import dataclass
from typing import Optional


def _safe_int(v, default=0) -> int:
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def _safe_bool(v, default=False) -> bool:
    return bool(v) if v is not None else default


@dataclass
class Call:
    """Модель звонка из T-Bank API"""
    segmentId: int
    startDate: str
    endDate: Optional[str]
    duration: int  # Полная длительность звонка в секундах
    operatorUserId: int
    operatorUserLogin: Optional[str]
    operatorUserFullName: Optional[str]
    callDirection: Optional[str]
    phoneNumber: Optional[str]
    
    @staticmethod
    def from_dict(d: dict) -> "Call":
        """Создание объекта Call из словаря API"""
        return Call(
            segmentId=_safe_int(d.get('segmentId') or d.get('id')),
            startDate=d.get("startDate", ""),
            endDate=d.get("endDate"),
            duration=_safe_int(d.get("duration")),
            operatorUserId=_safe_int(d.get("operatorUserId")),
            operatorUserLogin=d.get("operatorUserLogin"),
            operatorUserFullName=d.get("operatorUserFullName"),
            callDirection=d.get("callDirection"),
            phoneNumber=d.get("clientPhoneNumber"),
        )
