# Modélisation et Analyse Stochastique d'une Tontine

## Introduction
La tontine est un système de finance sociale et collective dont la stabilité repose sur la synchronisation des flux de cotisations individuelles. L'objectif de ce projet est de dépasser la simple analyse descriptive pour proposer une **analyse inférentielle et stochastique** de la robustesse d'un tel système. En abandonnant l'approche déterministe et "naïve" (une simulation à exécution unique), ce projet quantifie l'incertitude globale et prédit le risque de défaillance du fonds grâce à des modèles mathématiques et probabilistes avancés.

![Perspectives](https://147776342.fs1.hubspotusercontent-eu1.net/hubfs/147776342/tontine.png)

## Technologies et Outils
* **Langages de programmation :** Python (moteur stochastique et visualisation), C (pour le projet initial de gestion de tontine).
* **Mathématiques & Statistiques :** Algèbre Linéaire, Probabilités (Théorème Central Limite, Loi des Grands Nombres).

##  Méthodologie : Les 3 Piliers du Modèle

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
