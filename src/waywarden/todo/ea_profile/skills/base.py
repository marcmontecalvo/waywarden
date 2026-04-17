from dataclasses import dataclass


@dataclass(slots=True)
class Skill:
    name: str
    description: str
    model_profile: str

    def as_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
            "model_profile": self.model_profile,
        }
