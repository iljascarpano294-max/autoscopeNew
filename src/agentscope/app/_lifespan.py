# -*- coding: utf-8 -*-
"""Application lifespan: release in-process sessions on shutdown."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Yield while the app runs, then drop the in-process sessions.

    Stage 10 keeps sessions in process memory, so a restart loses them
    and later lookups report not-found; releasing them here lets the
    agents be garbage collected promptly.
    """
    yield
    app.state.sessions.clear()
