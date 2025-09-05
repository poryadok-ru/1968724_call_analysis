from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass
class PromptInput:
    custom_criteria: List[str]

    @staticmethod
    def from_dict(data: List[List[str]]) -> PromptInput:
        custom_criteria = []
        for d in data:
            custom_criteria.append(d[0])

        return PromptInput(
            custom_criteria=custom_criteria,
        )