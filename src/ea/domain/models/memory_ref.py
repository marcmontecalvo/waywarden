from dataclasses import dataclass


@dataclass(slots=True)
class MemoryItem:
    id: str
    text: str
