# -*- coding: utf-8 -*-
"""The skill model for AgentScope agent skills."""
from pathlib import Path

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """One agent skill discovered from a SKILL.md file.

    A skill bundles instructions (and optionally scripts/resources)
    that extend the agent's capabilities. The instructions are external
    data: they are presented to the agent as prompt material and never
    override the repository's own guidance.
    """

    name: str
    """The skill name from the SKILL.md frontmatter."""

    description: str
    """The skill description from the SKILL.md frontmatter."""

    dir: Path
    """The absolute directory holding the SKILL.md."""

    instructions: str = ""
    """The SKILL.md body below the frontmatter."""
