"""Load SKILL.md files into system prompts."""
import sys
from pathlib import Path

from ..config import settings

ONSHAPE_SKILL_FILES = [
    "spatial-reasoning/SKILL.md",
    "print-profiles/SKILL.md",
    "onshape-design-assistant/SKILL.md",
]

CADQUERY_SKILL_FILES = [
    "spatial-reasoning/SKILL.md",
    "print-profiles/SKILL.md",
    "_legacy/cadquery-codegen/SKILL.md",
    "_legacy/cadquery-validate/SKILL.md",
]


def _strip_frontmatter(content: str) -> str:
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            return content[end + 3 :].strip()
    return content


def load_skills(skill_paths: list[str] | None = None) -> str:
    """Concatenate SKILL.md files into a system prompt."""
    skills_dir = settings.resolved_skills_dir()
    paths = skill_paths or ONSHAPE_SKILL_FILES
    parts: list[str] = []
    for rel in paths:
        path = skills_dir / rel
        if not path.exists():
            print(f"WARNING: Skill file not found: {path}", file=sys.stderr)
            continue
        content = _strip_frontmatter(path.read_text())
        skill_name = path.parent.name
        parts.append(f"# === SKILL: {skill_name} ===\n\n{content}")
    return "\n\n---\n\n".join(parts)


def load_onshape_system_prompt() -> str:
    return load_skills(ONSHAPE_SKILL_FILES)


def load_cadquery_system_prompt() -> str:
    return load_skills(CADQUERY_SKILL_FILES)
