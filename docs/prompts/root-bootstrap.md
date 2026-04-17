Build a production-shaped but intentionally small Waywarden core harness in Python.

Constraints:
- Do not build Waywarden as an EA-only substrate.
- Build one slim core plus profile packs.
- Native VM app first. Docker only for sidecars.
- Python 3.13, uv, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, Alembic, pytest, Ruff.
- Honcho is the starting memory provider.
- LLM-Wiki is the starting knowledge provider via an adapter boundary, not deep coupling.
- Memory, knowledge, tools, channels, profiles, and tracing must all be swappable by interface.
- Support multiple harness instances side by side.
- Support shared root-level assets filtered into profiles.
- No dream system in the hot path.
- No self-editing governance.
- No giant monolithic prompt architecture.
- Start with web API + CLI only.
- The separate Web UI is optional and out of repo; APIs are king.

Deliverables:
1. repo skeleton
2. typed settings/config system
3. domain models including instance/profile/policy concepts
4. DB models + migrations
5. extension registry
6. profile loader
7. model router
8. Honcho adapter interface + implementation stub
9. LLM-Wiki adapter interface + implementation stub
10. approval/policy engine
11. token accounting hooks
12. tracer abstraction
13. tests and basic docs

Prefer boring, testable code over clever abstractions.
