"""EA inbox triage routine handler.

Classifies inbound items, drafts responses, and hits approval before
outbound actions can proceed.

Canonical references:
    - ADR 0005 (approval model)
    - ADR 0007 (good/bad patterns)
    - P5-3 #83, P5-4 #84
"""

from __future__ import annotations

from dataclasses import dataclass, field

from waywarden.services.approval_types import (
    ApprovalDecision,
    DeniedAbandon,
    Granted,
)
from waywarden.services.ea_task_service import (
    ApprovalDecisionRequest,
    CreateTaskRequest,
    EATaskService,
    RequestApprovalRequest,
    TransitionTaskRequest,
)


@dataclass(slots=True)
class InboxItem:
    """An item from the inbox to be triaged."""

    subject: str
    from_address: str
    body: str

    classification: str = "unknown"
    drafted_response: str = ""
    approved: bool = False


@dataclass(slots=True)
class TriageResult:
    """Result of the inbox triage routine."""

    items_triaged: int = 0
    items_approved: int = 0
    items_denied: int = 0
    items_malformed: int = 0
    items: list[InboxItem] = field(default_factory=list)


class EAIboxTriageHandler:
    """Triage routine for inbound inbox items.

    Flow per item:
    1. Classify (heuristic: valid subject → categorized)
    2. Draft a response
    3. Request approval checkpoint
    4. Apply decision: approve → draft response, deny → abandon

    Items with blank subjects are marked malformed and skipped.
    """

    # Heuristic classification keywords (purely for testing)
    _CLASSIFIERS: dict[str, str] = {
        "urgent": "urgent",
        "budget": "financial",
        "meeting": "scheduling",
        "request": "information",
        "vendor": "external",
    }

    def __init__(self, task_service: EATaskService | None = None) -> None:
        self.task_service = task_service or EATaskService()

    def run(
        self,
        items: list[InboxItem] | None = None,
        decisions: dict[str, ApprovalDecision] | None = None,
    ) -> TriageResult:
        """Execute the inbox triage routine.

        Args:
            items: Inbox items to classify and draft.
            decisions: Map from subject to the approval decision.

        Returns:
            A >>TriageResult``` summarising triage outcomes.
        """
        result = TriageResult()
        items = items or []
        decisions = decisions or {}

        for item in items:
            # Step 1: Validate - blank subject means malformed
            if not item.subject.strip():
                item.classification = "malformed"
                result.items_malformed += 1
                result.items.append(item)
                continue

            # Step 2: Classify
            item.classification = self._classify(item.subject)

            # Step 3: Draft response
            item.drafted_response = self._draft_response(item)

            # Step 4: Task assembly via EA task service
            task = self.task_service.create_task(
                CreateTaskRequest(
                    session_id="triage-sess",
                    title=f"Triage: {item.subject}",
                    objective=item.body,
                    acceptance_criteria=(f"classify.{item.classification}",),
                )
            )
            task_id = task["id"]

            # Step 5: Transition through pipeline
            self.task_service.transition_task(
                TransitionTaskRequest(task_id=task_id, state="planning")
            )
            self.task_service.transition_task(
                TransitionTaskRequest(task_id=task_id, state="executing")
            )

            # Step 6: Approval checkpoint
            self.task_service.request_approval(RequestApprovalRequest(task_id=task_id))

            # Step 7: Apply decision
            decision = decisions.get(item.subject, Granted())
            self.task_service.resolve_approval(
                ApprovalDecisionRequest(
                    task_id=task_id,
                    decision=decision,
                )
            )

            item.approved = isinstance(decision, Granted)
            result.items_triaged += 1
            if isinstance(decision, Granted):
                result.items_approved += 1
            elif isinstance(decision, DeniedAbandon):
                result.items_denied += 1

            result.items.append(item)

        return result

    def _classify(self, subject: str) -> str:
        """Heuristic classification by subject keywords."""
        lower = subject.lower()
        for keyword, category in self._CLASSIFIERS.items():
            if keyword in lower:
                return category
        return "general"

    def _draft_response(self, item: InboxItem) -> str:
        """Draft a standard response for a triaged item."""
        return (
            f"Subject: {item.subject}\n"
            f"Category: {item.classification}\n"
            f"Draft: Thank you for reaching out about {item.subject}.\n"
            f"Addressed to: {item.from_address}\n"
        )
