"""Stage 8 task 4: local skill loader."""

import asyncio
import os

import pytest

from agentscope.skill import LocalSkillLoader, SkillError

SKILL_MD = """---
name: echo-skill
description: Demonstrates a minimal local skill.
---

# Echo Skill

Follow these instructions to echo text politely.
"""


def test_skill_loader(tmp_path) -> None:
    skill_dir = tmp_path / "echo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

    loader = LocalSkillLoader(directory=tmp_path)
    skills = asyncio.run(loader.load())

    assert len(skills) == 1
    skill = skills[0]
    assert skill.name == "echo-skill"
    assert skill.description == "Demonstrates a minimal local skill."
    assert skill.dir == skill_dir.resolve()
    assert "Echo Skill" in skill.instructions


def test_loader_skips_directories_without_skill_md(tmp_path) -> None:
    (tmp_path / "not-a-skill").mkdir()
    skill_dir = tmp_path / "real-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

    skills = asyncio.run(LocalSkillLoader(directory=tmp_path).load())
    assert [skill.name for skill in skills] == ["echo-skill"]


def test_missing_metadata_is_rejected(tmp_path) -> None:
    bad = tmp_path / "bad-skill"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: only-name\n---\nbody",
        encoding="utf-8",
    )

    with pytest.raises(SkillError, match="description"):
        asyncio.run(LocalSkillLoader(directory=tmp_path).load())


def test_escaping_skill_dir_is_rejected(tmp_path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")

    loader_root = tmp_path / "skills"
    loader_root.mkdir()
    link = loader_root / "sneaky"
    if hasattr(os, "symlink"):
        try:
            os.symlink(outside, link, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks not supported on this filesystem")
        with pytest.raises(SkillError):
            asyncio.run(LocalSkillLoader(directory=loader_root).load())
