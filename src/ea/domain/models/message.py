from dataclasses import dataclass


@dataclass(slots=True)
class Message:
    session_id: str
    role: str
    content: str
