import psycopg2
from psycopg2.extras import execute_values
from contextlib import contextmanager
from typing import List, Optional
import time

from callq import get_logger
from callq.models.db_models import OperatorDTO, CallDTO, TranscriptDTO, EvaluationDTO, RecommendationDTO, AgreementDTO, DeclineReasonDTO


class PostgresClient:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.logger = get_logger()
    
    @contextmanager
    def get_connection(self):
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                conn = psycopg2.connect(self.connection_string)
                try:
                    yield conn
                    conn.commit()
                    return
                except Exception:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            except psycopg2.OperationalError as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Ошибка подключения к БД (попытка {attempt + 1}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                else:
                    self.logger.error(f"Не удалось подключиться к БД после {max_retries} попыток")
                    raise
    
    def upsert_call(self, call: CallDTO):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO calls (
                        id, start_time, finish_time, operator_id, department_id, phone_number,
                        total_score, max_score, performance_percentage
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    call.id, call.start_time, call.finish_time, call.operator_id,
                    call.department_id, call.phone_number, call.total_score,
                    call.max_score, call.performance_percentage
                ))
    
    def upsert_transcript(self, transcript: TranscriptDTO):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO call_transcripts (call_id, transcript)
                    VALUES (%s, %s)
                    ON CONFLICT (call_id) DO UPDATE SET transcript = EXCLUDED.transcript
                """, (transcript.call_id, transcript.transcript))
    
    def insert_evaluations(self, evaluations: List[EvaluationDTO]):
        if not evaluations:
            return
            
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for eval in evaluations:
                    cur.execute("""
                        INSERT INTO call_evaluations (call_id, category, criterion, score, max_score, reason)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        eval.call_id, eval.category, eval.criterion,
                        eval.score, eval.max_score, eval.reason
                    ))
    
    def insert_recommendations(self, recommendations: List[RecommendationDTO]):
        if not recommendations:
            return
            
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for rec in recommendations:
                    cur.execute("""
                        INSERT INTO call_recommendations (call_id, category, issue, recommendation, priority)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        rec.call_id, rec.category, rec.issue,
                        rec.recommendation, rec.priority
                    ))
    
    def insert_agreements(self, agreements: List[AgreementDTO]):
        if not agreements:
            return

        with self.get_connection() as conn:
            with conn.cursor() as cur:
                for agr in agreements:
                    cur.execute("""
                        INSERT INTO agreements (call_id, amount, agreement)
                        VALUES (%s, %s, %s)
                    """, (
                        agr.call_id, agr.amount, agr.agreement
                    ))

    def save_call_complete(self, call: CallDTO, transcript: Optional[TranscriptDTO], 
                          evaluations: List[EvaluationDTO], recommendations: List[RecommendationDTO], 
                          agreements: List[AgreementDTO], decline_reasons: List[DeclineReasonDTO] = None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO calls (
                        id, start_time, finish_time, operator_id, department_id, phone_number,
                        total_score, max_score, performance_percentage
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    call.id, call.start_time, call.finish_time, call.operator_id,
                    call.department_id, call.phone_number, call.total_score,
                    call.max_score, call.performance_percentage
                ))

                if transcript:
                    cur.execute("""
                        INSERT INTO call_transcripts (call_id, transcript)
                        VALUES (%s, %s)
                        ON CONFLICT (call_id) DO UPDATE SET transcript = EXCLUDED.transcript
                    """, (transcript.call_id, transcript.transcript))

                if evaluations:
                    eval_data = [
                        (eval.call_id, eval.category, eval.criterion, eval.score, eval.max_score, eval.reason)
                        for eval in evaluations
                    ]
                    execute_values(cur, """
                        INSERT INTO call_evaluations (call_id, category, criterion, score, max_score, reason)
                        VALUES %s
                    """, eval_data)

                if recommendations:
                    rec_data = [
                        (rec.call_id, rec.category, rec.issue, rec.recommendation, rec.priority)
                        for rec in recommendations
                    ]
                    execute_values(cur, """
                        INSERT INTO call_recommendations (call_id, category, issue, recommendation, priority)
                        VALUES %s
                    """, rec_data)

                if agreements:
                    agr_data = [
                        (agr.call_id, agr.amount, agr.agreement)
                        for agr in agreements
                    ]
                    execute_values(cur, """
                        INSERT INTO agreements (call_id, amount, agreement)
                        VALUES %s
                    """, agr_data)

                if decline_reasons:
                    decline_data = [
                        (reason.call_id, reason.reason_type, reason.reason_description, reason.product_category)
                        for reason in decline_reasons
                    ]
                    execute_values(cur, """
                        INSERT INTO call_decline_reasons (call_id, reason_type, reason_description, product_category)
                        VALUES %s
                    """, decline_data)
