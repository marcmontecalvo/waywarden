"""Tool registry and built-in tool providers.

Public-facing API:
- ``ToolProvider`` — Protocol defining the provider surface.
- ``ToolRegistry`` — Capability-dispatch and policy-validation layer.
- ``ShellReadTool`` — First built-in tool provider (capability ``shell``, action ``read``).
"""
