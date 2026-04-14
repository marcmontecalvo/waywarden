from dataclasses import dataclass


@dataclass(slots=True)
class KnowledgeHit:
    id: str
    title: str
    snippet: str
