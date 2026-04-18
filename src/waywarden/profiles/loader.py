"""Filesystem loader for checked-in profile descriptors."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

from waywarden.domain.profile import ProfileDescriptor, ProfileId, ProfileRegistry


class ProfileLoadError(ValueError):
    """Aggregated failure raised when one or more profile manifests are invalid."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = ["Profile loading failed:"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def load_profiles(profiles_dir: Path | None = None) -> ProfileRegistry:
    """Load all profile manifests from ``profiles/*/profile.yaml``."""

    resolved_profiles_dir = (profiles_dir or Path("profiles")).resolve()
    if not resolved_profiles_dir.exists():
        raise ProfileLoadError(
            [f"{resolved_profiles_dir.as_posix()}: profiles directory not found"]
        )
    if not resolved_profiles_dir.is_dir():
        raise ProfileLoadError(
            [f"{resolved_profiles_dir.as_posix()}: profiles path is not a directory"]
        )

    descriptors_by_path: dict[Path, ProfileDescriptor] = {}
    errors: list[str] = []

    for profile_path in sorted(resolved_profiles_dir.glob("*/profile.yaml")):
        descriptor = _load_profile_descriptor(profile_path, errors)
        if descriptor is not None:
            descriptors_by_path[profile_path] = descriptor

    errors.extend(_collect_duplicate_id_errors(descriptors_by_path))
    if errors:
        raise ProfileLoadError(errors)

    ordered_descriptors = {
        descriptor.id: descriptor
        for _, descriptor in sorted(
            descriptors_by_path.items(),
            key=lambda item: item[1].id,
        )
    }
    return ProfileRegistry(ordered_descriptors)


def _load_profile_descriptor(
    profile_path: Path,
    errors: list[str],
) -> ProfileDescriptor | None:
    try:
        content = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{profile_path.as_posix()}: unable to read file: {exc.strerror or exc}")
        return None
    except yaml.YAMLError as exc:
        reason = getattr(exc, "problem", None) or str(exc)
        errors.append(f"{profile_path.as_posix()}: YAML parse error: {reason}")
        return None

    if content is None or not isinstance(content, dict):
        errors.append(f"{profile_path.as_posix()}: expected a mapping of profile settings")
        return None
    if not all(isinstance(key, str) for key in content):
        errors.append(f"{profile_path.as_posix()}: profile setting names must be strings")
        return None

    try:
        return ProfileDescriptor(**content)
    except (TypeError, ValueError) as exc:
        errors.append(f"{profile_path.as_posix()}: {exc}")
        return None


def _collect_duplicate_id_errors(
    descriptors_by_path: dict[Path, ProfileDescriptor],
) -> list[str]:
    paths_by_profile_id: dict[ProfileId, list[Path]] = defaultdict(list)
    for profile_path, descriptor in descriptors_by_path.items():
        paths_by_profile_id[descriptor.id].append(profile_path)

    errors: list[str] = []
    for profile_id, duplicate_paths in sorted(paths_by_profile_id.items()):
        if len(duplicate_paths) < 2:
            continue

        ordered_paths = ", ".join(path.as_posix() for path in sorted(duplicate_paths))
        errors.append(
            f"profile id {str(profile_id)!r} is declared by multiple files: {ordered_paths}"
        )

    return errors
