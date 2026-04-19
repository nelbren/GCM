from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class ModelResponse:
    code: int
    provider: str
    model: Optional[str]
    content: Optional[str]
    usage: Optional[dict]
    elapsed: float
    error: Optional[str] = None


@dataclass
class ProviderInfo:
    name: str
    available: bool
    roles: List[str]
    priority: int
    query_fn: Callable[[str], tuple]
    models: List[str] = field(default_factory=list)
    reason_unavailable: Optional[str] = None


@dataclass
class CandidateMessage:
    provider: str
    model: Optional[str]
    content: str
    usage: Optional[dict]
    elapsed: float


@dataclass
class ExecutionPlan:
    generators: List[ProviderInfo]
    judge: Optional[ProviderInfo]
    refiner: Optional[ProviderInfo]
