from typing import List

from callq import get_logger
from callq.clients.postgres import PostgresClient
from callq.models import CallDTO, TranscriptDTO, EvaluationDTO, RecommendationDTO, AgreementDTO, DeclineReasonDTO


def save_call_analysis_to_db(postgres_client: PostgresClient, report, department_id: int):
    """Сохранить один CallAnalysisReport в БД"""

    logger = get_logger()
    logger.info(f"Сохранение звона: {report.call_id}")

    call_dto = CallDTO(
        id=report.call_id,
        start_time=report.start_time,
        finish_time=report.finish_time,
        operator_id=report.call_record.call.operatorUserId,
        department_id=department_id,
        phone_number=report.call_record.call.phoneNumber,
        total_score=report.analysis_result.total_score if report.analysis_result else None,
        max_score=report.analysis_result.max_possible_score if report.analysis_result else None,
        performance_percentage=report.analysis_result.performance_percentage if report.analysis_result else None
    )

    transcript_dto = None
    if report.call_record.transcription:
        transcript_text = "\n".join([
            f"{phrase.channel}: {phrase.text}" 
            for phrase in report.call_record.transcription.phrases
        ])
        transcript_dto = TranscriptDTO(
            call_id=report.call_id,
            transcript=transcript_text
        )

    evaluations = []
    recommendations = []
    agreements = []
    decline_reasons = []
    
    if report.analysis_result:
        evaluations = []
        skipped_count = 0
        for eval in report.analysis_result.evaluations:
            if eval.score_given is None or eval.max_score is None:
                skipped_count += 1
                logger.warning(
                    f"Пропущена оценка для звонка {report.call_id}: "
                    f"category='{eval.category}', criterion='{eval.criterion}', "
                    f"score_given={eval.score_given}, max_score={eval.max_score}"
                )
                continue
            
            evaluations.append(
                EvaluationDTO(
                    call_id=report.call_id,
                    category=eval.category,
                    criterion=eval.criterion,
                    score=eval.score_given,
                    max_score=eval.max_score,
                    reason=eval.reason
                )
            )
        
        if skipped_count > 0:
            logger.warning(
                f"Для звонка {report.call_id} пропущено {skipped_count} оценок с отсутствующими значениями"
            )
        
        recommendations = [
            RecommendationDTO(
                call_id=report.call_id,
                category=rec.category,
                issue=rec.issue,
                recommendation=rec.recommendation,
                priority=rec.priority
            )
            for rec in report.analysis_result.recommendations
        ]

        agreements = [
            AgreementDTO(
                call_id=report.call_id,
                amount=agr.amount,
                agreement=agr.agreement
            )
            for agr in report.analysis_result.agreements
        ]

        if report.analysis_result.decline_reasons:
            decline_reasons = [
                DeclineReasonDTO(
                    call_id=report.call_id,
                    reason_type=reason.reason_type,
                    reason_description=reason.reason_description,
                    product_category=reason.product_category
                )
                for reason in report.analysis_result.decline_reasons
            ]

    postgres_client.save_call_complete(call_dto, transcript_dto, evaluations, recommendations, agreements, decline_reasons)


def save_batch_to_db(postgres_client: PostgresClient, reports: List, department_id: int):
    logger = get_logger()
    
    for report in reports:
        save_call_analysis_to_db(postgres_client, report, department_id)
    
    logger.info(f"Saved {len(reports)} call analyses to database")