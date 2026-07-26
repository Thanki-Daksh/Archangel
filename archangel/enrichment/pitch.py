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
        
        # 1. Determine Angle
        angle_type = "General"
        opening_line = f"Saw what you're building at {company_name} and wanted to reach out."
        value_prop = "We help companies like yours scale their engineering without the overhead of full-time hires."
        
        # Health Angle
        if health and health.get("score", 100) < 80:
            angle_type = "Performance & Health"
            hooks = health.get("sales_hooks", [])
            hook_str = hooks[0] if hooks else "some performance bottlenecks"
            opening_line = f"Was checking out {company_name} and noticed {hook_str.lower()}."
            value_prop = "We specialize in fixing these exact issues to improve conversion rates and user experience."
            
        # Tech Angle
        elif tech:
            angle_type = "Tech Specific"
            primary_tech = tech[0]
            opening_line = f"Noticed {company_name} is built on {primary_tech}."
            value_prop = f"We have deep expertise in {primary_tech} and help teams scale their infrastructure rapidly."
            
        # Pain Angle
        elif pains:
            angle_type = "Pain Resolution"
            primary_pain = pains[0].get("name", "scaling challenges")
            opening_line = f"Saw you're dealing with {primary_pain.lower()} at {company_name}."
            value_prop = f"We've helped several companies overcome similar {primary_pain.lower()} and get back to shipping features."

        cta = "Would you be open to a quick 10-minute chat this week to see if there's a fit?"
        
        return PitchAngle(
            opening_line=opening_line,
            value_proposition=value_prop,
            call_to_action=cta,
            angle_type=angle_type
        )
