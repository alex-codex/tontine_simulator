import json
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Any
import uuid
import random

from tontine_config import TontineConfig, IndividualParticipantConfig
from tontine_state import TontineState, ParticipantState, ParticipantStatus

class TontineInitializer:
    """
    Initialiser une simulation de tontine à partir des fichiers de configuration
    """
    
    @staticmethod
    def load_config(config_path: str) -> Tuple[TontineConfig, List[IndividualParticipantConfig]]:
        """
        Load tontine and individual participant configurations from a JSON file
        """
        try:
            with open(config_path, 'r') as config_file:
                config_data = json.load(config_file)
                
            tontine_data = config_data["tontine"]
            
            num_start = tontine_data.get("num_participants_start", len(config_data.get("participants", [])))
            
            # Extract tontine config
            tontine_config = TontineConfig(
                num_participants_start=num_start,
                num_partipiants_min=tontine_data["num_partipiants_min"],
                monthly_contrib=tontine_data["monthly_contrib"],
                monthly_interest_rate=tontine_data["monthly_interest_rate"],
                monthly_distribution_percentage=tontine_data.get("monthly_distribution_percentage", 0.5),
                arrival_probability=tontine_data["arrival_probability"],
                cycle_duration_months=tontine_data.get("cycle_duration_months", 12),
                max_cycles=tontine_data.get("max_cycles", 5),
                emergency_fund_percentage=tontine_data.get("emergency_fund_percentage", 0.1),
                max_loan_amount=tontine_data.get("max_loan_amount", 0),
                late_payment_penalty=tontine_data.get("late_payment_penalty", 0.05),
                max_simultaneous_loans=tontine_data.get("max_simultaneous_loans", 3),
                min_membership_months=tontine_data.get("min_membership_months", 3)
            )
            
            # Extract individual participant configs
            participant_configs = []
            
            # Participants are explicitly defined in the config
            for participant_data in config_data["participants"]:
                config = IndividualParticipantConfig(
                    id=participant_data.get("id", str(uuid.uuid4())),
                    name=participant_data.get("name", f"Participant {len(participant_configs)+1}"),
                    default_probability=participant_data["default_probability"],
                    loan_prob=participant_data["loan_prob"],
                    loan_reemboursement_prob=participant_data["loan_reemboursement_prob"],
                    exit_probability=participant_data["exit_probability"],
                    max_consecutive_defaults=participant_data.get("max_consecutive_defaults", 3)
                )
                participant_configs.append(config)
        
            
            return tontine_config, participant_configs
            
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            raise Exception(f"Failed to load configuration: {str(e)}")
    
    @staticmethod
    def create_initial_state(
        tontine_config: TontineConfig, 
        participant_configs: List[IndividualParticipantConfig]
    ) -> TontineState:
        """
        Create an initial tontine state based on the configuration
        """
        start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Create initial participant states
        active_participants = {}
        for participant_config in participant_configs:
            participant = ParticipantState(
                id=participant_config.id,
                config=participant_config,
                join_date=start_date,
                status=ParticipantStatus.ACTIVE,
                total_contributions=0.0,
                current_debt=0.0,
                active_loans=[],
                missed_payments=0,
                consecutive_defaults=0,
                last_payment_date=start_date,
                total_borrowed=0.0,
                total_repaid=0.0,
                is_eligible_for_loan=False,
                monthly_distributions_received=0.0
            )
            
            active_participants[participant_config.id] = participant
        
        return TontineState(
            current_date=start_date,
            cycle_number=1,
            month_in_cycle=1,
            active_participants=active_participants,
            total_participants_history=len(active_participants),
            treasury_balance=0.0,
            emergency_fund=0.0,
            total_loans_outstanding=0.0,
            total_contributions_received=0.0,
            total_interest_earned=0.0,
            default_rate=0.0,
            loan_recovery_rate=0.0,
            cycle_contributions=0.0,
            cycle_defaults=0,
            cycle_new_members=0,
            cycle_exits=0
        )