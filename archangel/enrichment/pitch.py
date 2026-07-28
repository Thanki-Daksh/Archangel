"""Deterministic Pitch Generator Engine.

Generates highly personalized outreach angles based on extracted intelligence.
"""

from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class PitchAngle:
    opening_line: str
    value_proposition: str
    call_to_action: str
    angle_type: str

    def to_dict(self) -> dict:
        return asdict(self)

class PitchGenerator:
    """Generates personalized pitches based on lead intelligence."""
    
    def generate(self, enriched_data: Dict[str, Any]) -> PitchAngle:
        
        health = enriched_data.get("website_health") or {}
        pains = enriched_data.get("pain_categories", [])
        tech = enriched_data.get("detected_tech", [])
        company_name = enriched_data.get("company_profile", {}).get("company_name", {}).get("value", "your company")
        
        # Determine Angle (Pain -> Tech -> Health -> General)
        angle_type = "General"
        opening_line = f"Saw what you're building at {company_name} and wanted to reach out."
        value_prop = "We help teams scale their engineering and ship features faster without full-time hiring overhead."
        
        # 1. Pain Angle (Highest Intent)
        if pains:
            angle_type = "Pain Resolution"
            first_pain = pains[0]
            pain_name = first_pain.get("name") if isinstance(first_pain, dict) else str(first_pain)
            opening_line = f"Saw you're tackling {pain_name.lower()} challenges at {company_name}."
            value_prop = f"We specialize in solving {pain_name.lower()} bottlenecks to help engineering teams ship reliably."
            
        # 2. Tech Specific Angle
        elif tech:
            angle_type = "Tech Specific"
            primary_tech = tech[0]
            opening_line = f"Noticed {company_name} is actively working with {primary_tech}."
            value_prop = f"We have deep hands-on expertise in {primary_tech} and help teams scale production systems rapidly."
            
        # 3. Performance & Health Angle (Fallback for low health with no explicit pain/tech)
        elif health and health.get("score", 100) < 80:
            angle_type = "Performance & Health"
            hooks = health.get("sales_hooks", [])
            hook_str = hooks[0] if hooks else "some performance bottlenecks"
            opening_line = f"Was reviewing {company_name} and noticed {hook_str.lower()}."
            value_prop = "We specialize in optimizing performance diagnostics and conversion infrastructure."

        cta = "Would you be open to a quick 10-minute chat this week to explore how we can help?"
        
        return PitchAngle(
            opening_line=opening_line,
            value_proposition=value_prop,
            call_to_action=cta,
            angle_type=angle_type
        )
