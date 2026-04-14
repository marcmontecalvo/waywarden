from dataclasses import dataclass


@dataclass(slots=True)
class Approval:
    id: str
    action: str
    status: str = "pending"
