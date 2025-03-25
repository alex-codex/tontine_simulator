from dataclasses import dataclass


@dataclass
class TontineConfig: 
    num_participants_start: int  # Le nombre de participants initial de la tontine
    num_partipiants_min: int     # Le nombre minimal de participants dans la tontine (ie le nombre de participants est inférieur à ce nombre alors la tontine fait faillite)
    monthly_contrib: float       # Le montant de la cotisation mensuelle par participant
    monthly_interest_rate: float # Le taux d'intérêt mensuel par participants en cas de prêt
    arrival_probability: float   # La probabilité qu'un participant rejoigne la tontine à la fin d'un cycle (d'une année)
    cycle_duration_months: int   # Durée d'un cycle en mois (typiquement 12 mois)
    max_cycles: int              # Nombre maximum de cycles avant la fin de la tontine
    emergency_fund_percentage: float  # Pourcentage des cotisations réservé pour le fonds d'urgence
    max_loan_amount: float            # Montant maximum qu'un participant peut emprunter
    late_payment_penalty: float       # Pénalité en pourcentage pour retard de paiement
    max_simultaneous_loans: int       # Nombre maximum de prêts actifs simultanément
    min_membership_months: int        # Durée minimale d'adhésion avant d'être éligible aux prêts
    monthly_distribution_percentage: float  # Pourcentage des cotisations redistribué chaque mois


@dataclass
class IndividualParticipantConfig:
    id: str
    name: str
    default_probability: float
    loan_prob: float
    loan_reemboursement_prob: float
    exit_probability: float
    max_consecutive_defaults: int
    
    def clone(self):
        return IndividualParticipantConfig(
                id=self.id,
                name=self.name,
                default_probability=self.default_probability,
                loan_prob=self.loan_prob,
                loan_reemboursement_prob=self.loan_reemboursement_prob,
                exit_probability=self.exit_probability,
                max_consecutive_defaults=self.max_consecutive_defaults

        )
