# Simulateur de Tontine
------------------------------------

## Description

Outil de simulation pour modéliser et analyser le fonctionnement d'une tontine. Une tontine est un système financier collectif où les membres effectuent des contributions régulières dans un fonds commun et peuvent bénéficier de prêts, selon des règles spécifiques de participation, contributions et distribution des prêts.

## Principales Caractéristiques

- Simulation réaliste de la dynamique des tontines
- Modélisation du comportement des participants incluant :
  - Défaut de paiement
  - Demande de prêt
  - Arrivées et départs des membres
- Suivi financier incluant :
  - Solde de la trésorerie
  - Fonds d'urgence
  - Gestion des prêts
  - Calcul des intérêts
- Indicateurs de risque et de performance

## Composants du Modèle

### Configuration
- `TontineConfig` : Paramètres globaux de la tontine
- `IndividualParticipantConfig` : Paramètres individuels de comportement des participants

### Suivi d'État
- `TontineState` : État actuel de la tontine
- `ParticipantState` : Statut et historique de chaque membre

## Utilisation
Pour démarrer la simulation, installez d'abord les dépendances (voir section Installation) puis exécutez la commande suivante :

```bash
python run_simulation.py --config config_sample.json --months 36 --output results
```

## Paramètres

La simulation prend en compte divers paramètres incluant :
- Nombre initial de participants
- Montant des cotisations mensuelles
- Taux d'intérêts mensuels
- Probabilités de défaut de paiement
- Taux d'arrivée et de départ des membres
- Paramètres relatifs aux prêts

## Indicateurs de Sortie

La simulation fournit des informations sur :
- La santé de la trésorerie
- Les taux de défaut
- La rétention des membres
- La performance des prêts
- La durabilité globale de la tontine

## Licence

[Informations de licence à ajouter]

## Fonctionnalités
- Gestion des participants (adhésion, départ, défaut de paiement, demande d'emprunt, remboursements).
- Cotisations mensuelles et accumulation des fonds de la tontine.
- Attribution et gestion des prêts avec taux d'intérêts.
- Pénalités en cas de retard ou de sortie anticipée.
- Simulation sur plusieurs cycles avec conditions de faillite.
- Gestion des fonds d'urgence et des règles d'exclusion.

## Configuration

### TontineConfig
La configuration de la tontine est définie par la classe `TontineConfig` avec les paramètres suivants :

| Paramètre | Type | Description |
|-----------|------|-------------|
| `num_participants_min` | `int` | Seuil minimum de participants avant faillite |
| `monthly_contrib` | `float` | Montant de la cotisation mensuelle par participant |
| `monthly_interest_rate` | `float` | Taux d'intérêt mensuel appliqué aux prêts |
| `arrival_probability` | `float` | Probabilité qu'un nouveau participant rejoigne la tontine à la fin d'un cycle |
| `cycle_duration_months` | `int` | Durée d'un cycle en mois (ex: 12 mois) |
| `max_cycles` | `int` | Nombre maximum de cycles de la tontine |
| `emergency_fund_percentage` | `float` | Pourcentage des cotisations réservé au fonds d'urgence |
| `max_loan_amount` | `float` | Montant maximum qu'un participant peut emprunter |
| `late_payment_penalty` | `float` | Pénalité en cas de retard de paiement |
| `max_simultaneous_loans` | `int` | Nombre maximum de prêts actifs simultanément |
| `min_membership_months` | `int` | Durée minimale d'adhésion avant d'être éligible aux prêts |
| `monthly_distribution_percentage` | `float` | Pourcentage des cotisations redistribué chaque mois |

### IndividualParticipantConfig
La classe `IndividualParticipantConfig` définit les comportements des participants avec les paramètres suivants :

| Paramètre | Type | Description |
|-----------|------|-------------|
| `default_probability` | `float` | Probabilité qu'un participant fasse défaut sur un paiement mensuel |
| `loan_prob` | `float` | Probabilité qu'un participant demande un prêt |
| `loan_reemboursement_prob` | `float` | Probabilité qu'un participant rembourse sa dette à échéance |
| `exit_probability` | `float` | Probabilité qu'un participant quitte la tontine à la fin d'un cycle |
| `max_consecutive_defaults` | `int` | Nombre maximum de défauts consécutifs avant exclusion |




### TODO : Détails sur la modélisation stochastique et profils de participants