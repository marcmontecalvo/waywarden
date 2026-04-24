# WayWarden — Agent Harness

## Problem
Develop a Python-first agent harness that manages autonomous agent workflows with profile-driven configuration, providing a modular runtime for EA, coding, and home assistant profiles.

## Goals
- Profile-driven runtime supporting EA, coding, and home overlay profiles
- Multi-instance capable with named instances (marc-ea, lisa-ea, coding-main, ha-main)
- Provider-boundary clean architecture with adapter pattern for LLM/memory/knowledge channels

## Users / Actors
- Marc Montecalvo (primary dev/user)
- Lisa (needs EA support via separate instance)
- Autonomous agents (the runtime itself)

## Technical Direction
- Stack: Python 3.13, FastAPI, Uvicorn, Pydantic v2, pytest, Ruff
- Framework: FastAPI
- Deployment: Initially local Linux, later VPS
- Testing: pytest
