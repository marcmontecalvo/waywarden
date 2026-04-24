"""Tests for channel binding validation on InstanceDescriptor."""

from __future__ import annotations

from pathlib import Path

import pytest

from waywarden.config import InstanceLoadError, load_instances
from waywarden.domain.channel_binding import register_channel_provider
from waywarden.domain.ids import InstanceId


def _make_profiles(tmp_path: Path) -> Path:
    """Create a minimal profile fixture."""
    profiles_dir = tmp_path / "profiles"
    (profiles_dir / "ea").mkdir(parents=True)
    (profiles_dir / "ea" / "profile.yaml").write_text(
        "id: ea\n"
        "display_name: Executive Assistant\n"
        "version: 1.0.0\n"
        "required_providers:\n"
        "  model: fake-model\n"
        "  memory: fake-memory\n"
        "  knowledge: fake-knowledge\n"
        "supported_extensions:\n"
        "  - skill\n",
        encoding="utf-8",
    )
    return profiles_dir


def _ensure_instance_config(config_dir: Path, instance_id: str) -> Path:
    """Create a minimal instance overlay for a given instance id."""
    instances_dir = config_dir / "instances"
    instances_dir.mkdir(parents=True, exist_ok=True)
    path = instances_dir / f"{instance_id}.yaml"
    path.write_text("env: {}\noverrides: {}\n", encoding="utf-8")
    return path


class TestChannelBindingType:
    """ChannelBinding must be a typed structure accepted only as a list of mappings."""

    def test_channel_binding_accepts_valid_mapping(self) -> None:
        from waywarden.domain.channel_binding import ChannelBinding

        binding = ChannelBinding(
            channel_name="chat",
            transport="http",
            path="/api/chat",
            enabled=True,
        )
        assert binding.channel_name == "chat"
        assert binding.transport == "http"
        assert binding.path == "/api/chat"
        assert binding.enabled is True

    def test_channel_binding_defaults_enabled_to_true(self) -> None:
        from waywarden.domain.channel_binding import ChannelBinding

        binding = ChannelBinding(
            channel_name="chat",
            transport="http",
        )
        assert binding.enabled is True
        assert binding.path is None

    def test_channel_binding_rejects_invalid_transport(self) -> None:
        from waywarden.domain.channel_binding import ChannelBinding

        with pytest.raises(ValueError, match="transport"):
            ChannelBinding(channel_name="chat", transport="websocket")  # type: ignore[arg-type]

    def test_channel_binding_rejects_empty_channel_name(self) -> None:
        from waywarden.domain.channel_binding import ChannelBinding

        with pytest.raises(ValueError, match="channel_name"):
            ChannelBinding(channel_name="  ", transport="http")


class TestUnknownChannelRejected:
    """Unknown channel name raises at startup."""

    def test_unknown_channel_rejected(self, tmp_path: Path) -> None:
        """When ChannelProviders are registered, unknown channel names are rejected."""
        register_channel_provider("chat")  # Register a real channel to hit the validation path
        try:
            profiles_dir = _make_profiles(tmp_path)
            config_dir = tmp_path / "config"

            instances_dir = config_dir / "instances"
            instances_dir.mkdir(parents=True)
            (config_dir / "instances.yaml").write_text(
                "instances:\n"
                "  - id: test-insta\n"
                "    display_name: Test Insta\n"
                "    profile_id: ea\n"
                "    config_path: instances/test-insta.yaml\n",
                encoding="utf-8",
            )
            (instances_dir / "test-insta.yaml").write_text(
                "env: {}\n"
                "overrides:\n"
                "  channels:\n"
                "    - channel_name: nonexistent\n"
                "      transport: http\n",
                encoding="utf-8",
            )

            with pytest.raises(InstanceLoadError) as exc_info:
                load_instances(
                    config_dir=config_dir,
                    profiles_dir=profiles_dir,
                )

            message = str(exc_info.value)
            assert "nonexistent" in message
            assert "unknown" in message.lower()
        finally:
            # Clean up the registry so other tests aren't affected
            import waywarden.domain.channel_binding as cb

            cb._CHANNEL_REGISTRY.discard("chat")


