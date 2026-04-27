"""Regression guardrails for the real EA runtime path."""

from __future__ import annotations

from pathlib import Path

import yaml

from waywarden.domain.delegation.envelope import DelegationEnvelope
from waywarden.domain.delegation.handoff import EAAHandoffHelper, HandoffContext

REPO_ROOT = Path(__file__).resolve().parents[2]
EA_PROFILE_PATH = REPO_ROOT / "profiles" / "ea" / "profile.yaml"
EA_E2E_TEST_PATH = REPO_ROOT / "tests" / "integration" / "ea" / "test_ea_e2e.py"
EA_TASK_SERVICE_PATH = REPO_ROOT / "src" / "waywarden" / "services" / "ea_task_service.py"


def test_checked_in_ea_profile_uses_concrete_provider_ids() -> None:
    content = yaml.safe_load(EA_PROFILE_PATH.read_text(encoding="utf-8"))
    providers = content["required_providers"]

    assert providers["model"] == "fake-model"
    assert providers["memory"] == "fake-memory"
    assert providers["knowledge"] == "filesystem"
    assert providers["tracer"] == "noop"
    assert providers["model"] != "fake"
    assert providers["memory"] != "fake"


def test_ea_integration_proof_uses_real_runtime_primitives() -> None:
    text = EA_E2E_TEST_PATH.read_text(encoding="utf-8")

    assert "FakeEATaskService" not in text
    assert "TaskRepositoryImpl" in text
    assert "ApprovalRepositoryImpl" in text
    assert "RunEventRepositoryImpl" in text
    assert "WorkspaceManifestRepositoryImpl" in text
    assert "ModelRouter" in text
    assert "hydrate_ea_profile" in text


def test_ea_task_service_source_has_no_local_authoritative_state() -> None:
    text = EA_TASK_SERVICE_PATH.read_text(encoding="utf-8")

    assert "defer repository wiring" not in text
    assert "_tasks: dict" not in text
    assert "_approvals: dict" not in text
    assert "_events: list" not in text
    assert "TaskRepository" in text
    assert "ApprovalEngine" in text
    assert "RunEventRepository" in text


def test_ea_handoff_helper_returns_typed_envelope() -> None:
    helper = EAAHandoffHelper(parent_run_id="run-guardrail")
    envelope = helper.make_envelope_manual(HandoffContext(objective="Guardrail"))

    assert isinstance(envelope, DelegationEnvelope)
