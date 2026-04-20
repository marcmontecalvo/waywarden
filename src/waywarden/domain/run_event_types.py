"""RT-002 run event type catalog — exact 10 values, no extras."""

from typing import Literal

RunEventType = Literal[
    "run.created",
    "run.plan_ready",
    "run.execution_started",
    "run.progress",
    "run.approval_waiting",
    "run.resumed",
    "run.artifact_created",
    "run.completed",
    "run.failed",
    "run.cancelled",
]
