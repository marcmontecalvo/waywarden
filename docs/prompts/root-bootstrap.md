Build a production-shaped but intentionally small EA harness in Python.

Constraints:
- EA-only substrate. Do not build HA runtime or coding runtime inside this repo.
- Native VM app first. Docker only for sidecars.
- Python 3.13, uv, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2, Alembic, pytest, Ruff.
- Honcho is the memory layer.
- LLM-Wiki is the knowledge layer via an adapter boundary, not deep coupling.
- Skills, memory, knowledge, tools, and channels must all be swappable by interface.
- No dream system in the hot path.
- No self-editing policies.
- No giant monolithic prompt architecture.
- Start with web API + CLI only.

Deliverables:
1. repo skeleton
2. typed settings/config system
3. domain models
4. DB models + migrations
5. skill registry
6. model router
7. Honcho adapter interface + implementation stub
8. LLM-Wiki adapter interface + implementation stub
9. tool registry
10. tests and basic docs

Prefer boring, testable code over clever abstractions.
