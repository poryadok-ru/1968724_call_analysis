from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict

def _to_int(v, default=0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default

def _to_str(v, default=None) -> str:
    try:
        return str(v)
    except (TypeError, ValueError):
        return default

@dataclass
class ItemAutocomplete:
    id: int
    name: str
    externalId: Optional[str]
    breadCrumbs: Optional[str]
    type: Optional[str]

    @staticmethod
    def from_dict(data: Dict) -> ItemAutocomplete:
        return ItemAutocomplete(
            id=_to_int(data.get('id')),
            name=_to_str(data.get("name")),
            externalId=_to_str(data.get('externalId')),
            breadCrumbs=_to_str(data.get('breadCrumbs')),
            type=_to_str(data.get('type')),
        )


@dataclass
class Autocomplete:
    Items: Optional[List[ItemAutocomplete]]

    @staticmethod
    def from_dict(data: List[Dict]) -> Autocomplete:
        items: List[ItemAutocomplete] = []
        for item in data:
            items.append(ItemAutocomplete.from_dict(item))

        return Autocomplete(
            Items=items,
        )

