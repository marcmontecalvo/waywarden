from fastapi import FastAPI

from ea.api.routers import health, chat, tasks, approvals, skills, memory, knowledge, backups

app = FastAPI(title="Waywarden")

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(skills.router)
app.include_router(memory.router)
app.include_router(knowledge.router)
app.include_router(backups.router)
