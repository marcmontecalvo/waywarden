"""PolicyLoader — reads preset YAML and produces domain ``ToolPolicy``.

Resolves a preset name from ``config/policy/presets/{name}.yaml``,
optionally merges overrides, and returns a domain ``ToolPolicy``
suitable for attachment to a ``WorkspaceManifest``.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yaml

from waywarden.domain.manifest.tool_policy import ToolPolicy
from waywarden.policy.schema import PolicyPresetDoc


class PolicyLoaderError(RuntimeError):
    """General policy loading failure (malformed YAML, etc.)."""


class UnknownPresetError(PolicyLoaderError):
    """Requested preset does not exist."""


class PolicyLoader:
    """Load policy presets from YAML files.

    Parameters
    ----------
    presets_dir:
        Directory that contains ``{preset_name}.yaml`` files.
    """

    def __init__(self, presets_dir: Path | None = None) -> None:
        if presets_dir is None:
            presets_dir = Path("config/policy/presets")
        self.presets_dir = presets_dir

    def list_presets(self) -> list[str]:
        """Return sorted names of all available preset files."""
        if not self.presets_dir.is_dir():
            return []
        names: list[str] = []
        for file in sorted(self.presets_dir.iterdir()):
            if file.suffix in (".yaml", ".yml"):
                names.append(file.stem)
        return names

    def load(
        self,
        name: str,
        *,
        override: Mapping[str, Any] | None = None,
    ) -> ToolPolicy:
        """Load a preset by ``name`` and produce a domain ``ToolPolicy``.

        Parameters
        ----------
        name:
            Preset file stem (e.g. ``"ask"``).
        override:
            Optional dictionary of keys to merge on top of the loaded
            ``PolicyPresetDoc`` before converting to domain.

        Returns
        -------
        ToolPolicy
            The resolved domain policy.

        Raises
        ------
        UnknownPresetError
            When the preset file does not exist.
        PolicyLoaderError
            On malformed YAML or validation failure.
        """
        preset_path = self.presets_dir / f"{name}.yaml"
        if not preset_path.is_file():
            raise UnknownPresetError(f"Unknown preset '{name}'; expected {preset_path}")

        try:
            raw = yaml.safe_load(preset_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise PolicyLoaderError(f"Malformed YAML in {preset_path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise PolicyLoaderError(
                f"Preset {preset_path} did not resolve to a mapping; got {type(raw).__name__}"
            )

        doc: PolicyPresetDoc
        try:
            doc = PolicyPresetDoc(**raw)
        except Exception as exc:
            raise PolicyLoaderError(
                f"Validation failed for preset '{name}' in {preset_path}: {exc}"
            ) from exc

        if override is not None:
            doc = self._apply_overrides(doc, override)

        return doc.to_domain()

    @staticmethod
    def _apply_overrides(
        doc: PolicyPresetDoc,
        override: Mapping[str, Any],
    ) -> PolicyPresetDoc:
        """Merge ``override`` keys into ``doc`` fields.

        Only ``default_decision`` and ``rules`` are supported override
        targets.  Any other key is silently ignored (future-proofing).
        """
        merged: dict[str, Any] = doc.model_dump(mode="json")

        if "default_decision" in override:
            merged["default_decision"] = override["default_decision"]

        if "rules" in override:
            existing_rules: list[dict[str, Any]] = list(merged.get("rules", []))
            raw_override_rules: list[dict[str, Any]] = list(override["rules"])
            rule_map: dict[tuple[str, str | None], dict[str, Any]] = {}
            for r in existing_rules:
                key: tuple[str, str | None] = (r["tool"], r.get("action"))
                rule_map[key] = r
            for r in raw_override_rules:
                key = (r["tool"], r.get("action"))
                rule_map[key] = r
            merged["rules"] = list(rule_map.values())

        return PolicyPresetDoc(**merged)
