from dataclasses import dataclass


@dataclass(slots=True)
class Session:
    id: str
