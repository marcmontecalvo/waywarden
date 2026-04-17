from dataclasses import dataclass


@dataclass(slots=True)
class BackupJob:
    id: str
    status: str
