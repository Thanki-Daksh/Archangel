"""UserProfileMemory — Parses configs/you.txt to tune lead scoring and filtering based on user background."""

import re
import logging
from pathlib import Path
from typing import List, Set, Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_YOU_TXT_PATH = Path("you.txt")

COMMON_TECH_TOKENS = {
    "python", "fastapi", "django", "flask", "react", "next.js", "nextjs",
    "vue", "svelte", "node", "nodejs", "typescript", "javascript", "rust",
    "golang", "go", "flutter", "react native", "ai", "llm", "scraping",
    "scraper", "telegram", "discord", "bot", "bots", "automation", "aws",
    "docker", "kubernetes", "postgres", "postgresql", "mongodb"
}


class UserProfileMemory:
    """Parses plain-text bullet points from root-level you.txt into scoring preferences and exclusions."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path = file_path or DEFAULT_YOU_TXT_PATH
        self.positive_keywords: Set[str] = set()
        self.negative_keywords: Set[str] = set()
        self.min_budget: Optional[float] = None
        self.raw_bullets: List[str] = []
        self.reload()

    def reload(self) -> None:
        """Reads and parses configs/you.txt."""
        self.positive_keywords.clear()
        self.negative_keywords.clear()
        self.raw_bullets.clear()
        self.min_budget = None

        if not self.file_path.exists():
            logger.warning("Profile memory file %s not found. Using defaults.", self.file_path)
            return

        try:
            content = self.file_path.read_text(encoding="utf-8")
            lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
            
            for line in lines:
                # Strip leading numbering like "1. ", "- ", "* "
                clean_line = re.sub(r"^\d+[\.\)]\s*|^\*\s*|^-\s*", "", line)
                self.raw_bullets.append(clean_line)

                line_lower = clean_line.lower()

                # Check if this line is an exclusion rule
                is_exclusion = any(neg in line_lower for neg in ["do not want", "don't want", "no ", "exclude", "avoid", "not want"])

                # Extract words/tokens
                words = set(re.findall(r"\b[a-zA-Z0-9\.\+#\-]+\b", line_lower))

                # Extract budget numbers if mentioned (e.g. $1,000 or $1000)
                budget_match = re.search(r"\$\s*([0-9,]+)", clean_line)
                if budget_match:
                    try:
                        val = float(budget_match.group(1).replace(",", ""))
                        if self.min_budget is None or val < self.min_budget:
                            self.min_budget = val
                    except ValueError:
                        pass

                # Token matching against common tech terms or user words
                for w in words:
                    if w in COMMON_TECH_TOKENS or len(w) > 2:
                        if is_exclusion:
                            if w not in {"do", "not", "want", "dont", "no", "exclude", "avoid", "or", "and"}:
                                self.negative_keywords.add(w)
                        else:
                            if w not in {"build", "specialize", "prefer", "work", "apps", "using", "with", "for", "the", "and", "remote", "contract", "freelance"}:
                                self.positive_keywords.add(w)

            logger.info("Loaded UserProfileMemory from %s: %d positive, %d negative keywords",
                        self.file_path, len(self.positive_keywords), len(self.negative_keywords))
        except Exception as e:
            logger.error("Error reading profile memory file %s: %s", self.file_path, e)

    def evaluate_lead(
        self,
        tags: List[str],
        category: str,
        content: str,
        estimated_budget: str = "",
    ) -> Dict[str, Any]:
        """Evaluates a lead against user profile preferences.
        
        Returns:
            dict with 'score_modifier' (+/- float), 'is_excluded' (bool), and 'matches' (list).
        """
        text_corpus = f"{category} {' '.join(tags)} {content}".lower()

        # 1. Check Exclusion Rules
        excluded_matches = [neg for neg in self.negative_keywords if neg in text_corpus]
        if excluded_matches:
            return {
                "score_modifier": -50.0,
                "is_excluded": True,
                "reason": f"Matches exclusion keywords: {', '.join(excluded_matches)}",
                "matches": excluded_matches,
            }

        # 2. Match Positive Keywords
        positive_matches = [pos for pos in self.positive_keywords if pos in text_corpus]
        score_modifier = len(positive_matches) * 5.0  # +5 points per matched skill keyword

        # Cap modifier at +25.0 max
        score_modifier = min(score_modifier, 25.0)

        # 3. Budget Boost
        if self.min_budget and estimated_budget:
            nums = re.findall(r"\$\s*([0-9,]+)", estimated_budget)
            if nums:
                try:
                    lead_budget = float(nums[0].replace(",", ""))
                    if lead_budget >= self.min_budget:
                        score_modifier += 10.0
                except ValueError:
                    pass

        return {
            "score_modifier": score_modifier,
            "is_excluded": False,
            "reason": f"Matches positive skills: {', '.join(positive_matches)}" if positive_matches else "Standard profile match",
            "matches": positive_matches,
        }