class TestDuplicateTransportPathRejected:
    """Duplicate (transport, path) raises at startup."""

    def test_duplicate_transport_path_rejected(self, tmp_path: Path) -> None:
        profiles_dir = _make_profiles(tmp_path)
        config_dir = tmp_path / "config"

        instances_dir = config_dir / "instances"
        instances_dir.mkdir(parents=True)
        (config_dir / "instances.yaml").write_text(
            "instances:\n"
            "  - id: test-insta\n"
            "    display_name: Test Insta\n"
            "    profile_id: ea\n"
            "    config_path: instances/test-insta.yaml\n",
            encoding="utf-8",
        )
        (instances_dir / "test-insta.yaml").write_text(
            "env: {}\n"
            "overrides:\n"
            "  channels:\n"
            "    - channel_name: chat-a\n"
            "      transport: http\n"
            "      path: /api/chat\n"
            "    - channel_name: chat-b\n"
            "      transport: http\n"
            "      path: /api/chat\n",
            encoding="utf-8",
        )

        with pytest.raises(InstanceLoadError) as exc_info:
            load_instances(
                config_dir=config_dir,
                profiles_dir=profiles_dir,
            )

        message = str(exc_info.value)
        assert "duplicate" in message.lower() or "conflict" in message.lower()


class TestTypedListRequired:
    """Instance.channels accepts a typed list; free-form dict rejected at validation."""

    def test_typed_list_required(self) -> None:
        """channels must be a typed list of channel mapping items."""
        from waywarden.domain.channel_binding import ChannelBinding

        # ChannelBinding rejects when passed as a single dict (not as kwargs)
        with pytest.raises(TypeError):
            ChannelBinding({"channel_name": "chat", "transport": "http"})  # type: ignore[arg-type]

    def test_instance_descriptor_rejects_channels_as_scalar(self, tmp_path: Path) -> None:
        """If channels is a string or bare dict, load should reject it."""
        profiles_dir = _make_profiles(tmp_path)
        config_dir = tmp_path / "config"
        _ensure_instance_config(config_dir, "test-insta")

        (config_dir / "instances.yaml").write_text(
            "instances:\n"
            "  - id: test-insta\n"
            "    display_name: Test Insta\n"
            "    profile_id: ea\n"
            "    config_path: instances/test-insta.yaml\n",
            encoding="utf-8",
        )
        config_yaml = config_dir / "instances" / "test-insta.yaml"
        # channels as a bare string should be rejected
        config_yaml.write_text(
            "env: {}\n"
            "overrides:\n"
            "  channels: \"not-a-list\"\n",
            encoding="utf-8",
        )

        with pytest.raises(InstanceLoadError) as exc_info:
            load_instances(config_dir=config_dir, profiles_dir=profiles_dir)

        message = str(exc_info.value)
        assert "channels" in message.lower()

    def test_instance_descriptor_rejects_channels_as_dict(self, tmp_path: Path) -> None:
        """If channels is a bare dict (not a list), load should reject it."""
        profiles_dir = _make_profiles(tmp_path)
        config_dir = tmp_path / "config"
        _ensure_instance_config(config_dir, "test-insta")

        (config_dir / "instances.yaml").write_text(
            "instances:\n"
            "  - id: test-insta\n"
            "    display_name: Test Insta\n"
            "    profile_id: ea\n"
            "    config_path: instances/test-insta.yaml\n",
            encoding="utf-8",
        )
        config_yaml = config_dir / "instances" / "test-insta.yaml"
        config_yaml.write_text(
            "env: {}\n"
            "overrides:\n"
            "  channels:\n"
            "    chat:\n"
            "      transport: http\n",
            encoding="utf-8",
        )

        with pytest.raises(InstanceLoadError) as exc_info:
            load_instances(config_dir=config_dir, profiles_dir=profiles_dir)

        message = str(exc_info.value)
        assert "channels" in message.lower()

    def test_instance_descriptor_typed_channels_parsed_from_yaml(self, tmp_path: Path) -> None:
        """Valid channels list is parsed and available on InstanceDescriptor."""
        profiles_dir = _make_profiles(tmp_path)
        config_dir = tmp_path / "config"
        _ensure_instance_config(config_dir, "test-insta")

        (config_dir / "instances.yaml").write_text(
            "instances:\n"
            "  - id: test-insta\n"
            "    display_name: Test Insta\n"
            "    profile_id: ea\n"
            "    config_path: instances/test-insta.yaml\n",
            encoding="utf-8",
        )
        config_yaml = config_dir / "instances" / "test-insta.yaml"
        config_yaml.write_text(
            "env: {}\n"
            "overrides:\n"
            "  channels:\n"
            "    - channel_name: chat\n"
            "      transport: http\n"
            "      path: /api/chat\n",
            encoding="utf-8",
        )

        registry = load_instances(config_dir=config_dir, profiles_dir=profiles_dir)
        descriptor = registry["test-insta"]

        assert descriptor.channels is not None
        assert len(descriptor.channels) == 1
        assert descriptor.channels[0].channel_name == "chat"
        assert descriptor.channels[0].transport == "http"
        assert descriptor.channels[0].path == "/api/chat"
        assert descriptor.channels[0].enabled is True
