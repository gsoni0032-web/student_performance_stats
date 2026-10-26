"""Assemble every v1 router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, classes, dashboard, data, model, predictions, students, users

api_router = APIRouter()
for module in (auth, students, classes, users, predictions, dashboard, data, model):
    api_router.include_router(module.router)
