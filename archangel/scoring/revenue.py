"""Revenue Estimation Engine.

Estimates buying power and budget sizing based on heuristics.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class RevenueEstimate:
    estimated_arr_range: str
    estimated_budget: float
    confidence: float
    budget_level: str

    def to_dict(self) -> dict:
        return asdict(self)

class RevenueEstimator:
    """Calculates potential budget based on available company heuristics."""
    
    def evaluate(self, funding_stage: str, team_size: str, platform: str) -> RevenueEstimate:
        budget = 500.0  # Base budget
        confidence = 0.3
        arr_range = "$0 - $100K"
        
        # Funding heuristic
        if funding_stage:
            fs = funding_stage.lower()
            if "series c" in fs or "series d" in fs:
                budget += 50000.0
                confidence += 0.4
                arr_range = "$10M+"
            elif "series b" in fs:
                budget += 25000.0
                confidence += 0.3
                arr_range = "$5M - $10M"
            elif "series a" in fs:
                budget += 10000.0
                confidence += 0.3
                arr_range = "$1M - $5M"
            elif "seed" in fs:
                budget += 2000.0
                confidence += 0.2
                arr_range = "$100K - $1M"
            elif "bootstrapped" in fs:
                budget += 500.0
                confidence += 0.2
                arr_range = "$100K - $500K"
                
        # Team size heuristic
        if team_size and team_size != "Unknown":
            if "500" in team_size or "1000" in team_size:
                budget += 10000.0
                confidence += 0.2
                if "$10M" not in arr_range:
                    arr_range = "$10M+"
            elif "50" in team_size or "100" in team_size:
                budget += 5000.0
                confidence += 0.2
                if "$5M" not in arr_range and "$10M" not in arr_range:
                    arr_range = "$1M - $5M"
            elif "11" in team_size or "10" in team_size:
                budget += 1000.0
                confidence += 0.1
                
        # Platform noise (Upwork vs HN)
        if platform:
            plat = platform.lower()
            if "upwork" in plat or "fiverr" in plat:
                budget = min(budget, 2000.0) # Cap low-quality platforms
                confidence += 0.1
            elif "hackernews" in plat or "remoteok" in plat or "weworkremotely" in plat:
                budget += 1500.0
                confidence += 0.1
                
        if budget >= 10000.0:
            level = "Enterprise"
        elif budget >= 5000.0:
            level = "High"
        elif budget >= 1500.0:
            level = "Medium"
        else:
            level = "Low"
            
        return RevenueEstimate(
            estimated_arr_range=arr_range,
            estimated_budget=budget,
            confidence=round(min(0.95, confidence), 2),
            budget_level=level
        )
