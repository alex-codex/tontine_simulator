"""
monte_carlo.py
-----------
Simulation Monte Carlo de la tontine.

RAPPEL MATHÉMATIQUE
-------------------
Monte Carlo repose sur la loi des grands nombres :
    si X_1, X_2, ..., X_N sont N réalisations indépendantes d'une variable X,
    alors  (1/N) somme(X_i)  ->  E[X]  quand N -> infini

Ici X peut être : trésorerie finale,....
On obtient ainsi :
  - E[trésorerie]  =  moyenne empirique sur N runs
  - P(faillite)    =  nombre de runs en faillite / N
  - IC à 95%       =  [moyenne - 1.96·σ/√N,  moyenne + 1.96·σ/√N]

STRUCTURE
---------
  SimulationResult   : métriques d'un run
  MonteCarloEngine   : lance N runs et collecte les résultats
  MonteCarloAnalyzer : analyse statistique des N résultats
"""

import json
import io
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from rich.console import Console

from tontine_config import TontineConfig, IndividualParticipantConfig
from tontine_initializer import TontineInitializer
from tontine_executor import TontineExecutor



#  Structure : résultat d'un run
@dataclass
class SimulationResult:
    """
    Métriques collectées à la fin d'une simulation unique.

    Attributs
    ---------
    run_id : int
        Numéro du run (0 à N-1).
    failed : bool
        True si la tontine a fait faillite avant la fin des mois prévus.
        Critère : is_tontine_failed() retourne True dans l'executor.
    failure_month : Optional[int]
        Mois auquel la faillite s'est produite. None si pas de faillite.
    treasury_final : float
        Solde de la trésorerie au dernier mois simulé.
    default_rate : float
        Taux de défaut global = total défauts / total cotisations attendues.
        Récupéré directement depuis state.default_rate.
    total_contributions : float
        Cotisations effectivement collectées sur toute la simulation.
    active_participants_final : int
        Nombre de participants actifs au dernier mois.
    """
    run_id: int
    failed: bool
    failure_month: Optional[int]
    treasury_final: float
    default_rate: float
    total_contributions: float
    active_participants_final: int


class MonteCarloEngine:
    """
    Lance N simulations indépendantes et collecte les SimulationResult.

    Chaque run repart d'un état initial identique (même config)
    mais les tirages aléatoires internes (random.random()) diffèrent

    Paramètres
    ----------
    tontine_config : TontineConfig
    participant_configs : List[IndividualParticipantConfig]
    n_simulations : int
        Nombre de runs. 500
    num_months : int
        Durée de chaque simulation en mois.
    """

    def __init__(
        self,
        tontine_config: TontineConfig,
        participant_configs: List[IndividualParticipantConfig],
        n_simulations: int = 500,
        num_months: int = 36,
    ):
        self.tontine_config      = tontine_config
        self.participant_configs = participant_configs
        self.n_simulations       = n_simulations
        self.num_months          = num_months
        self.results: List[SimulationResult] = []

    def _silent_console(self) -> Console:
        
        buf = io.StringIO()
        return Console(file=buf, record=True, quiet=True)

    def _run_one(self, run_id: int) -> SimulationResult:
        """
        Exécute une simulation et retourne son SimulationResult.
        On intercepte l'état final pour extraire les métriques
        """
       
        initial_state = TontineInitializer.create_initial_state(
            self.tontine_config,
            self.participant_configs,
        )

        console  = self._silent_console()
        executor = TontineExecutor(
            tontine_config=self.tontine_config,
            participant_configs=self.participant_configs,
            console=console,
            initial_state=initial_state,
            output_dir=f"/tmp/mc_run_{run_id}", 
        )

    
        failure_month = None
        original_failed = executor.state.is_tontine_failed

        def patched_failed(config):
            nonlocal failure_month
            result = original_failed(config)
            return result

        executor.tracer_ligne = lambda recap, membres: None
        executor.run_simulation(num_months=self.num_months)
        state = executor.state
        failed = state.is_tontine_failed(self.tontine_config)

        active_count = sum(
            1 for p in state.active_participants.values()
            if p.status.value == "active"
        )

        return SimulationResult(
            run_id=run_id,
            failed=failed,
            failure_month=failure_month,
            treasury_final=state.treasury_balance,
            default_rate=state.default_rate,
            total_contributions=state.total_contributions_received,
            active_participants_final=active_count,
        )

    def run(self, verbose: bool = True) -> List[SimulationResult]:
        """
        Lance les N simulations et stocke les résultats.

        Paramètre
        ----------
        verbose : bool
         Si true, affiche une barre de progression dans le terminal.

        Returns
        -------
        List[SimulationResult] de longueur n_simulations.
        """
        self.results = []

        print(f"\n{'═'*55}")
        print(f"  Monte Carlo — {self.n_simulations} simulations × {self.num_months} mois")
        print(f"{'═'*55}")

        for i in range(self.n_simulations):
            result = self._run_one(i)
            self.results.append(result)

            if verbose and (i + 1) % 50 == 0:
                pct = (i + 1) / self.n_simulations * 100
                bar = "▮" * int(pct / 5) + "▥" * (20 - int(pct / 5))
                n_failed = sum(1 for r in self.results if r.failed)
                print(f"  [{bar}] {i+1:>4}/{self.n_simulations}  |  faillites so far: {n_failed}")

        print(f"\n  ✓ {self.n_simulations} simulations terminées.")
        return self.results


