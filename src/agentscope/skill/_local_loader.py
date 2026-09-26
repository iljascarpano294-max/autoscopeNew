# -*- coding: utf-8 -*-
"""Load agent skills from local directories."""
import asyncio
from pathlib import Path

import yaml

from ._base import Skill
from ..exception import AgentOrientedException


class SkillError(AgentOrientedException):
    """Structured failure for skill discovery and validation."""


class LocalSkillLoader:
    """Discover skills in a directory tree.

    A skill is a subdirectory of ``directory`` containing a SKILL.md with
    YAML frontmatter defining ``name`` and ``description``. Directories
    whose SKILL.md is missing or lacks metadata are reported as
    SkillError; a skill directory that resolves outside the loader root
    (e.g. through a symlink) is rejected so a malicious skill cannot
    make the agent read arbitrary locations.
    """

    def __init__(self, directory: Path | str) -> None:
        self._root = Path(directory)
        if not self._root.is_dir():
            raise SkillError(
                f"Skill directory '{self._root}' does not exist.",
            )
        self._resolved_root = self._root.resolve()

    async def load(self) -> list[Skill]:
        """Scan the directory tree and load every valid skill."""
        skill_dirs = [
            path.parent
            for path in sorted(self._resolved_root.rglob("SKILL.md"))
        ]
        skills = await asyncio.gather(
            *(self._load_single(skill_dir) for skill_dir in skill_dirs),
        )
        return list(skills)

    async def _load_single(self, skill_dir: Path) -> Skill:
        # A symlinked skill directory must resolve inside the loader root.
        resolved_dir = skill_dir.resolve()
        if resolved_dir != self._resolved_root and not resolved_dir.is_relative_to(
            self._resolved_root,
        ):
            raise SkillError(
                f"Skill directory '{skill_dir}' escapes the loader root "
                f"'{self._resolved_root}'.",
            )

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            raise SkillError(
                f"'{skill_dir}' does not contain a SKILL.md.",
            )

        try:
            content = skill_md.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise SkillError(
                f"Failed to read '{skill_md}': {error}",
            ) from error

        name, description, instructions = self._parse_frontmatter(content)
        if not name or not description:
            missing = [
                field for field, value in (("name", name), ("description", description))
                if not value
            ]
            raise SkillError(
                f"SKILL.md in {skill_dir} is missing required fields: "
                f"{', '.join(missing)}.",
            )

        return Skill(
            name=name,
            description=description,
            dir=resolved_dir,
            instructions=instructions,
        )

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[str, str, str]:
        """Split YAML frontmatter from the body and return (name,
        description, instructions)."""
        if not content.startswith("---"):
            return "", "", content
        parts = content.split("---", 2)
        if len(parts) < 3:
            return "", "", content
        try:
            metadata = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as error:
            raise SkillError(f"Invalid SKILL.md frontmatter: {error}") from error
        if not isinstance(metadata, dict):
            metadata = {}
        instructions = parts[2].strip()
        return (
            str(metadata.get("name", "")).strip(),
            str(metadata.get("description", "")).strip(),
            instructions,
        )
