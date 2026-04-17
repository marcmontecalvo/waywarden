from fastapi import FastAPI

from waywarden.api.routers import approvals, backups, chat, health, knowledge, memory, skills, tasks

app = FastAPI(title="Waywarden")

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(tasks.router)
app.include_router(approvals.router)
app.include_router(skills.router)
app.include_router(memory.router)
app.include_router(knowledge.router)
app.include_router(backups.router)
