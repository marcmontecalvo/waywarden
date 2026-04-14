from dataclasses import dataclass


@dataclass(slots=True)
class ToolCall:
    name: str
    payload: dict[str, object]
