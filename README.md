# Modélisation et Analyse Stochastique d'une Tontine

## Introduction
La tontine est un système de finance sociale et collective dont la stabilité repose sur la synchronisation des flux de cotisations individuelles. L'objectif de ce projet est de dépasser la simple analyse descriptive pour proposer une **analyse inférentielle et stochastique** de la robustesse d'un tel système. En abandonnant l'approche déterministe et "naïve" (une simulation à exécution unique), ce projet quantifie l'incertitude globale et prédit le risque de défaillance du fonds grâce à des modèles mathématiques et probabilistes avancés.

![Perspectives](https://147776342.fs1.hubspotusercontent-eu1.net/hubfs/147776342/tontine.png)

## Technologies et Outils
* **Langages de programmation :** Python (moteur stochastique et visualisation), C (pour le projet initial de gestion de tontine).
* **Mathématiques & Statistiques :** Algèbre Linéaire, Probabilités (Théorème Central Limite, Loi des Grands Nombres).

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


## Installation
```bash
pip install -r requirements.txt
```
##  Méthodologie : Les 3 Piliers du Modèle

## Utilisation
Pour démarrer la simulation, installez d'abord les dépendances (voir section Installation) puis exécutez la commande suivante :

```bash
python run_simulation.py --config config_sample.json --months 36 --output results
```

### 1. La Rigueur de Markov (Modélisation Comportementale)
Afin de capturer la persistance du comportement individuel (un défaut ponctuel est souvent corrélé à une incapacité de paiement future), le modèle utilise des **chaînes de Markov à temps discret**.
Trois états fondamentaux sont définis dans le système :
* **ACTIF :** Le membre cotise nominalement et est éligible aux prêts.
* **DÉFAUT :** Échec de cotisation ; la dette et les intérêts s'accumulent.
* **EXCLU :** État absorbant atteint après le dépassement d'un seuil de défauts consécutifs.

  
![Perspectives](https://147776342.fs1.hubspotusercontent-eu1.net/hubfs/147776342/graphe.png)

L'étude de la **matrice de transition (P)** de format 3x3 permet de calculer la convergence du système vers son état stationnaire et d'évaluer le risque de chaque individu analytiquement, sans passer par la simulation.

### 2. Le Moteur Monte Carlo (Quantification Globale)
Là où l'algèbre de Markov étudie la persistance individuelle, la méthode de **Monte Carlo** se concentre sur la liquidité systémique. En s'appuyant sur le principe d'ergodicité et la Loi des Grands Nombres, des centaines de trajectoires (cycles de 36 mois) sont générées :
* **Résolution de l'incertitude :** Les fluctuations aléatoires s'annulent pour révéler la moyenne de l'ensemble de la population.
* **Évaluation des risques :** Extraction des indicateurs clés tels que la médiane de trésorerie, la volatilité et surtout la probabilité de faillite (quand la trésorerie passe sous la barre de zéro).
* **Intervalle de Confiance :** Définition de la zone de sécurité financière (IC 95%) certifiant l'enveloppe de probabilité de l'évolution du solde.

### 3. Visualisation Avancée par KDE (Signature de Risque)
Pour pallier le "bruit visuel" et l'aspect discontinu de l'histogramme classique, la trésorerie finale de la tontine est modélisée par un **KDE (Kernel Density Estimation)**.
Ce lissage de la distribution respecte la véritable fluidité de l'argent et met en lumière :
* **Le Sommet :** Le scénario financier le plus probable.
* **La Zone de Faillite :** La zone critique située en dessous de zéro.
* **Le 95e centile (P95) :** Les quelques scénarios extrêmement optimistes tirant la moyenne vers le haut.

![Perspectives](https://147776342.fs1.hubspotusercontent-eu1.net/hubfs/147776342/kde_tresorerie.png)
##  Scénarios et Configurations Observés
Les tests restent à effectuer !!

##  Perspectives d'Évolution et Validation Statistique
Cette version n'est que la fondation d'un outil d'aide à la décision complet. Les prochains axes d'amélioration intègrent la validation inférentielle :
* **Analyse Comparative (ANOVA) :** Sortir du scénario unique pour comparer simultanément l'impact de plusieurs groupes hétérogènes (profils prudents vs risqués) et attester que les différences de trésorerie sont statistiquement significatives.
* **Test de Conformité ($\chi^2$) :** Garantir techniquement que les fréquences observées dans les simulations Monte Carlo sont en stricte adéquation avec les probabilités du modèle théorique de Markov.
* **Dynamique comportementale rétroactive :** Modéliser des scénarios où la baisse du trésor influe en temps réel sur la confiance (et donc sur le taux de défaut) des membres.

![Perspectives](https://147776342.fs1.hubspotusercontent-eu1.net/hubfs/147776342/perspectives.png)
