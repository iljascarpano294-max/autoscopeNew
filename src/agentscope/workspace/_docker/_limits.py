# -*- coding: utf-8 -*-
"""Resource limits for the Docker sandbox."""
from pydantic import BaseModel


class DockerLimits(BaseModel):
    """Container resource and network limits."""

    image: str = "python:3.11-slim"
    memory: str = "256m"
    cpus: str = "0.5"
    network: bool = False
    """Network access is disabled by default for sandbox isolation."""
