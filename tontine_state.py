from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
from enum import Enum

from tontine_config import IndividualParticipantConfig

class ParticipantStatus(Enum):
    ACTIVE = "active"
    DEFAULTED = "defaulted"
    EXITED = "exited"

@dataclass
class ParticipantState:
    id: str
    config: IndividualParticipantConfig  # Add reference to participant's config
    join_date: datetime
    exit_date: datetime
    status: ParticipantStatus
    total_contributions: float
    current_debt: float
    active_loans: List[float]
    missed_payments: int
    consecutive_defaults: int
    last_payment_date: datetime
    total_borrowed: float
    total_repaid: float
    is_eligible_for_loan: bool
    monthly_distributions_received: float = 0.0  

@dataclass
class TontineState:
    current_date: datetime
    cycle_number: int
    month_in_cycle: int
    
    # Participants
    active_participants: Dict[str, ParticipantState]
    historical_participant : Dict[str, ParticipantState]
    total_participants_history: int
    
    # Financial State
    treasury_balance: float
    emergency_fund: float
    total_loans_outstanding: float
    total_contributions_received: float
    total_interest_earned: float
    
    # Risk Metrics
    default_rate: float
    loan_recovery_rate: float
    
    # Current Cycle Stats
    cycle_contributions: float
    cycle_defaults: int
    cycle_new_members: int
    cycle_exits: int
    
    # Round Robin
    round_robin_history: List[str] = field(default_factory=list)
    
    def is_cycle_end(self) -> bool:
        """Check if we're at the end of a cycle"""
        return self.month_in_cycle == 12
    
    def is_tontine_failed(self, config) -> bool:
        """Check if the tontine has failed based on configuration parameters"""
        return len(self.active_participants) < config.num_partipiants_min
    
    def get_participant_state(self, participant_id: str) -> ParticipantState | None:
        """Get the state of a specific participant"""
        return self.active_participants.get(participant_id)
    

