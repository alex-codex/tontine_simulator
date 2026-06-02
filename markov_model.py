"""
markov_model.py
===============
Modélisation par chaînes de Markov du comportement des participants d'une tontine.

RAPPEL MATHÉMATIQUE
  - Espace d'états S = {ACTIF, DÉFAUT, EXCLU}
  - Une matrice de transition P
  - La propriété de Markov : l'état actuel ne depend que de l'état immédiatement précédent

La distribution au temps t est :  π_t = π_0 · P^t
La distribution STATIONNAIRE π vérifie : π = π · P


ÉTATS
-----
  0 = ACTIF  : cotise normalement, éligible aux prêts
  1 = DÉFAUT : ne cotise pas ce mois, dette croît avec intérêts
  2 = EXCLU  : état absorbant — on ne peut plus en sortir (atteint après max_consecutive_defaults défauts consécutifs)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict
import warnings
from tontine_config import IndividualParticipantConfig


ACTIF  = 0
DEFAUT = 1
EXCLU  = 2
ETATS  = ["ACTIF", "DÉFAUT", "EXCLU"]


@dataclass
class MarkovResult:
    """
    Résultat de l'analyse de Markov pour un participant.

    Attributs:

    participant_id : str
    participant_name : str
    transition_matrix : np.ndarray, shape (3, 3)
        P[i, j] = probabilité de passer de l'état i à l'état j en un mois.
    stationary : np.ndarray, shape (3,)
    expected_active_months : float
    convergence_months : int
    risk_score : float  ∈ [0, 1]
        Score de risque synthétique = 1 - π_A.
        0 = participant parfait, 1 = exclu immédiat.
    """
    participant_id: str
    participant_name: str
    transition_matrix: np.ndarray
    stationary: np.ndarray
    expected_active_months: float
    convergence_months: int
    risk_score: float


class ParticipantMarkovChain:
    """
    Construit et analyse la chaîne de Markov d'un participant.

    La matrice P est construite à partir des probabilités du config :
      - default_probability     -> p  (probabilité de défaut mensuel)
      - max_consecutive_defaults -> k  (seuil d'exclusion)
      - exit_probability         -> départ volontaire en fin de cycle

     q = probabilité d'être exclu SACHANT qu'on est en DÉFAUT
          approximation : 1/k pour k défauts max
          (après k défauts consécutifs, on est exclu -> en moyenne 1 chance sur k par mois de défaut)

    """

    def __init__(self, config: IndividualParticipantConfig):
        self.config = config
        self._P = None

    def build_matrix(self) -> np.ndarray:
    
        p = self.config.default_probability          
        k = max(1, self.config.max_consecutive_defaults)  

       
        q = min(0.99, 1.0 / k)

        P = np.array([
            [1 - p,    p,          0.0   ],
            [1 - p,    p * (1-q),  p * q ],
            [0.0,      0.0,        1.0   ],
        ], dtype=float)

       
        row_sums = P.sum(axis=1)
        if not np.allclose(row_sums, 1.0, atol=1e-10):
            warnings.warn(
                f"Participant {self.config.id} : les lignes de P ne somment pas à 1. "
                f"Sums = {row_sums}. Renormalisation automatique."
            )
            P = P / row_sums[:, np.newaxis]

        self._P = P
        return P

    #La methode stationnary_distribution 
    def stationary_distribution(self) -> np.ndarray:
        """
        Calcule la distribution stationnaire π par méthode algébrique.

        MÉTHODE : résoudre le système linéaire π · P = π avec somme(π_i) = 1.
        
        Returns
        -------
        pi : np.ndarray, shape (3,)
            [π_ACTIF, π_DÉFAUT, π_EXCLU]
        """
        if self._P is None:
            self.build_matrix()

        P = self._P
        n = P.shape[0]

        
        A = (P - np.eye(n)).T
        A[:, -1] = 1.0 

        b = np.zeros(n)
        b[-1] = 1.0

        try:
            pi = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            pi = np.array([1.0, 0.0, 0.0])

        pi = np.clip(pi, 0, 1)
        pi /= pi.sum()

        return pi

    def simulate_distribution(self, months: int = 36) -> np.ndarray:
        """
        Calcule la distribution π_t = π_0 · P^t mois par mois
        en partant de l'état ACTIF (π_0 = [1, 0, 0]).

        Usgae : visualiser la convergence vers la distribution stationnaire.

        Returns
        -------
        history : np.ndarray, shape (months+1, 3)
            history[t] = [P(ACTIF au mois t), P(DÉFAUT), P(EXCLU)]
        """
        if self._P is None:
            self.build_matrix()

        pi = np.array([1.0, 0.0, 0.0]) 
        history = [pi.copy()]

        for _ in range(months):
            pi = pi @ self._P
            history.append(pi.copy())

        return np.array(history)

    def convergence_speed(self, tol: float = 1e-6) -> int:
        """
        Nombre de mois avant que ||π_t - π_infini|| < tol.

        Paramètres
        ----------
        tol : float
            Tolérance sur la distance L1 entre π_t et π_infini.

        Returns
        -------
        t_conv : int
            Mois de convergence. Retourne 999 si pas convergé en 500 mois.
        """
        pi_inf = self.stationary_distribution()
        history = self.simulate_distribution(months=500)

        for t, pi_t in enumerate(history):
            if np.sum(np.abs(pi_t - pi_inf)) < tol:
                return t

        return 999

    def analyze(self, horizon_months: int = 36) -> MarkovResult:
       
        P   = self.build_matrix()
        pi  = self.stationary_distribution()
        t_c = self.convergence_speed()

        expected_active = pi[ACTIF] * horizon_months
        risk_score = 1.0 - pi[ACTIF]

        return MarkovResult(
            participant_id=self.config.id,
            participant_name=self.config.name,
            transition_matrix=P,
            stationary=pi,
            expected_active_months=expected_active,
            convergence_months=t_c,
            risk_score=risk_score,
        )


class TontineMarkovAnalyzer:
    """
    Analyse l'ensemble des participants d'une tontine par chaînes de Markov.

    Permet de :
    - Comparer les profils de risque entre participants
    - Estimer l'impact financier
    - Détecter les participants à risque élevé avant simulation
    - Comparer des configurations différentes
    """

    def __init__(self, configs: List[IndividualParticipantConfig], horizon_months: int = 36):
        self.configs = configs
        self.horizon = horizon_months
        self.results: Dict[str, MarkovResult] = {}

    def analyze_all(self) -> Dict[str, MarkovResult]:
        """
        Lance l'analyse de Markov pour chaque participant.

        Returns
        -------
        dict[participant_id → MarkovResult]
        """
        for config in self.configs:
            chain = ParticipantMarkovChain(config)
            self.results[config.id] = chain.analyze(self.horizon)
        return self.results

    def summary_dataframe(self):

        import pandas as pd

        if not self.results:
            self.analyze_all()

        rows = []
        for r in self.results.values():
            rows.append({
                "id":                     r.participant_id,
                "name":                   r.participant_name,
                "pi_actif":               round(r.stationary[ACTIF],  4),
                "pi_defaut":              round(r.stationary[DEFAUT], 4),
                "pi_exclu":               round(r.stationary[EXCLU],  4),
                "expected_active_months": round(r.expected_active_months, 2),
                "risk_score":             round(r.risk_score, 4),
                "convergence_months":     r.convergence_months,
            })

        return pd.DataFrame(rows).sort_values("risk_score", ascending=False)

    def expected_total_contributions(self, monthly_contrib: float) -> float:
        
        if not self.results:
            self.analyze_all()

        total = sum(
            r.expected_active_months * monthly_contrib
            for r in self.results.values()
        )
        return round(total, 2)

    def high_risk_participants(self, threshold: float = 0.5) -> List[MarkovResult]:
        
        if not self.results:
            self.analyze_all()

        risky = [r for r in self.results.values() if r.risk_score > threshold]
        return sorted(risky, key=lambda r: r.risk_score, reverse=True)

    def compare_configs(
        self,
        configs_a: List[IndividualParticipantConfig],
        configs_b: List[IndividualParticipantConfig],
        label_a: str = "Config A",
        label_b: str = "Config B",
    ) -> dict:
        """
        Compare deux ensembles de configurations.
        Retourne un dict avec les métriques agrégées pour chaque groupe.

        Utilisation typique : tester l'effet de changer max_consecutive_defaults
        de 2 à 3 sur la stabilité globale de la tontine.

        Returns
        -------
        dict avec clés label_a, label_b, chacun contenant :
            - mean_pi_actif : moyenne de π(ACTIF) sur le groupe
            - mean_risk_score
            - expected_contributions (pour une cotisation fictive de 100)
        """
        def _aggregate(configs):
            analyzer = TontineMarkovAnalyzer(configs, self.horizon)
            analyzer.analyze_all()
            pis = [r.stationary[ACTIF] for r in analyzer.results.values()]
            return {
                "mean_pi_actif":   round(float(np.mean(pis)), 4),
                "std_pi_actif":    round(float(np.std(pis)),  4),
                "mean_risk_score": round(float(np.mean([r.risk_score for r in analyzer.results.values()])), 4),
                "expected_contributions": analyzer.expected_total_contributions(100.0),
            }

        return {
            label_a: _aggregate(configs_a),
            label_b: _aggregate(configs_b),
        }



#  Exemple d'utilisation rapide
if __name__ == "__main__":
    import json

    SEP  = "─" * 60
    SEP2 = "═" * 60

    with open("config_sample.json") as f:
        data = json.load(f)

    from tontine_config import IndividualParticipantConfig

    configs = [
        IndividualParticipantConfig(
            id=p["id"],
            name=p["name"],
            default_probability=p["default_probability"],
            loan_prob=p["loan_prob"],
            loan_reemboursement_prob=p["loan_reemboursement_prob"],
            exit_probability=p["exit_probability"],
            max_consecutive_defaults=p.get("max_consecutive_defaults", 2),
        )
        for p in data["participants"]
    ]

    analyzer = TontineMarkovAnalyzer(configs, horizon_months=36)
    analyzer.analyze_all()

    print(f"\n{SEP2}")
    print("  BLOC 1 — Synthèse par participant")
    print(f"{SEP2}")
    print(
        "Lecture : π_actif = proportion du temps actif à long terme.\n"
        "risk_score = 1 - π_actif. Plus c'est proche de 1, plus c'est risqué.\n"
        "expected_active_months = π_actif × 36 mois = cotisations espérées / 100.\n"
    )
    df = analyzer.summary_dataframe()
    print(df.to_string(index=False))

    print(f"\n{SEP2}")
    print("  BLOC 2 — Matrices de transition P par participant")
    print(f"{SEP2}")
    print(
        "Lecture : P[i,j] = probabilité de passer de l'état i à j en 1 mois.\n"
        "Chaque LIGNE somme à 1.0.\n"
        "Colonnes : [ACTIF, DÉFAUT, EXCLU]\n"
    )
    for r in analyzer.results.values():
        print(f"{SEP}  {r.participant_name} (p_défaut={configs[[c.id for c in configs].index(r.participant_id)].default_probability})")
        header = f"  {'':12}  {'→ ACTIF':>10}  {'→ DÉFAUT':>10}  {'→ EXCLU':>10}"
        print(header)
        labels = ["depuis ACTIF ", "depuis DÉFAUT", "depuis EXCLU "]
        for i, row in enumerate(r.transition_matrix):
            print(f"  {labels[i]}  {row[0]:>10.4f}  {row[1]:>10.4f}  {row[2]:>10.4f}")
        print(f"  → π stationnaire : ACTIF={r.stationary[ACTIF]:.4f}  DÉFAUT={r.stationary[DEFAUT]:.4f}  EXCLU={r.stationary[EXCLU]:.4f}")

    print(f"\n{SEP2}")
    print("  BLOC 3 — Trajectoire P(ACTIF au mois t) sur 36 mois")
    print(f"{SEP2}")
    print(
        "Lecture : chaque ligne = mois t, valeur = probabilité d'être ACTIF ce mois-là.\n"
        "On part toujours de π_0 = [1, 0, 0] (participant actif au départ).\n"
        "On affiche 3 profils contrastés : faible / moyen / élevé risque.\n"
    )

    sorted_results = sorted(analyzer.results.values(), key=lambda r: r.risk_score)
    profils_choisis = [sorted_results[0], sorted_results[len(sorted_results)//2], sorted_results[-1]]
    labels_profil   = ["(faible risque)", "(risque moyen)", "(risque élevé)"]

    print(f"  {'Mois':>5}", end="")
    for r, lbl in zip(profils_choisis, labels_profil):
        col = f"{r.participant_name} {lbl}"
        print(f"  {col:>30}", end="")
    print()

   
    histories = []
    for r in profils_choisis:
        chain = ParticipantMarkovChain(configs[[c.id for c in configs].index(r.participant_id)])
        chain.build_matrix()
        histories.append(chain.simulate_distribution(months=36))

    checkpoints = [0, 1, 2, 3, 6, 12, 18, 24, 30, 36]
    for t in checkpoints:
        print(f"  {t:>5}", end="")
        for hist in histories:
            bar_len = int(hist[t][ACTIF] * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"  {hist[t][ACTIF]:.4f} [{bar}]", end="")
        print()

    print(
        "\n  Lecture de la barre : █ = proportion active, ░ = proportion non-active.\n"
        "  La valeur converge vers π_actif (distribution stationnaire)."
    )


    print(f"\n{SEP2}")
    print("  BLOC 4 — Note sur la convergence")
    print(f"{SEP2}")
    
    print(f"\n{SEP2}")
    print("  BLOC 5 — Comparaison : max_consecutive_defaults = 2 vs 3")
    print(f"{SEP2}")


    import copy
    configs_k3 = []
    for c in configs:
        c2 = c.clone()
        c2.max_consecutive_defaults = 3
        configs_k3.append(c2)

    comparison = analyzer.compare_configs(
        configs_a=configs,
        configs_b=configs_k3,
        label_a="k=2 (actuel)",
        label_b="k=3 (assoupli)",
    )
    for label, metrics in comparison.items():
        print(f"  {label}")
        for k, v in metrics.items():
            print(f"    {k:<30} = {v}")
        print()

    print(f"\n{SEP2}")
    print("  BLOC 6 — Estimation financière Markov")
    print(f"{SEP2}")
    contrib = data["tontine"]["monthly_contrib"]
    esperees = analyzer.expected_total_contributions(contrib)
    theorique = len(configs) * 36 * contrib
    print(
        f"  Cotisation mensuelle            : {contrib:.2f} €\n"
        f"  Cotisations théoriques max      : {theorique:.2f} €  (si 0% défaut)\n"
        f"  Cotisations espérées (Markov)   : {esperees:.2f} €\n"
        f"  Manque à gagner estimé          : {theorique - esperees:.2f} €\n"
        f"\n"
        f"  Interprétation : le modèle Markov prédit que la tontine collectera\n"
        f"  seulement {100*esperees/theorique:.1f}% des cotisations théoriques sur 36 mois.\n"
        f"  C'est une borne AVANT Monte Carlo — la vraie valeur variera autour de ça."
    )