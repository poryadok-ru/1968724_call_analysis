from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Evaluation:
    category: str
    criterion: str
    score_given: int
    max_score: int
    reason: str

    @staticmethod
    def from_list(items: List[Dict[str, Any]]) -> List[Evaluation]:
        result: List[Evaluation] = []
        for item in items:
            result.append(
                Evaluation(
                    category=item.get('category'),
                    criterion=item.get('criterion'),
                    score_given=item.get('score_given'),
                    max_score=item.get('max_score'),
                    reason=item.get('reason'),
                ),
            )
        return result

@dataclass
class Recommendation:
    category: str
    issue: str
    recommendation: str
    priority: str

    @staticmethod
    def from_list(items: List[Dict[str, Any]]) -> List[Recommendation]:
        result: List[Recommendation] = []
        for item in items:
            result.append(Recommendation(
                category=item.get('category'),
                issue=item.get('issue'),
                recommendation=item.get('recommendation'),
                priority=item.get('priority'),
            ))

        return result

@dataclass
class Agreement:
    amount: int
    agreement: str

    @staticmethod
    def from_list(items: List[Dict[str, Any]]) -> List[Agreement]:
        result: List[Agreement] = []
        for item in items:
            agreement_text = item.get('agreement')
            if not agreement_text:
                continue
                
            result.append(Agreement(
                amount=item.get('amount'),
                agreement=agreement_text,
            ))

        return result

@dataclass
class DeclineReason:
    reason_type: str
    reason_description: str
    product_category: Optional[str] = None

    @staticmethod
    def from_list(items: List[Dict[str, Any]]) -> List[DeclineReason]:
        result: List[DeclineReason] = []
        for item in items:
            result.append(DeclineReason(
                reason_type=item.get('reason_type'),
                reason_description=item.get('reason_description'),
                product_category=item.get('product_category'),
            ))

        return result

@dataclass
class Result:
    is_sales_call: bool
    total_score: int
    max_possible_score: int
    performance_percentage: int

    evaluations: List[Evaluation]
    recommendations: List[Recommendation]
    agreements: List[Agreement]
    decline_reasons: Optional[List[DeclineReason]] = None

    @staticmethod
    def from_list(data: Dict[str, Any]) -> Result:
        decline_reasons_data = data.get('decline_reasons')
        decline_reasons = DeclineReason.from_list(decline_reasons_data) if decline_reasons_data else None
        
        return Result(
            is_sales_call=bool(data.get('is_sales_call')),
            total_score=int(data.get('total_score')),
            max_possible_score=int(data.get('max_possible_score')),
            performance_percentage=int(data.get('performance_percentage')),

            evaluations=Evaluation.from_list(data.get('evaluations')),
            recommendations=Recommendation.from_list(data.get('recommendations')),
            agreements=Agreement.from_list(data.get('agreements')),
            decline_reasons=decline_reasons
        )