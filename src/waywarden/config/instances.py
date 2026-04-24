from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path

import yaml

from waywarden.domain.channel_binding import ChannelBinding, get_channel_registry
from waywarden.domain.instance import (
    InstanceConfig,
    InstanceDescriptor,
    InstanceId,
    InstanceRegistry,
)
from waywarden.domain.profile import ProfileRegistry
from waywarden.profiles import ProfileLoadError, load_profiles


class InstanceLoadError(ValueError):
    """Aggregated failure raised when one or more instance fixtures are invalid."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(self.__str__())

    def __str__(self) -> str:
        lines = ["Instance loading failed:"]
        lines.extend(f"- {error}" for error in self.errors)
        return "\n".join(lines)


def load_instances(
    config_dir: Path | None = None,
    profiles_dir: Path | None = None,
) -> InstanceRegistry:
    """Load checked-in instance fixtures from ``config/instances.yaml``."""

    resolved_config_dir = (config_dir or Path("config")).resolve()
    resolved_profiles_dir = (profiles_dir or Path("profiles")).resolve()
    manifest_path = resolved_config_dir / "instances.yaml"

    errors: list[str] = []
    try:
        profiles = load_profiles(resolved_profiles_dir)
    except ProfileLoadError as exc:
        errors.extend(f"profile validation prerequisite failed: {error}" for error in exc.errors)
        raise InstanceLoadError(errors) from exc

    if not manifest_path.is_file():
        raise InstanceLoadError(
            [f"{manifest_path.as_posix()}: required instance manifest not found"]
        )

    content = _read_yaml_mapping(manifest_path, errors, mapping_label="instance manifest")
    if content is None:
        raise InstanceLoadError(errors)

    raw_instances = content.get("instances")
    if not isinstance(raw_instances, list):
        errors.append(f"{manifest_path.as_posix()}: field `instances` must be a list of instances")
        raise InstanceLoadError(errors)

    descriptors: list[InstanceDescriptor] = []
    for index, raw_descriptor in enumerate(raw_instances):
        descriptor = _load_descriptor(
            raw_descriptor=raw_descriptor,
            index=index,
            manifest_path=manifest_path,
            config_dir=resolved_config_dir,
            profiles=profiles,
            errors=errors,
        )
        if descriptor is not None:
            descriptors.append(descriptor)

    errors.extend(_collect_duplicate_id_errors(descriptors))
    if errors:
        raise InstanceLoadError(errors)

    ordered_descriptors = {
        descriptor.id: descriptor for descriptor in sorted(descriptors, key=lambda item: item.id)
    }
    return InstanceRegistry(ordered_descriptors)


def _load_descriptor(
    *,
    raw_descriptor: object,
    index: int,
    manifest_path: Path,
    config_dir: Path,
    profiles: ProfileRegistry,
    errors: list[str],
) -> InstanceDescriptor | None:
    entry_prefix = f"{manifest_path.as_posix()}: instances[{index}]"
    if not isinstance(raw_descriptor, dict):
        errors.append(f"{entry_prefix}: expected a mapping of instance settings")
        return None
    if not all(isinstance(key, str) for key in raw_descriptor):
        errors.append(f"{entry_prefix}: instance setting names must be strings")
        return None

    try:
        descriptor = InstanceDescriptor(**raw_descriptor)
    except (TypeError, ValueError) as exc:
        errors.append(f"{entry_prefix}: {exc}")
        return None

    if descriptor.profile_id not in profiles:
        errors.append(
            f"{entry_prefix}: profile_id {descriptor.profile_id!r} does not match any checked-in "
            "profile"
        )

    config_path = _resolve_instance_config_path(config_dir, descriptor.config_path)
    if not config_path.is_file():
        errors.append(
            f"{entry_prefix}: config_path {descriptor.config_path.as_posix()!r} "
            f"does not exist under {config_dir.as_posix()}"
        )
        return descriptor

    _ = _load_instance_config(config_path=config_path, errors=errors)

    # Parse the instance overlay once and share the content between channel
    # validation and the existing config loader to avoid redundant I/O.
    parsed_content = _read_yaml_mapping(config_path, errors, mapping_label="instance config")
    channels = _load_channels(
        config_path=config_path,
        config_dir=config_dir,
        errors=errors,
        content=parsed_content,
    )

    try:
        descriptor = InstanceDescriptor(
            id=descriptor.id,
            display_name=descriptor.display_name,
            profile_id=descriptor.profile_id,
            config_path=descriptor.config_path,
            channels=tuple(channels),
        )
    except (TypeError, ValueError) as exc:
        errors.append(f"{entry_prefix}: {exc}")
        return None

    return descriptor


def _load_instance_config(*, config_path: Path, errors: list[str]) -> InstanceConfig | None:
    content = _read_yaml_mapping(config_path, errors, mapping_label="instance config")
    if content is None:
        return None

    try:
        return InstanceConfig(
            env=_string_mapping_field(content, field_name="env", path=config_path, errors=errors),
            overrides=_mapping_field(
                content,
                field_name="overrides",
                path=config_path,
                errors=errors,
            ),
        )
    except (TypeError, ValueError) as exc:
        errors.append(f"{config_path.as_posix()}: {exc}")
        return None


def _load_channels(
    *,
    config_path: Path,
    config_dir: Path,
    errors: list[str],
    content: Mapping[str, object] | None = None,
) -> list[ChannelBinding]:
    """Parse and validate channels from the instance config overlay.

    Channels live under ``overrides.channels`` in the instance YAML file.  They
    must be a list of channel definitions (mapping keys to ``ChannelBinding``
    sub-mappings).  Scalar or dict values are rejected.

    The ``content`` parameter accepts a pre-parsed YAML mapping so that the
    file need not be read a second time by callers that already parsed it.
    """
    if content is None:
        content = _read_yaml_mapping(config_path, errors, mapping_label="instance config")
        if content is None:
            return []

    raw_channels = content.get("overrides", {})
    if not isinstance(raw_channels, dict):
        errors.append(f"{config_path.as_posix()}: field `overrides` must be a mapping")
        return []

    raw_list = raw_channels.get("channels")
    if raw_list is None:
        return []

    if not isinstance(raw_list, list):
        errors.append(
            f"{config_path.as_posix()}: field `overrides.channels` must be a list",
        )
        return []

    bindings: list[ChannelBinding] = []
    transport_path_pairs: list[tuple[str, str | None]] = []
    registry = get_channel_registry()

    for idx, raw_item in enumerate(raw_list):
        item_prefix = f"{config_path.as_posix()}: overrides.channels[{idx}]"
        if not isinstance(raw_item, dict):
            errors.append(f"{item_prefix}: expected a channel definition mapping")
            continue

        try:
            binding = ChannelBinding(
                channel_name=raw_item["channel_name"],
                transport=raw_item["transport"],
                path=raw_item.get("path"),
                enabled=raw_item.get("enabled", True),
            )
        except (TypeError, ValueError, KeyError) as exc:
            errors.append(f"{item_prefix}: {exc}")
            continue

        # Validate channel name against registered ChannelProviders.
        # When the registry is empty (no adapters implemented yet), channel
        # names are accepted structurally; reject only when adapters exist.
        # This is a skip, not a reject — an unregistered binding that also
        # duplicates another binding will fail the transport-path check
        # (or will be silently accepted if the duplicate is also unregistered).
        if registry and binding.channel_name not in registry:
            errors.append(
                f"{item_prefix}: unknown channel {binding.channel_name!r} "
                f"(not registered with any ChannelProvider; "
                f"known: {sorted(registry)})",
            )
            continue

        # Validate uniqueness of (transport, path) pairs.
        for dup_idx, (existing_transport, existing_path) in enumerate(transport_path_pairs):
            if binding.transport == existing_transport and binding.path == existing_path:
                errors.append(
                    f"{item_prefix}: duplicate (transport, path) pair "
                    f"({binding.transport!r}, {binding.path!r}) "
                    f"conflicts with overrides.channels[{dup_idx}]",
                )
                break

        transport_path_pairs.append((binding.transport, binding.path))
        bindings.append(binding)

    return bindings


def _mapping_field(
    content: Mapping[str, object],
    *,
    field_name: str,
    path: Path,
    errors: list[str],
) -> Mapping[str, object]:
    raw_value = content.get(field_name, {})
    if not isinstance(raw_value, dict):
        errors.append(f"{path.as_posix()}: field `{field_name}` must be a mapping")
        return {}
    if not all(isinstance(key, str) for key in raw_value):
        errors.append(f"{path.as_posix()}: field `{field_name}` keys must be strings")
        return {}
    return raw_value


def _string_mapping_field(
    content: Mapping[str, object],
    *,
    field_name: str,
    path: Path,
    errors: list[str],
) -> Mapping[str, str]:
    raw_mapping = _mapping_field(content, field_name=field_name, path=path, errors=errors)

    normalized_mapping: dict[str, str] = {}
    for key, value in raw_mapping.items():
        if not isinstance(value, str):
            errors.append(f"{path.as_posix()}: field `{field_name}` values must be strings")
            return {}
        normalized_mapping[key] = value

    return normalized_mapping


def _read_yaml_mapping(
    path: Path,
    errors: list[str],
    *,
    mapping_label: str,
) -> Mapping[str, object] | None:
    try:
        content: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        errors.append(f"{path.as_posix()}: unable to read file: {exc.strerror or exc}")
        return None
    except yaml.YAMLError as exc:
        reason = getattr(exc, "problem", None) or str(exc)
        errors.append(f"{path.as_posix()}: YAML parse error: {reason}")
        return None

    if content is None or not isinstance(content, dict):
        errors.append(f"{path.as_posix()}: expected a mapping of {mapping_label} settings")
        return None
    if not all(isinstance(key, str) for key in content):
        errors.append(f"{path.as_posix()}: {mapping_label} setting names must be strings")
        return None

    return content


def _resolve_instance_config_path(config_dir: Path, config_path: Path) -> Path:
    if config_path.is_absolute():
        return config_path
    return (config_dir / config_path).resolve()


def _collect_duplicate_id_errors(descriptors: list[InstanceDescriptor]) -> list[str]:
    ids_to_indexes: dict[InstanceId, list[int]] = defaultdict(list)
    for index, descriptor in enumerate(descriptors):
        ids_to_indexes[descriptor.id].append(index)

    errors: list[str] = []
    for instance_id, indexes in sorted(ids_to_indexes.items()):
        if len(indexes) < 2:
            continue

        ordered_indexes = ", ".join(str(index) for index in indexes)
        errors.append(
            f"instance id {str(instance_id)!r} is declared multiple times in config/instances.yaml "
            f"at indexes: {ordered_indexes}"
        )

    return errors
