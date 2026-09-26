# -*- coding: utf-8 -*-
"""The skill module of agentscope."""

from ._base import Skill
from ._local_loader import LocalSkillLoader, SkillError

__all__ = [
    "Skill",
    "LocalSkillLoader",
    "SkillError",
]