class MonteCarloAnalyzer:
    """
    Analyse statistique des résultats Monte Carlo.

    Calcule pour chaque métrique :
      - Moyenne, écart-type, min, max
      - Intervalles de confiance à 95%
      - Quantiles : P5, P25, médiane, P75, P95
      - Probabilité de faillite

    """

    def __init__(self, results: List[SimulationResult]):
        self.results = results
        self.N = len(results)


        self.treasury   = np.array([r.treasury_final      for r in results])
        self.def_rate   = np.array([r.default_rate         for r in results])
        self.contribs   = np.array([r.total_contributions  for r in results])
        self.failed_arr = np.array([r.failed               for r in results], dtype=float)

    def _ic95(self, arr: np.ndarray) -> tuple:
        """
        Intervalle de confiance à 95% sur la moyenne.

        Hypothèse : par le Théorème Central Limite, la moyenne
        empirique est approximativement normale pour N ≥ 30.
        Ici, N est à 500.

        Returns
        -------
        (lower, upper) : bornes de l'IC à 95%.
        """
        mean  = np.mean(arr)
        se    = np.std(arr, ddof=1) / np.sqrt(self.N) 
        return (mean - 1.96 * se, mean + 1.96 * se)

    def _stats(self, arr: np.ndarray, label: str) -> dict:
        """Calcule toutes les statistiques pour un array."""
        ic_low, ic_high = self._ic95(arr)
        return {
            "label":     label,
            "N":         self.N,
            "mean":      round(float(np.mean(arr)),   2),
            "std":       round(float(np.std(arr, ddof=1)), 2),
            "min":       round(float(np.min(arr)),    2),
            "P5":        round(float(np.percentile(arr,  5)), 2),
            "P25":       round(float(np.percentile(arr, 25)), 2),
            "median":    round(float(np.median(arr)),  2),
            "P75":       round(float(np.percentile(arr, 75)), 2),
            "P95":       round(float(np.percentile(arr, 95)), 2),
            "max":       round(float(np.max(arr)),    2),
            "ic95_low":  round(ic_low,  2),
            "ic95_high": round(ic_high, 2),
        }

    def bankruptcy_probability(self) -> float:
        """
        P(faillite) = nombre de runs en faillite / N.

        """
        return round(float(np.mean(self.failed_arr)), 4)

    def bankruptcy_ic95(self) -> tuple:
        p = self.bankruptcy_probability()
        se = np.sqrt(p * (1 - p) / self.N)
        return (round(max(0, p - 1.96 * se), 4), round(min(1, p + 1.96 * se), 4))

    def full_report(self) -> dict:
       
        return {
            "treasury":      self._stats(self.treasury,  "Trésorerie finale (€)"),
            "default_rate":  self._stats(self.def_rate,  "Taux de défaut"),
            "contributions": self._stats(self.contribs,  "Cotisations collectées (€)"),
            "bankruptcy": {
                "probability": self.bankruptcy_probability(),
                "ic95":        self.bankruptcy_ic95(),
                "n_failed":    int(np.sum(self.failed_arr)),
                "n_total":     self.N,
            },
        }

    def print_report(self):
        report = self.full_report()
        SEP  = "─" * 55
        SEP2 = "═" * 55

        print(f"\n{SEP2}")
        print("  RÉSULTATS MONTE CARLO")
        print(f"{SEP2}\n")

        bk = report["bankruptcy"]
        ic = bk["ic95"]
        print(f"{'PROBABILITÉ DE FAILLITE':}")
        print(f"  {bk['n_failed']} faillites sur {bk['n_total']} simulations")
        print(f"  P(faillite) = {bk['probability']:.2%}")
        print(f"  IC 95%      = [{ic[0]:.2%},  {ic[1]:.2%}]")
        print(f"\n  Lecture : si on relançait la tontine 100 fois avec ces\n"
              f"  paramètres, elle ferait faillite ~{bk['probability']*100:.0f} fois.\n")

        for key in ["treasury", "default_rate", "contributions"]:
            s = report[key]
            print(f"{SEP}")
            print(f"  {s['label'].upper()}")
            print(f"  Moyenne   = {s['mean']:>12,.2f}   ± {s['std']:,.2f} (écart-type)")
            print(f"  IC 95%    = [{s['ic95_low']:>10,.2f},  {s['ic95_high']:,.2f}]")
            print(f"  Min / Max = {s['min']:>10,.2f}  /  {s['max']:,.2f}")
            print(f"  Quantiles : P5={s['P5']:,.2f}  médiane={s['median']:,.2f}  P95={s['P95']:,.2f}")

            arr = self.treasury if key == "treasury" else \
                  self.def_rate  if key == "default_rate" else self.contribs
            _print_ascii_hist(arr, bins=10)

        print(f"\n{SEP2}")
        print("  LIEN AVEC MARKOV")
        print(f"{SEP2}")

        from markov_model import TontineMarkovAnalyzer
        with open("config_sample.json") as f:
            data = json.load(f)
        from tontine_config import IndividualParticipantConfig
        configs = [
            IndividualParticipantConfig(
                id=p["id"], name=p["name"],
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
        markov_contrib = analyzer.expected_total_contributions(data["tontine"]["monthly_contrib"])

        s = report["contributions"]
        print(f"\n  Cotisations espérées (Markov)    = {markov_contrib:>10,.2f} €")
        print(f"  Cotisations moyenne (Monte Carlo)= {s['mean']:>10,.2f} €")
        print(f"  Écart                            = {s['mean'] - markov_contrib:>+10,.2f} €")
        print(f"\n  Interprétation : Markov donne une borne analytique,")
        print(f"  Monte Carlo montre la distribution réelle autour de cette borne.")
        print(f"  Un écart positif = la simulation collecte plus que prévu par Markov")


    def plot_kde(self, save_dir: str = '.') -> None:
        """
        Génère deux graphiques KDE séparés :
          1. Distribution de la trésorerie finale sur N runs
          2. Distribution des cotisations collectées sur N runs

       
        Annotations sur chaque graphique
        ---------------------------------
        - Courbe KDE + remplissage
        - Ligne pleine    : moyenne µ
        - Zone grisée     : IC 95% sur µ
        - Ligne tiretée   : médiane
        - Lignes pointillées : P5 et P95 (quantiles extrêmes)
        - Ligne violette  : cotisations seul
        - Zone rouge      : zone de faillite si trésorerie < 0
        """
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from scipy.stats import gaussian_kde
        import os

        os.makedirs(save_dir, exist_ok=True)

        def _make_kde_plot(arr, title, xlabel, filename,
                           color_main, markov_value=None, markov_label=None):

            fig, ax = plt.subplots(figsize=(10, 5))
            fig.patch.set_facecolor("white")
            ax.set_facecolor("white")

            kde = gaussian_kde(arr)
            spread = arr.max() - arr.min()
            x = np.linspace(arr.min() - 0.1 * spread,
                            arr.max() + 0.1 * spread, 500)
            y = kde(x)

            ax.plot(x, y, color=color_main, linewidth=2.5, label="Densité KDE")
            ax.fill_between(x, y, alpha=0.12, color=color_main)

            mean_v  = np.mean(arr)
            std_v   = np.std(arr, ddof=1)
            median_v = np.median(arr)
            p5_v    = np.percentile(arr, 5)
            p95_v   = np.percentile(arr, 95)
            ic_lo   = mean_v - 1.96 * std_v / np.sqrt(len(arr))
            ic_hi   = mean_v + 1.96 * std_v / np.sqrt(len(arr))


            ax.axvspan(ic_lo, ic_hi, alpha=0.13, color="gray",
                       label=f"IC 95% moy. [{ic_lo:,.0f} ; {ic_hi:,.0f}]")

            ax.axvline(mean_v, color=color_main, linewidth=2.2, linestyle="-",
                       label=f"Moyenne  = {mean_v:,.0f}")

            ax.axvline(median_v, color="steelblue", linewidth=1.5,
                       linestyle="--", label=f"Médiane  = {median_v:,.0f}")

            ax.axvline(p5_v, color="#E67E22", linewidth=1.3, linestyle=":",
                       label=f"P5       = {p5_v:,.0f}")
            ax.axvline(p95_v, color="#27AE60", linewidth=1.3, linestyle=":",
                       label=f"P95      = {p95_v:,.0f}")

            if markov_value is not None:
                ax.axvline(markov_value, color="#8E44AD", linewidth=1.8,
                           linestyle="-.",
                           label=f"{markov_label} = {markov_value:,.0f}")

            if arr.min() < 0:
                x_left = x[0]
                ax.axvspan(x_left, 0, alpha=0.07, color="red",
                           label="Zone faillite (< 0)")
                ax.axvline(0, color="red", linewidth=0.9,
                           linestyle="-", alpha=0.5)
                
            ax.set_title(title, fontsize=13, fontweight="bold",
                         pad=14, color="#1F3864")
            ax.set_xlabel(xlabel, fontsize=11, color="#333333")
            ax.set_ylabel("Densité de probabilité", fontsize=11, color="#333333")
            ax.legend(fontsize=8.5, loc="upper right",
                      framealpha=0.9, edgecolor="#CCCCCC")
            ax.tick_params(axis="both", labelsize=9, colors="#444444")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#CCCCCC")
            ax.spines["bottom"].set_color("#CCCCCC")
            ax.grid(axis="y", color="#EEEEEE", linewidth=0.8)

            note = (f"N = {len(arr)} simulations  |  "
                    f"μ = {mean_v:,.0f}  |  σ = {std_v:,.0f}  |  "
                    f"P5 = {p5_v:,.0f}  |  P95 = {p95_v:,.0f}")
            fig.text(0.5, -0.02, note, ha="center", fontsize=8.5,
                     color="#666666", style="italic")

            plt.tight_layout()
            path = os.path.join(save_dir, filename)
            fig.savefig(path, dpi=150, bbox_inches="tight",
                        facecolor="white", edgecolor="none")
            plt.close(fig)
            print(f"  -> Sauvegarde : {path}")

        _make_kde_plot(
            arr         = self.treasury,
            title       = (f"Distribution de la trésorerie finale"
                           f" — Monte Carlo (N={self.N})"),
            xlabel      = "Trésorerie finale (€)",
            filename    = "kde_tresorerie.png",
            color_main  = "#2E75B6",
        )

        markov_val, markov_lbl = None, None
        try:
            from markov_model import TontineMarkovAnalyzer
            with open("config_sample.json") as _f:
                _data = json.load(_f)
            _cfgs = [
                IndividualParticipantConfig(
                    id=p["id"], name=p["name"],
                    default_probability=p["default_probability"],
                    loan_prob=p["loan_prob"],
                    loan_reemboursement_prob=p["loan_reemboursement_prob"],
                    exit_probability=p["exit_probability"],
                    max_consecutive_defaults=p.get("max_consecutive_defaults", 2),
                )
                for p in _data["participants"]
            ]
            _ma = TontineMarkovAnalyzer(_cfgs, horizon_months=36)
            _ma.analyze_all()
            markov_val = _ma.expected_total_contributions(
                _data["tontine"]["monthly_contrib"])
            markov_lbl = "Borne Markov"
        except Exception:
            pass

        _make_kde_plot(
            arr          = self.contribs,
            title        = (f"Distribution des cotisations collectées"
                            f" — Monte Carlo (N={self.N})"),
            xlabel       = "Cotisations collectées (€)",
            filename     = "kde_cotisations.png",
            color_main   = "#1D7A6B",
            markov_value = markov_val,
            markov_label = markov_lbl,
        )

        print("")
        print("  Lecture des graphiques :")
        print("  - Courbe KDE     : densité empirique sur N simulations")
        print("  - Zone grisée    : IC 95% sur la moyenne (précision)")
        print("  - Ligne tiretée  : médiane")
        print("  - Lignes ...     : P5 (scénario pessimiste) et P95 (optimiste)")
        print("  - Ligne violette : borne analytique Markov (cotisations)")
        print("  - Zone rouge     : runs en faillite (trésorerie < 0)")


def _print_ascii_hist(arr: np.ndarray, bins: int = 10):
   
    counts, edges = np.histogram(arr, bins=bins)
    max_count = max(counts)
    bar_max = 30

    print()
    for i, (c, edge) in enumerate(zip(counts, edges)):
        bar_len = int(c / max_count * bar_max) if max_count > 0 else 0
        bar = "█" * bar_len
        label = f"{edge:>10,.1f}"
        pct = c / len(arr) * 100
        print(f"  {label} │{bar:<{bar_max}} {pct:4.1f}%")
    print()


if __name__ == "__main__":

    
    with open("config_sample.json") as f:
        data = json.load(f)

    tontine_config, participant_configs = TontineInitializer.load_config("config_sample.json")

    engine = MonteCarloEngine(
        tontine_config=tontine_config,
        participant_configs=participant_configs,
        n_simulations=500,
        num_months=36,
    )
    results = engine.run(verbose=True)

    analyzer = MonteCarloAnalyzer(results)
    analyzer.print_report()
    analyzer.plot_kde(save_dir="results")