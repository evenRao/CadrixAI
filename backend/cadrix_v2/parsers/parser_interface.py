from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from cadrix_v2.schemas import DesignIntent


@dataclass
class ParserOutput:
    intent: Optional[DesignIntent]
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class DesignParser(ABC):
    @abstractmethod
    def parse(self, prompt: str, requested_model_type: Optional[str] = None) -> ParserOutput:
        raise NotImplementedError
