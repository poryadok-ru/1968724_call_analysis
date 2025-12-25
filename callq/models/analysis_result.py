from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


@dataclass
class Evaluation:
    category: str
    criterion: str
    score_given: int
    max_score: int
    reason: str

    @staticmethod
    def from_list(items: List[Dict[str, Any]], criterion_mapping: Optional[Dict[Tuple[str, str], Tuple[str, str]]] = None) -> List[Evaluation]:
        """
        Создает список Evaluation из словарей ответа LLM.
        
        Args:
            items: Список словарей с данными оценок от LLM
            criterion_mapping: Маппинг для нормализации категорий и критериев (опционально)
        """
        from callq.utils.criterion_normalizer import normalize_category_and_criterion
        
        result: List[Evaluation] = []
        for item in items:
            llm_category = item.get('category', '')
            llm_criterion = item.get('criterion', '')
            
            if criterion_mapping:
                category, criterion = normalize_category_and_criterion(
                    llm_category, 
                    llm_criterion, 
                    criterion_mapping
                )
            else:
                import re
                category = re.sub(r'\s+', ' ', str(llm_category).strip())
                criterion = re.sub(r'\s+', ' ', str(llm_criterion).strip())
            
            score_given = item.get('score_given')
            max_score = item.get('max_score')
            
            if score_given is not None and max_score is not None:
                if score_given > max_score:
                    from callq import get_logger
                    logger = get_logger()
                    logger.warning(
                        f"Модель превысила max_score: score_given={score_given}, max_score={max_score}, "
                        f"category='{category}', criterion='{criterion}'. Ограничиваем до max_score."
                    )
                    score_given = max_score
                elif score_given < 0:
                    # Отрицательные баллы не допускаются
                    from callq import get_logger
                    logger = get_logger()
                    logger.warning(
                        f"Модель выдала отрицательный score: score_given={score_given}, "
                        f"category='{category}', criterion='{criterion}'. Устанавливаем 0."
                    )
                    score_given = 0
            
            result.append(
                Evaluation(
                    category=category,
                    criterion=criterion,
                    score_given=score_given,
                    max_score=max_score,
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
    def from_list(items: List[Dict[str, Any]], criterion_mapping: Optional[Dict[Tuple[str, str], Tuple[str, str]]] = None) -> List[Recommendation]:
        """
        Создает список Recommendation из словарей ответа LLM.
        
        Args:
            items: Список словарей с данными рекомендаций от LLM
            criterion_mapping: Маппинг для нормализации категорий (опционально)
        """
        from callq.utils.criterion_normalizer import normalize_text
        
        result: List[Recommendation] = []
        allowed_priorities = {'high', 'medium', 'low'}

        for item in items:
            if not item:
                continue

            priority_raw = item.get('priority')
            priority_clean = str(priority_raw).strip().lower() if priority_raw is not None else ""
            if priority_clean not in allowed_priorities:
                priority_clean = 'medium'

            issue = item.get('issue')
            recommendation_text = item.get('recommendation')

            if not issue or not recommendation_text:
                continue

            llm_category = item.get('category', '')
            if criterion_mapping:
                from callq.utils.criterion_normalizer import normalize_category_only
                category = normalize_category_only(llm_category, criterion_mapping)
            else:
                import re
                category = re.sub(r'\s+', ' ', str(llm_category).strip())

            result.append(Recommendation(
                category=category,
                issue=issue,
                recommendation=recommendation_text,
                priority=priority_clean,
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
            if not item:
                continue

            raw_agreement = item.get('agreement')
            agreement_text = ""
            if raw_agreement is not None:
                agreement_text = str(raw_agreement).strip()

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
            if not item:
                continue

            raw_description = item.get('reason_description')
            description = ""
            if raw_description is not None:
                description = str(raw_description).strip()

            if not description:
                continue

            raw_reason_type = item.get('reason_type')
            reason_type = str(raw_reason_type).strip() if raw_reason_type is not None else ""

            product_category = item.get('product_category')
            product_category_clean = (
                str(product_category).strip() if product_category is not None else None
            )

            result.append(DeclineReason(
                reason_type=reason_type or "",
                reason_description=description,
                product_category=product_category_clean or None,
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
    def from_list(data: Dict[str, Any], criterion_mapping: Optional[Dict[Tuple[str, str], Tuple[str, str]]] = None) -> Result:
        """
        Создает объект Result из словаря ответа LLM.
        
        Args:
            data: Словарь с данными анализа от LLM
            criterion_mapping: Маппинг для нормализации категорий и критериев (опционально)
        """
        decline_reasons_data = data.get('decline_reasons')
        decline_reasons = DeclineReason.from_list(decline_reasons_data) if decline_reasons_data else None
        
        evaluations = Evaluation.from_list(data.get('evaluations'), criterion_mapping)
        
        total_score = sum(eval.score_given for eval in evaluations if eval.score_given is not None)
        max_possible_score = sum(eval.max_score for eval in evaluations if eval.max_score is not None)
        
        if max_possible_score > 0:
            performance_percentage = int((total_score / max_possible_score) * 100)
        else:
            performance_percentage = 0
        
        return Result(
            is_sales_call=bool(data.get('is_sales_call')),
            total_score=total_score,
            max_possible_score=max_possible_score,
            performance_percentage=performance_percentage,

            evaluations=evaluations,
            recommendations=Recommendation.from_list(data.get('recommendations'), criterion_mapping),
            agreements=Agreement.from_list(data.get('agreements')),
            decline_reasons=decline_reasons
        )