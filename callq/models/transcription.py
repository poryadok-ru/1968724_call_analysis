from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


def _to_int(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


@dataclass
class Phrase:
    text: str
    start_time: float
    channel: str


@dataclass
class Transcription:
    phrases: List[Phrase]

    @staticmethod
    def from_dict(d: dict) -> Transcription:
        operator_id = _to_int(d.get("firstOperatorId"))
        
        transcription = Transcription(phrases=[])
        
        for part in d.get("transcriptionParts", []):
            for phrase_data in part.get("phrases", []):
                contact_id = phrase_data.get("contactId")
                channel = "operator" if contact_id == operator_id else "client"
                
                phrase = Phrase(
                    text=phrase_data.get("phraseText", ""),
                    start_time=_to_int(phrase_data.get("startTimeInMs", 0)),
                    channel=channel
                )
                transcription.phrases.append(phrase)
        
        return transcription