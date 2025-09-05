from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class Message:
    content: str
    role: str
    tool_calls: Optional[Any] = None
    function_call: Optional[Any] = None
    annotations: Optional[Any] = None


@dataclass
class Choice:
    finish_reason: str
    index: int
    message: Message


@dataclass
class Usage:
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    completion_tokens_details: Optional[Any] = None
    prompt_tokens_details: Optional[Dict] = None
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class LLMResponse:
    id: str
    created: int
    model: str
    object: str
    system_fingerprint: Optional[str]
    choices: List[Choice]
    usage: Usage
    
    @classmethod
    def from_dict(cls, data: dict) -> LLMResponse:
        choices = [
            Choice(
                finish_reason=c['finish_reason'],
                index=c['index'],
                message=Message(**c['message'])
            )
            for c in data['choices']
        ]
        
        usage = Usage(**data['usage'])
        
        return cls(
            id=data['id'],
            created=data['created'],
            model=data['model'],
            object=data['object'],
            system_fingerprint=data.get('system_fingerprint'),
            choices=choices,
            usage=usage
        )
    
    def get_content(self) -> str:
        if self.choices:
            return self.choices[0].message.content
        return ""
    
    def get_tokens_used(self) -> int:
        return self.usage.total_tokens