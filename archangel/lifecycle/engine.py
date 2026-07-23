"""Lead Lifecycle State Machine Engine."""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

VALID_LIFECYCLE_STATES = [
    "discovered",
    "analyzed",
    "contacted",
    "responded",
    "negotiating",
    "won",
    "lost",
    "paid",
    "archived",
]

TRANSITION_MAP = {
    "discovered": ["analyzed", "archived"],
    "analyzed": ["contacted", "archived"],
    "contacted": ["responded", "won", "lost", "archived"],
    "responded": ["negotiating", "lost", "archived"],
    "negotiating": ["won", "lost", "archived"],
    "won": ["paid", "archived"],
    "lost": ["archived"],
    "paid": ["archived"],
    "archived": ["discovered"],  # Can unarchive back to start if re-opened
}


class LifecycleEngine:
    """Manages lead pipeline states and transition validation."""

    def is_valid_state(self, state: str) -> bool:
        return state in VALID_LIFECYCLE_STATES

    def can_transition(self, current_state: str, new_state: str) -> bool:
        if not self.is_valid_state(new_state):
            return False
        if not current_state:
            return True
        allowed = TRANSITION_MAP.get(current_state, VALID_LIFECYCLE_STATES)
        return new_state in allowed
