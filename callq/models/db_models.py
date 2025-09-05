from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class OperatorDTO:
    id: int
    full_name: str


@dataclass
class CallDTO:
    id: int
    start_time: datetime
    finish_time: Optional[datetime]
    operator_id: int
    department_id: int
    phone_number: Optional[str]
    total_score: Optional[float]
    max_score: Optional[float]
    performance_percentage: Optional[float]


@dataclass
class TranscriptDTO:
    call_id: int
    transcript: str


@dataclass
class EvaluationDTO:
    call_id: int
    category: str
    criterion: str
    score: float
    max_score: float
    reason: Optional[str]


@dataclass
class RecommendationDTO:
    call_id: int
    category: str
    issue: str
    recommendation: str
    priority: str

@dataclass
class AgreementDTO:
    call_id: int
    amount: float
    agreement: str


@dataclass
class DeclineReasonDTO:
    call_id: int
    reason_type: Optional[str]
    reason_description: str
    product_category: Optional[str]
