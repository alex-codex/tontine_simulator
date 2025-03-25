#!/usr/bin/env python3

import argparse
from rich.console import Console

from tontine_initializer import TontineInitializer
from tontine_executor import TontineExecutor

def main():
    """Point d'entrée principal pour la simulation de la tontine"""
    parser = argparse.ArgumentParser(description="Exécuter la simulation de la tontine")
    parser.add_argument("--config", type=str, default="config_sample.json",
                        help="Chemin d'accès au fichier de configuration JSON")
    parser.add_argument("--months", type=int, default=36,
                        help="Nombre de mois à simuler")
    parser.add_argument("--output", type=str, default="simulation_results",
                        help="Répertoire pour stocker les résultats de la simulation")
    
    args = parser.parse_args()
    
    console = Console(record=True)
    
    try:
        # Charger la configuration
        console.print("[cyan]Chargement de la configuration de la tontine...[/cyan]")
        tontine_config, participant_configs = TontineInitializer.load_config(args.config)
        
        # Créer l'état initial de la tontine
        console.print("[cyan]Création de l'état initial de la tontine...[/cyan]")
        initial_state = TontineInitializer.create_initial_state(tontine_config, participant_configs)
        
        # Démarrer la simulation
        console.print("[cyan]Démarrage de la simulation...[/cyan]")
        executor = TontineExecutor(
            tontine_config=tontine_config,
            participant_configs=participant_configs,
            initial_state=initial_state,
            output_dir=args.output
        )
        
        executor.run_simulation(num_months=args.months)
        
    except Exception as e:
        console.print(f"[bold red]Erreur : {str(e)}[/bold red]")
        raise e
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())