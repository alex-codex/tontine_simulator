# Tontine Simulator
------------------------------------

## Description

A simulation tool for modeling and analyzing tontine operations. A tontine is a group-based financial arrangement where members make regular contributions to a common fund and can benefit from loans, with specific rules for membership, contributions, and loan distribution.

## Key Features

- Realistic simulation of tontine dynamics
- Participant behavior modeling including:
  - Payment defaults
  - Loan requests
  - Member arrivals and departures
- Financial tracking including:
  - Treasury balance
  - Emergency fund
  - Loan management
  - Interest calculations
- Risk metrics and performance indicators

## Model Components

### Configuration
- `TontineConfig`: Global tontine parameters
- `ParticipantConfig`: Individual participant behavior parameters

### State Tracking
- `TontineState`: Current state of the tontine
- `ParticipantState`: Individual member status and history

## Usage

[Usage instructions to be added]

## Parameters

The simulation takes into account various parameters including:
- Initial number of participants
- Monthly contribution amounts
- Interest rates
- Default probabilities
- Member arrival/exit rates
- Loan-related parameters

## Output Metrics

The simulation provides insights on:
- Treasury health
- Default rates
- Member retention
- Loan performance
- Overall tontine sustainability

## License

[License information to be added]

## Fonctionnalités
- Gestion des participants (adhésion, départ, défaut de paiement, emprunts, remboursements).
- Cotisations mensuelles et accumulation des fonds de la tontine.
- Attribution et gestion des prêts avec taux d'intérêt.
- Pénalités en cas de retard ou de sortie anticipée.
- Simulation sur plusieurs cycles avec conditions de faillite.
- Gestion des fonds d'urgence et des règles d'exclusion.

## Configuration

### TontineConfig
La configuration de la tontine est définie par la classe `TontineConfig` avec les paramètres suivants :

| Paramètre | Type | Description |
|-----------|------|-------------|
| `num_participants_start` | `int` | Nombre initial de participants |
| `num_participants_min` | `int` | Seuil minimum de participants avant faillite |
| `monthly_contrib` | `float` | Montant de la cotisation mensuelle par participant |
| `monthly_interest_rate` | `float` | Taux d'intérêt mensuel appliqué aux prêts |
| `arrival_probability` | `float` | Probabilité qu'un nouveau participant rejoigne la tontine à la fin d'un cycle |
| `cycle_duration_months` | `int` | Durée d'un cycle en mois (ex: 12 mois) |
| `max_cycles` | `int` | Nombre maximum de cycles de la tontine |
| `emergency_fund_percentage` | `float` | Pourcentage des cotisations réservé au fonds d'urgence |
| `max_loan_amount` | `float` | Montant maximum qu'un participant peut emprunter |
| `late_payment_penalty` | `float` | Pénalité en pourcentage pour retard de paiement |
| `max_simultaneous_loans` | `int` | Nombre maximum de prêts actifs simultanément |
| `min_membership_months` | `int` | Durée minimale d'adhésion avant d'être éligible aux prêts |

### ParticipantConfig
La classe `ParticipantConfig` définit les comportements des participants avec les paramètres suivants :

| Paramètre | Type | Description |
|-----------|------|-------------|
| `default_probability` | `float` | Probabilité qu'un participant fasse défaut sur un paiement mensuel |
| `loan_prob` | `float` | Probabilité qu'un participant demande un prêt |
| `loan_reemboursement_prob` | `float` | Probabilité qu'un participant rembourse sa dette à échéance |
| `exit_probability` | `float` | Probabilité qu'un participant quitte la tontine à la fin d'un cycle |
| `max_consecutive_defaults` | `int` | Nombre maximal de défauts consécutifs avant exclusion |
| `credit_score_threshold` | `float` | Score de crédit minimum pour être éligible aux prêts |
| `max_loan_to_contribution_ratio` | `float` | Ratio maximum prêt/cotisations totales |
| `early_exit_penalty` | `float` | Pénalité en pourcentage pour sortie anticipée |
| `guarantor_required` | `bool` | Indique si un garant est requis pour les prêts |

