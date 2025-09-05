from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Criterion:
    category: str
    indicator: str
    comment: str
    score: int
    criteria: str

    @staticmethod
    def parse_criterion(data: List[List[str]]) -> List[Criterion]:
        check_list = []
        current_category = ""

        for index, row in enumerate(data[1:]):
            if len(row) == 1:
                current_category = row[0]
                continue

            if len(row) > 1:
                check_list.append(Criterion(
                    category=current_category,
                    indicator=row[0],
                    comment=row[1],
                    score=row[2],
                    criteria=row[3],
                ))
                continue

            return check_list

        return check_list