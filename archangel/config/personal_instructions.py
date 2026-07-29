"""PersonalInstructionsStore — Manages user preferences, tech stack, and pitch customization."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_INSTRUCTIONS = {
    "developer_bio": "Senior Fullstack & AI Automation Engineer specializing in fast MVP development, SaaS web apps, and Python/Node automation.",
    "preferred_stack": ["Next.js", "React", "Python", "FastAPI", "Node.js", "TypeScript", "TailwindCSS"],
    "target_roles": ["Fullstack Developer", "SaaS Developer", "AI Automation Engineer", "Backend Engineer"],
    "minimum_budget_usd": 500,
    "minimum_budget_inr": 40000,
    "pitch_style": "Concise, technical, direct, focusing on speed to deliver and solid architecture.",
    "custom_instructions": "",
}


class PersonalInstructionsStore:
    """Manages persistent custom user instructions for lead scoring and AI pitch generation."""

    _instance: Optional["PersonalInstructionsStore"] = None

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or Path("data/user_instructions.json")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = self._load()

    @classmethod
    def get_instance(cls) -> "PersonalInstructionsStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> Dict[str, Any]:
        if self.config_path.exists():
            try:
                content = self.config_path.read_text(encoding="utf-8")
                loaded = json.loads(content)
                merged = DEFAULT_INSTRUCTIONS.copy()
                merged.update(loaded)
                return merged
            except Exception as e:
                logger.warning("Failed to parse user instructions file %s: %s", self.config_path, e)
        return DEFAULT_INSTRUCTIONS.copy()

    def save(self) -> None:
        """Persists current instructions to JSON file."""
        try:
            self.config_path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to save user instructions to %s: %s", self.config_path, e)

    def update_instruction(self, text: str) -> str:
        """Parses and updates custom instruction text from user command."""
        self.data["custom_instructions"] = text.strip()
        self.save()
        return f"Updated personal instructions: '{text.strip()}'"

    def get_pitch_context(self) -> str:
        """Returns concise prompt context block for pitch generator."""
        bio = self.data.get("developer_bio", "")
        stack = ", ".join(self.data.get("preferred_stack", []))
        style = self.data.get("pitch_style", "")
        custom = self.data.get("custom_instructions", "")
        ctx = f"Developer Bio: {bio}\nPreferred Tech Stack: {stack}\nPitch Style: {style}"
        if custom:
            ctx += f"\nCustom Instructions: {custom}"
        return ctx
