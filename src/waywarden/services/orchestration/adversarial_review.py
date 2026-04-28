"""Adversarial-review routine for pipeline review checkpoints."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from waywarden.domain.ids import RunEventId, RunId
from waywarden.domain.manifest.tool_policy import ToolDecision, ToolPolicy
from waywarden.domain.pipeline import PipelineOutcome
from waywarden.domain.run_event import Actor, Causation, RunEvent
from waywarden.services.approval_engine import ApprovalEngine

FindingClass = Literal[
    "prompt_injection",
    "approval_boundary_misuse",
    "malformed_memory_knowledge",
    "destructive_tool_misuse",
]
FindingSeverity = Literal["medium", "high", "critical"]
GateDecision = Literal["continue", "abort", "branch"]
ReviewStatus = Literal["completed", "aborted"]


@dataclass(frozen=True, slots=True)
class AdversarialFinding:
    """Typed adversarial finding emitted by a dedicated detector."""

    finding_class: FindingClass
    severity: FindingSeverity
    summary: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ApprovalExplanation:
    """Metadata explaining how policy and approval routing gated handback."""

    gate_decision: GateDecision
    approval_ids: tuple[str, ...]
    policy_preset: str
    policy_decisions: Mapping[str, ToolDecision]
    rationale: str

    def as_payload(self) -> dict[str, object]:
        return {
            "gate_decision": self.gate_decision,
            "approval_ids": self.approval_ids,
            "policy_preset": self.policy_preset,
            "policy_decisions": dict(self.policy_decisions),
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class AdversarialReviewInput:
    """Provider-neutral input artifact slice reviewed at a checkpoint."""

    run_id: str
    pipeline_id: str
    node_id: str
    input_artifact_ref: str
    input_artifact_kind: str
    handback_text: str = ""
    tool_calls: tuple[Mapping[str, object], ...] = ()
    memory_items: tuple[Mapping[str, object], ...] = ()
    knowledge_items: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class AdversarialReviewResult:
    """Result of adversarial review and the corresponding pipeline gate."""

    findings: tuple[AdversarialFinding, ...]
    gate_decision: GateDecision
    pipeline_outcome: PipelineOutcome
    status: ReviewStatus
    approval_explanation: ApprovalExplanation
    events: tuple[RunEvent, ...]
    handback_metadata: Mapping[str, Any]


class AdversarialReviewRoutine:
    """Runs deterministic adversarial detectors at a pipeline checkpoint."""

    def __init__(
        self,
        *,
        approval_engine: ApprovalEngine,
        tool_policy: ToolPolicy,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._approval_engine = approval_engine
        self._tool_policy = tool_policy
        self._now = now or (lambda: datetime.now(UTC))

    async def review(self, input: AdversarialReviewInput) -> AdversarialReviewResult:
        """Detect adversarial findings, route them through policy/approval, and gate."""
        findings = self._detect(input)
        policy_decisions: dict[str, ToolDecision] = {
            finding.finding_class: self._policy_decision_for(finding) for finding in findings
        }
        gate_decision = self._gate_decision(findings, policy_decisions)
        approval_ids = await self._request_approval(input, findings, gate_decision)
        explanation = ApprovalExplanation(
            gate_decision=gate_decision,
            approval_ids=approval_ids,
            policy_preset=self._tool_policy.preset,
            policy_decisions=policy_decisions,
            rationale=self._rationale(findings, gate_decision),
        )
        events = await self._emit_finding_events(input, findings, explanation)
        pipeline_outcome: PipelineOutcome = "success" if gate_decision == "continue" else "failure"
        status: ReviewStatus = "aborted" if gate_decision == "abort" else "completed"
        return AdversarialReviewResult(
            findings=findings,
            gate_decision=gate_decision,
            pipeline_outcome=pipeline_outcome,
            status=status,
            approval_explanation=explanation,
            events=events,
            handback_metadata={
                "input_artifact_ref": input.input_artifact_ref,
                "input_artifact_kind": input.input_artifact_kind,
                "approval_explanation": explanation.as_payload(),
            },
        )

    def _detect(self, input: AdversarialReviewInput) -> tuple[AdversarialFinding, ...]:
        findings: list[AdversarialFinding] = []
        if self._has_prompt_injection(input.handback_text):
            findings.append(
                AdversarialFinding(
                    finding_class="prompt_injection",
                    severity="high",
                    summary="Handback attempts to override instructions or reveal hidden prompts.",
                    evidence_refs=(f"{input.input_artifact_ref}#handback",),
                )
            )
        if self._has_approval_boundary_misuse(input.handback_text):
            findings.append(
                AdversarialFinding(
                    finding_class="approval_boundary_misuse",
                    severity="high",
                    summary="Handback attempts to bypass or self-grant an approval boundary.",
                    evidence_refs=(f"{input.input_artifact_ref}#handback",),
                )
            )
        malformed_refs = self._malformed_memory_knowledge_refs(input)
        if malformed_refs:
            findings.append(
                AdversarialFinding(
                    finding_class="malformed_memory_knowledge",
                    severity="medium",
                    summary="Memory or knowledge input is missing required reference fields.",
                    evidence_refs=malformed_refs,
                )
            )
        destructive_refs = self._destructive_tool_refs(input)
        if destructive_refs:
            findings.append(
                AdversarialFinding(
                    finding_class="destructive_tool_misuse",
                    severity="critical",
                    summary="Tool call attempts destructive filesystem or system mutation.",
                    evidence_refs=destructive_refs,
                )
            )
        return tuple(findings)

    @staticmethod
    def _has_prompt_injection(text: str) -> bool:
        lowered = text.lower()
        needles = (
            "ignore previous instructions",
            "ignore all previous instructions",
            "reveal system prompt",
            "developer message",
            "system message",
        )
        return any(needle in lowered for needle in needles)

    @staticmethod
    def _has_approval_boundary_misuse(text: str) -> bool:
        lowered = text.lower()
        needles = (
            "auto-approve",
            "self-approve",
            "bypass approval",
            "skip approval",
            "without approval",
        )
        return any(needle in lowered for needle in needles)

    @staticmethod
    def _malformed_memory_knowledge_refs(input: AdversarialReviewInput) -> tuple[str, ...]:
        refs: list[str] = []
        for index, item in enumerate(input.memory_items):
            if not _non_empty_str(item.get("id")) or not _non_empty_str(item.get("content")):
                refs.append(f"{input.input_artifact_ref}#memory[{index}]")
        for index, item in enumerate(input.knowledge_items):
            if not _non_empty_str(item.get("id")) or not _non_empty_str(item.get("source")):
                refs.append(f"{input.input_artifact_ref}#knowledge[{index}]")
        return tuple(refs)

    @staticmethod
    def _destructive_tool_refs(input: AdversarialReviewInput) -> tuple[str, ...]:
        refs: list[str] = []
        destructive_tokens = (
            "rm -rf",
            "mkfs",
            "diskutil erase",
            "format ",
            "git reset --hard",
            "shutdown",
        )
        for index, call in enumerate(input.tool_calls):
            command = str(call.get("command", "")).lower()
            action = str(call.get("action", "")).lower()
            if any(token in command for token in destructive_tokens) or action in {
                "delete",
                "destroy",
                "format",
            }:
                refs.append(f"{input.input_artifact_ref}#tool_calls[{index}]")
        return tuple(refs)

    def _policy_decision_for(self, finding: AdversarialFinding) -> ToolDecision:
        action = finding.finding_class
        for rule in self._tool_policy.rules:
            if rule.tool != "adversarial_review":
                continue
            if rule.action is not None and rule.action != action:
                continue
            return rule.decision
        if finding.finding_class == "destructive_tool_misuse":
            return "forbidden"
        return self._tool_policy.default_decision

    @staticmethod
    def _gate_decision(
        findings: tuple[AdversarialFinding, ...],
        policy_decisions: Mapping[str, ToolDecision],
    ) -> GateDecision:
        if not findings:
            return "continue"
        if any(
            finding.finding_class == "destructive_tool_misuse"
            or policy_decisions[finding.finding_class] == "forbidden"
            for finding in findings
        ):
            return "abort"
        return "branch"

    async def _request_approval(
        self,
        input: AdversarialReviewInput,
        findings: tuple[AdversarialFinding, ...],
        gate_decision: GateDecision,
    ) -> tuple[str, ...]:
        if not findings:
            return ()
        capability = (
            f"adversarial_review.{findings[0].finding_class}"
            if len(findings) == 1
            else "adversarial_review.multiple"
        )
        approval = await self._approval_engine.request(
            run_id=input.run_id,
            approval_kind="adversarial_review",
            summary=(
                f"Adversarial review {gate_decision}: "
                f"{', '.join(f.finding_class for f in findings)}"
            ),
            requested_capability=capability,
            checkpoint_ref=f"{input.pipeline_id}:{input.node_id}",
        )
        return (str(approval.id),)

    async def _emit_finding_events(
        self,
        input: AdversarialReviewInput,
        findings: tuple[AdversarialFinding, ...],
        explanation: ApprovalExplanation,
    ) -> tuple[RunEvent, ...]:
        if not findings:
            event = await self._append_progress_event(
                input=input,
                finding=None,
                explanation=explanation,
            )
            return (event,)
        events: list[RunEvent] = []
        for finding in findings:
            events.append(
                await self._append_progress_event(
                    input=input,
                    finding=finding,
                    explanation=explanation,
                )
            )
        return tuple(events)

    async def _append_progress_event(
        self,
        *,
        input: AdversarialReviewInput,
        finding: AdversarialFinding | None,
        explanation: ApprovalExplanation,
    ) -> RunEvent:
        next_seq = (await self._approval_engine.events.latest_seq(input.run_id)) + 1
        payload: dict[str, object] = {
            "phase": "review",
            "milestone": "findings_recorded",
            "milestone_ref": "review.findings_recorded",
            "run_id": input.run_id,
            "pipeline_id": input.pipeline_id,
            "node_id": input.node_id,
            "input_artifact_ref": input.input_artifact_ref,
            "input_artifact_kind": input.input_artifact_kind,
            "finding_class": "none",
            "finding_count": len(explanation.policy_decisions),
            "gate_decision": explanation.gate_decision,
            "approval_explanation": explanation.as_payload(),
        }
        if finding is not None:
            payload.update(
                {
                    "finding_class": finding.finding_class,
                    "severity": finding.severity,
                    "summary": finding.summary,
                    "evidence_refs": finding.evidence_refs,
                    "policy_decision": explanation.policy_decisions[finding.finding_class],
                }
            )

        event = RunEvent(
            id=RunEventId(f"evt-{input.run_id}-adversarial-{uuid4().hex}"),
            run_id=RunId(input.run_id),
            seq=next_seq,
            type="run.progress",
            payload=payload,
            timestamp=self._now(),
            causation=Causation(
                event_id=None,
                action="adversarial_review.findings_recorded",
                request_id=input.pipeline_id,
            ),
            actor=Actor(
                kind="policy-engine",
                id="adversarial-review",
                display="adversarial-review",
            ),
        )
        return await self._approval_engine.events.append(event)

    @staticmethod
    def _rationale(
        findings: tuple[AdversarialFinding, ...],
        gate_decision: GateDecision,
    ) -> str:
        if not findings:
            return "No adversarial findings detected; checkpoint may continue."
        classes = ", ".join(finding.finding_class for finding in findings)
        return f"Detected {classes}; checkpoint gate decision is {gate_decision}."


def _non_empty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


__all__ = [
    "AdversarialFinding",
    "AdversarialReviewInput",
    "AdversarialReviewResult",
    "AdversarialReviewRoutine",
    "ApprovalExplanation",
    "FindingClass",
]
