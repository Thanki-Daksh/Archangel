"""Historical Memory Graph Engine.

Cross-references past leads to determine recurring intent and map company history.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from archangel.storage import StorageBackend

@dataclass
class HistoricalContext:
    past_mentions: int
    first_seen_days_ago: int
    last_seen_days_ago: int
    urgency_multiplier: float

    def to_dict(self) -> dict:
        return asdict(self)

class HistoricalMemory:
    """Tracks companies across time to compute historical intent."""
    
    def __init__(self, storage: StorageBackend = None):
        self.storage = storage or StorageBackend.get_instance()
        
    def evaluate(self, domain: str, company_name: str, current_post_id: int) -> HistoricalContext:
        """Evaluates historical context for a given company/domain."""
        if not domain and not company_name:
            return HistoricalContext(0, 0, 0, 1.0)
            
        # Very simple historical check: query all leads, filter by domain or company_name
        # Note: In production at scale, this should be an indexed SQL query.
        # For V1.3, we iterate the recent leads (which is bounded)
        leads = self.storage.get_leads(limit=1000)
        
        matches = []
        for lead in leads:
            # Skip the current post itself
            if lead.get("id") == current_post_id:
                continue
                
            match = False
            # Check if domain matches (and is valid)
            if domain and domain.lower() != "unknown" and domain.lower() in str(lead.get("content", "")).lower():
                 # We don't have domain at the root level of get_leads output without a join in StorageBackend.
                 # Actually, get_leads in __init__.py joins with lead_scores and lead_analyses, but not lead_enrichments!
                 # So we rely on a text match or metadata. Let's just do a naive text search of the content for now.
                 match = True
            elif company_name and company_name.lower() != "unknown" and company_name.lower() in str(lead.get("content", "")).lower():
                 match = True
                 
            if match:
                matches.append(lead)
                
        if not matches:
            return HistoricalContext(0, 0, 0, 1.0)
            
        now = datetime.utcnow()
        timestamps = []
        
        for m in matches:
            ts = m.get("timestamp", 0)
            if ts:
                # Assuming timestamp is UNIX epoch
                try:
                    dt = datetime.utcfromtimestamp(float(ts))
                    timestamps.append(dt)
                except:
                    pass
                    
        if not timestamps:
            return HistoricalContext(len(matches), 0, 0, 1.2)
            
        first_seen = min(timestamps)
        last_seen = max(timestamps)
        
        first_days = (now - first_seen).days
        last_days = (now - last_seen).days
        
        # Urgency multiplier logic:
        # If they post frequently, urgency goes up.
        multiplier = 1.0
        
        # If seen in the last 30 days multiple times, high urgency
        if len(matches) > 1 and last_days < 30:
            multiplier = 1.5
        elif len(matches) > 0:
            multiplier = 1.2
            
        return HistoricalContext(
            past_mentions=len(matches),
            first_seen_days_ago=first_days,
            last_seen_days_ago=last_days,
            urgency_multiplier=round(multiplier, 2)
        )
