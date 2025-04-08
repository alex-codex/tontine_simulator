import random
from datetime import datetime, timedelta
import time
import numpy as np
import uuid
from typing import Dict, List, Tuple, Optional
import json
import os
from pathlib import Path
import matplotlib.pyplot as plt

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.text import Text

from tontine_config import TontineConfig, IndividualParticipantConfig
from tontine_state import TontineState, ParticipantState, ParticipantStatus
from tontine_initializer import TontineInitializer

class TontineExecutor:
    """
    Execute tontine simulation, including all monthly operations and state transitions
    """
    
    def __init__(
        self, 
        tontine_config: TontineConfig, 
        participant_configs: List[IndividualParticipantConfig],
        console:Console,
        initial_state: Optional[TontineState] = None,
        output_dir: str = "simulation_results"
    ):
        self.tontine_config = tontine_config
        self.participant_configs = participant_configs
        self.state = initial_state or TontineInitializer.create_initial_state(tontine_config)
        self.console = console
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Liste des configurations de participants
        self.logger = TontineLogger(self.console, self.output_dir)
    
    def _advance_date(self, month_num :int):
        """Advance the simulation date by one month"""
        self.state.current_date += timedelta(days=30)  # Approximate month
        self.state.month_in_cycle = (month_num % 12) or 12


    def run_simulation(self, num_months: int = 60):
        """
        Run the tontine simulation for a specified number of months
        """
        self.logger.log_simulation_start(self.tontine_config, self.participant_configs)
        # Log the initial participants state at simulation start
        self.logger.log_initial_participants(self.state)
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("[cyan]Running simulation...", total=num_months)
            
            for month in range(num_months):
                # Initialize monthly accumulators
                self.monthly_defaults = []      # names of participants who default this month
                self.monthly_total_collected = 0.0
                self.monthly_debt_refunded = 0.0
                self.monthly_beneficiary = "None"
                                
                self._process_month() 
                

                if self.state.is_tontine_failed(self.tontine_config)== True :
                   self.logger.log_tontine_failure(self.state)
                   sortie = self.recuperer_donne_synthese(self.state.historical_participant)
                   self.tracer_ligne(sortie)
                   return

                # Log monthly summary with extra parameters
                self.logger.log_monthly_summary(
                    state=self.state,
                    month_num=month + 1,
                    beneficiary=self.monthly_beneficiary,
                    defaults=self.monthly_defaults,
                    total_collected=self.monthly_total_collected,
                    debt_refunded=self.monthly_debt_refunded,
                )

                
                
                if (month +1 ) % 12 == 0:
                    # Cycle end processing gathers exit and arrival info
                    exited_names = []
                    new_member_names = []
                    for participant_id, participant in list(self.state.active_participants.items()):
                        if participant.status != ParticipantStatus.ACTIVE:
                            continue
                        if random.random() < participant.config.exit_probability:
                            participant.status = ParticipantStatus.EXITED
                            exited_names.append(participant.config.name)
                            self.state.historical_participant[participant_id].exit_date = self.state.current_date
                            self.state.active_participants.pop(participant_id)
                            return_amount = 0
                            if participant.current_debt > 0:
                                return_amount = max(0, participant.total_contributions - participant.current_debt)
                            self.state.treasury_balance -= return_amount
                            self.monthly_debt_refunded += return_amount
                            self.state.cycle_exits += 1
                        else:
                          participant.exit_date = datetime(year = 2025, month=4 , day=1 ) + timedelta(days=30 *self.state.month_in_cycle * self.state.cycle_number)
                    for _ in range(self._calculate_new_arrivals()):
                        new_id = self._add_new_participant()
                        new_member_names.append(self.state.active_participants[new_id].config.name)
                        self.state.historical_participant[new_id]= self.state.active_participants[new_id]
                    
                    self.logger.log_cycle_summary(self.state,exited_names, new_member_names)

                    
                    # Reset cycle stats and log detailed participants table at cycle end
                    self.state.cycle_contributions = 0
                    self.state.cycle_defaults = 0
                    self.state.cycle_new_members = 0
                    self.state.cycle_exits = 0
                    self.state.cycle_number += 1
                    self.state.month_in_cycle = 1
                else:
                    self._advance_date(month + 1)

                progress.update(task, advance=1, description=f"[cyan]Month {month + 1}/{num_months}")
               
        if(self.state.is_tontine_failed(self.tontine_config) == False):
         self.logger.log_simulation_end(self.state)
         sortie = self.recuperer_donne_synthese(self.state.historical_participant)
         self.tracer_ligne(sortie)
    
    def _process_month(self):
        """Process all activities for a single month"""
        
        total_contribution = self._collect_contributions()
        
        self._process_monthly_distribution(total_contribution)
        
        self._process_loan_requests()
        
        
        self._process_loan_repayments()
        
        
        if self.state.is_cycle_end():
            self._process_end_of_cycle()
            
        
        self._advance_date(self.state.month_in_cycle + 1 )
    
    def _collect_contributions(self):
        """Collect monthly contributions from all participants and return total collected"""
        total_collected = 0.0
        # Reset defaults list for the month
        self.monthly_defaults = []
        
        for participant_id, participant in list(self.state.active_participants.items()):
            if participant.status != ParticipantStatus.ACTIVE:
                continue
                
            if random.random() < participant.config.default_probability:
                # Default : Le participant décide de ne pas payer!
                participant.consecutive_defaults += 1
                participant.missed_payments += 1
                
                # Ajout de la dette du participant
                interest_amount = participant.current_debt * self.tontine_config.monthly_interest_rate
                participant.current_debt += self.tontine_config.monthly_contrib + interest_amount
                
                # Update tontine state
                self.state.cycle_defaults += 1
                self.state.default_rate = (
                    self.state.cycle_defaults / 
                    (len(self.state.active_participants) * self.state.month_in_cycle)
                )
                self.monthly_defaults.append(participant.config.name)
            else:
                # Le par
                participant.total_contributions += self.tontine_config.monthly_contrib
                participant.consecutive_defaults = 0
                participant.last_payment_date = self.state.current_date
                
                # Update credit score (improve slightly)
                total_collected += self.tontine_config.monthly_contrib
                
                # Update participant eligibility for loans
                months_since_join = (self.state.current_date - participant.join_date).days // 30
                participant.is_eligible_for_loan = (
                    months_since_join >= self.tontine_config.min_membership_months and
                    len(participant.active_loans) < self.tontine_config.max_simultaneous_loans
                )
        
        # Update tontine state with total contributions
        self.state.total_contributions_received += total_collected
        self.state.cycle_contributions += total_collected
        self.monthly_total_collected = total_collected
        
        return total_collected
    
    def _process_monthly_distribution(self, total_contribution: float):
        """Process the monthly distribution where one participant receives a portion of contributions"""
        if total_contribution <= 0:
            return
        
        # Calculate amounts for different purposes
        emergency_amount = total_contribution * self.tontine_config.emergency_fund_percentage
        self.state.emergency_fund += emergency_amount
        
        distributable_amount = total_contribution - emergency_amount
        
        # Allocate configured percentage to one participant
        distribution_amount = distributable_amount * self.tontine_config.monthly_distribution_percentage
        treasury_amount = distributable_amount - distribution_amount
        
        # Add to treasury
        self.state.treasury_balance += treasury_amount
        
        # Select next participant for distribution
        active_participants = [p for p in self.state.active_participants.values() 
                              if p.status == ParticipantStatus.ACTIVE]
        
        if active_participants:
            # Sort by participant ID for consistent ordering
            sorted_participants = sorted(active_participants, key=lambda p: p.id)
            
            # Find next participant who hasn't received payout recently
            next_participant = min(sorted_participants, 
                                  key=lambda p: getattr(p, 'monthly_distributions_received', 0))
            
            if not hasattr(next_participant, 'monthly_distributions_received'):
                next_participant.monthly_distributions_received = 0
                
            # Update participant state
            next_participant.monthly_distributions_received += distribution_amount
            
            # Update distribution history
            if not hasattr(self.state, 'monthly_distribution_history'):
                self.state.monthly_distribution_history = []
            self.state.monthly_distribution_history.append(next_participant.id)
            
            # Record beneficiary name for monthly summary
            self.monthly_beneficiary = next_participant.config.name
            
            # Log the distribution
            self.logger.log_monthly_distribution(
                participant=next_participant,
                amount=distribution_amount,
                month=self.state.month_in_cycle
            )
        else:
            # If no eligible participant, add to treasury
            self.state.treasury_balance += distribution_amount
    
    def _process_loan_requests(self):
        """Process loan requests from eligible participants"""
        for participant_id, participant in self.state.active_participants.items():
            if (
                participant.status == ParticipantStatus.ACTIVE and
                participant.is_eligible_for_loan and
                random.random() < participant.config.loan_prob  # Use participant-specific probability
            ):
                max_possible_loan = min(
                    self.state.treasury_balance * 0.5,
                    self.tontine_config.max_loan_amount)
                
                
                if max_possible_loan <= 0:
                    continue
                    
                loan_amount = random.uniform(0.5 * max_possible_loan, max_possible_loan)
                
                # Issue the loan
                participant.active_loans.append(loan_amount)
                participant.current_debt += loan_amount
                participant.total_borrowed += loan_amount
                
                # Update tontine state
                self.state.treasury_balance -= loan_amount
                self.state.total_loans_outstanding += loan_amount
    
    def _process_loan_repayments(self):
        """Process loan repayments"""
        for participant_id, participant in self.state.active_participants.items():
            if (
                participant.status == ParticipantStatus.ACTIVE and
                participant.current_debt > 0 and
                random.random() < participant.config.loan_reemboursement_prob
            ):
                # Calculate interest due
                interest_amount = participant.current_debt * self.tontine_config.monthly_interest_rate
                
                # Determine repayment amount (principal + interest)
                repayment_amount = interest_amount
                
                # Optionally repay some principal
                if random.random() > 0.5:  # 50% chance to repay some principal
                    principal_repayment = random.uniform(
                        self.tontine_config.monthly_contrib, 
                        participant.current_debt * 0.2  # Up to 20% of current debt
                    )
                    repayment_amount += principal_repayment
                
                # Apply the repayment
                participant.current_debt -= (repayment_amount - interest_amount)  # Subtract principal
                participant.total_repaid += repayment_amount
                
                # Remove fully repaid loans
                if participant.current_debt <= 0:
                    participant.active_loans = []
                    participant.current_debt = 0
                    
                # Update tontine state
                self.state.treasury_balance += repayment_amount
                self.state.total_loans_outstanding -= (repayment_amount - interest_amount)
                self.state.total_interest_earned += interest_amount
                
                # Update loan recovery metrics
                if self.state.total_loans_outstanding > 0:
                    self.state.loan_recovery_rate = (
                        self.state.total_interest_earned / 
                        self.state.total_loans_outstanding
                    )
    
    def _process_end_of_cycle(self):
        
        pass
    
    def _calculate_new_arrivals(self) -> int:
        """Calculate number of new participants arriving at end of cycle"""
        base_arrivals = round(len(self.state.active_participants) * self.tontine_config.arrival_probability)
        
        # Add some randomness
        variation = random.randint(-2, 2)
        new_arrivals = max(0, base_arrivals + variation)
        
        return new_arrivals
    
    def _add_new_participant(self):
        """Add a new participant to the tontine"""
        participant_id = str(uuid.uuid4())
        start = datetime.now().replace(day=1 ,hour=0 , minute=0, second=0, microsecond=0)

        # config the config of a random participant
        ref_config = random.choice(self.participant_configs).clone()
        ref_config.name= f"Participant {self.state.total_participants_history+1}"

        # Create a new participant
        participant = ParticipantState(
            id=participant_id,
            config = ref_config,
            join_date=self.state.current_date,
            exit_date = start + timedelta(days= 30 *self.state.cycle_number * self.state.month_in_cycle ) ,
            status=ParticipantStatus.ACTIVE,
            total_contributions=0.0,
            current_debt=0.0,
            active_loans=[],
            missed_payments=0,
            consecutive_defaults=0,
            last_payment_date=self.state.current_date,
            total_borrowed=0.0,
            total_repaid=0.0,
            is_eligible_for_loan=False,  # Not eligible at start
        )
        
        # Add to active participants
        self.state.active_participants[participant_id] = participant
        
        # Update tontine state
        self.state.total_participants_history += 1
        self.state.cycle_new_members += 1
        
        return participant_id
    
    def recuperer_donne_synthese(self, donnee: dict[str, ParticipantState]) -> list[list[float]]:
        liste_trait = []
        for ID in donnee:
            prob_rembourser = donnee[ID].config.loan_reemboursement_prob
            date_entree = donnee[ID].join_date
            date_sortie = donnee[ID].exit_date or datetime.now()
            time_entree = time.mktime(date_entree.timetuple())
            time_sortie = time.mktime(date_sortie.timetuple())
            liste_trait.append([time_entree, time_sortie, prob_rembourser])

        return liste_trait

    def tracer_ligne(self,liste_de_trait: list[list[float]]) -> None:
          """
        Args:
        liste_de_trait: une liste de liste contenant (date entree , date de sortie et probabilite de remboursement)]
          """
          min = 0.4
          for i, trait in enumerate(liste_de_trait):
              x_debut =trait[0]
              x_fin = trait[1]
              couleur_condition = trait[2]
              y = i
              if couleur_condition < min:
                couleur = 'red'
              else:
                couleur = 'green'

              plt.hlines(y=1 + 0.2 * (y + 1), xmin=x_debut, xmax=x_fin, color=couleur)
    
          plt.ylim(0, len(liste_de_trait) - 1)
          # plt.xticks( [0, 180, 360,5400, 7200, 9000, 10080], ['0', '25', 'dec', '26', 'Decembre', 'Juin-2027', 'Decembre'])
          plt.show()  

class TontineLogger:
    """
    Handle logging and state display for tontine simulation
    """
    
    def __init__(self, console: Console, output_dir: Path):
        self.console = console
        self.output_dir = output_dir
    
    def log_simulation_start(self, tontine_config: TontineConfig, participants_confg:List[IndividualParticipantConfig]):
        """Log the start of a simulation with configuration details"""
        self.console.clear()
        self.console.print()
        self.console.print("[bold cyan]╔═════════════════════════════════════════╗")
        self.console.print("[bold cyan]║       TONTINE SIMULATION STARTED        ║")
        self.console.print("[bold cyan]╚═════════════════════════════════════════╝")
        self.console.print()
        
        # Display tontine configuration
        table = Table(title="Tontine Configuration")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        for field in tontine_config.__dataclass_fields__:
            value = getattr(tontine_config, field)
            table.add_row(field, str(value))
            
        self.console.print(table)
        self.console.print()
        
        # Display participant configuration
        table = Table(title="Participant Configuration")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        #for field in participant_config.__dataclass_fields__:
         #   value = getattr(participant_config, field)
          #  table.add_row(field, str(value))
            
        self.console.print(table)
        self.console.print()
    
    def log_monthly_state(self, state: TontineState, month_num: int):
        """Log the state of the tontine after each month"""
        self.console.clear()
        self.console.print()
        
        header = f"[bold white on blue] TONTINE STATE - MONTH {month_num} (CYCLE {state.cycle_number}, MONTH {state.month_in_cycle}) [/]"
        self.console.print("ici ca marche")
        self.console.print(Panel(header, expand=False))
        self.console.print()
        
        # Display financial summary
        financial_text = Text()
        financial_text.append("Treasury Balance: ", style="white")
        financial_text.append(f"${state.treasury_balance:.2f}", style="green" if state.treasury_balance > 0 else "red")
        financial_text.append("\nEmergency Fund: ", style="white")
        financial_text.append(f"${state.emergency_fund:.2f}", style="green")
        financial_text.append("\nOutstanding Loans: ", style="white")
        financial_text.append(f"${state.total_loans_outstanding:.2f}", style="yellow")
        financial_text.append("\nTotal Interest Earned: ", style="white")
        financial_text.append(f"${state.total_interest_earned:.2f}", style="green")
        
        self.console.print(Panel(financial_text, title="Financial Summary", border_style="green"))
        
        # Display risk metrics
        risk_text = Text()
        risk_text.append("Default Rate: ", style="white")
        risk_text.append(f"{state.default_rate:.2%}", 
                         style="green" if state.default_rate < 0.1 else "yellow" if state.default_rate < 0.2 else "red")
        risk_text.append("\nLoan Recovery Rate: ", style="white")
        risk_text.append(f"{state.loan_recovery_rate:.2%}", 
                         style="green" if state.loan_recovery_rate > 0.9 else "yellow" if state.loan_recovery_rate > 0.7 else "red")
        
        self.console.print(Panel(risk_text, title="Risk Metrics", border_style="yellow"))
        
        # Display participant summary
        active_count = sum(1 for p in state.active_participants.values() if p.status == ParticipantStatus.ACTIVE)
        defaulted_count = sum(1 for p in state.active_participants.values() if p.status == ParticipantStatus.DEFAULTED)
        exited_count = sum(1 for p in state.active_participants.values() if p.status == ParticipantStatus.EXITED)
        
        participant_text = Text()
        participant_text.append("Active Participants: ", style="white")
        participant_text.append(f"{active_count}", style="green")
        participant_text.append("\nDefaulted Participants: ", style="white")
        participant_text.append(f"{defaulted_count}", style="red")
        participant_text.append("\nExited Participants: ", style="white")
        participant_text.append(f"{exited_count}", style="yellow")
        participant_text.append("\nTotal Historical Participants: ", style="white")
        participant_text.append(f"{state.total_participants_history}", style="blue")
        
        self.console.print(Panel(participant_text, title="Participant Summary", border_style="blue"))
        
        # Display cycle statistics
        cycle_text = Text()
        cycle_text.append("Cycle Contributions: ", style="white")
        cycle_text.append(f"${state.cycle_contributions:.2f}", style="green")
        cycle_text.append("\nCycle Defaults: ", style="white")
        cycle_text.append(f"{state.cycle_defaults}", style="red")
        cycle_text.append("\nNew Members This Cycle: ", style="white")
        cycle_text.append(f"{state.cycle_new_members}", style="green")
        cycle_text.append("\nExits This Cycle: ", style="white")
        cycle_text.append(f"{state.cycle_exits}", style="yellow")
        
        self.console.print(Panel(cycle_text, title="Cycle Statistics", border_style="magenta"))
        
        # Display detailed participant states - NEW SECTION
        self._log_detailed_participant_states(state)
        
        self.console.print()
    
    def _log_detailed_participant_states(self, state: TontineState):
        """Log detailed information about each participant's current state"""
        self.console.print("[bold blue]=== DETAILED PARTICIPANT STATES ===[/bold blue]")
        
        # Create a detailed table for active participants
        active_table = Table(
            title="Active Participants",
            show_lines=True,
            expand=True
        )
        
        # Add more detailed columns
        active_table.add_column("ID", style="cyan")
        active_table.add_column("Name", style="white")
        active_table.add_column("Status", style="green")
        active_table.add_column("Contributions", style="green")
        active_table.add_column("Distributions", style="blue")
        active_table.add_column("Current Debt", style="red")
        active_table.add_column("Credit Score", style="yellow")
        active_table.add_column("Default Risk", style="red")
        active_table.add_column("Loan Prob", style="blue")
        active_table.add_column("Exit Risk", style="yellow")
        active_table.add_column("Active Loans", style="blue")
        active_table.add_column("Payment History", style="cyan")
        
        # Sort participants by ID
        sorted_participants = sorted(
            state.active_participants.values(),
            key=lambda p: p.id
        )
        
        for participant in sorted_participants:
            if participant.status == ParticipantStatus.ACTIVE:
                # Get participant config for probabilities
                config = participant.config
                
                # Format loan information
                loans_str = ", ".join([f"${loan:.2f}" for loan in participant.active_loans])
                if not loans_str:
                    loans_str = "None"
                
                # Calculate payment history
                days_since_payment = (state.current_date - participant.last_payment_date).days
                payment_status = (
                    f"Regular ({days_since_payment}d)" if days_since_payment < 30
                    else f"[yellow]Late ({days_since_payment}d)[/yellow]" if days_since_payment < 60
                    else f"[red]Very Late ({days_since_payment}d)[/red]"
                )
                
                active_table.add_row(
                    participant.id[:8],
                    participant.config.name,
                    "ACTIVE",
                    f"${participant.total_contributions:.2f}",
                    f"${getattr(participant, 'monthly_distributions_received', 0):.2f}",
                    f"${participant.current_debt:.2f}",
                    f"{config.default_probability:.1%}",
                    f"{config.loan_prob:.1%}",
                    f"{config.exit_probability:.1%}",
                    loans_str,
                    payment_status
                )
        
        self.console.print(active_table)
        self.console.print()
    
    def log_tontine_failure(self, state: TontineState):
        """Log when a tontine fails"""
        self.console.print()
        self.console.print("[bold red]╔═════════════════════════════════════════╗")
        self.console.print("[bold red]║          TONTINE HAS FAILED!            ║")
        self.console.print("[bold red]╚═════════════════════════════════════════╝")
        self.console.print()
        
        active_count = sum(1 for p in state.active_participants.values() if p.status == ParticipantStatus.ACTIVE)
        self.console.print(f"[red]Active participants: {active_count} - below minimum threshold")
        self.console.print(f"[red]Treasury balance: ${state.treasury_balance:.2f}")
        self.console.print(f"[red]Emergency fund: ${state.emergency_fund:.2f}")
        self.console.print()

         # save ending state
        self.save_state_to_json(state, "final")
    
    def log_simulation_end(self, final_state: TontineState):
        """Log the end of a simulation with final statistics"""
        self.console.print()
        self.console.print("[bold green]╔═════════════════════════════════════════╗")
        self.console.print("[bold green]║       TONTINE SIMULATION COMPLETE       ║")
        self.console.print("[bold green]╚═════════════════════════════════════════╝")
        self.console.print()
        
        # Save final state
        self.save_state_to_json(final_state, "final")
        
        # Display final statistics
        table = Table(title="Final Tontine Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Final Treasury Balance", f"${final_state.treasury_balance:.2f}")
        table.add_row("Emergency Fund", f"${final_state.emergency_fund:.2f}")
        table.add_row("Total Contributions", f"${final_state.total_contributions_received:.2f}")
        table.add_row("Total Interest Earned", f"${final_state.total_interest_earned:.2f}")
        table.add_row("Default Rate", f"{final_state.default_rate:.2%}")
        table.add_row("Loan Recovery Rate", f"{final_state.loan_recovery_rate:.2%}")
        
        active_count = sum(1 for p in final_state.active_participants.values() if p.status == ParticipantStatus.ACTIVE)
        table.add_row("Final Active Participants", str(active_count))
        table.add_row("Total Historical Participants", str(final_state.total_participants_history))
        
        self.console.print(table)
        self.console.print()
        
        self.console.print("[green]Full simulation data has been saved to the output directory.")
        self.console.print()

        self.console.save_html(self.output_dir/"simulation.html")
    
    def save_state_to_json(self, state: TontineState, month_or_label):
        """Save the current state to a JSON file"""
        filename = f"tontine_state_{month_or_label}.json"
        filepath = self.output_dir / filename 
        
        # Convert state to serializable dict
        state_dict = self._serialize_state(state)
        
        with open(filepath, 'w') as f:
            json.dump(state_dict, f, indent=2, default=str)
    
    def _serialize_state(self, state: TontineState) -> dict:
        """Convert TontineState to a serializable dictionary"""
        # Convert participants
        participants_dict = {}
        for pid, participant in state.active_participants.items():
            participants_dict[pid] = {
                "id": participant.id,
                "join_date": participant.join_date.isoformat(),
                "exit_date":participant.exit_date ,
                "status": participant.status.value,
                "total_contributions": participant.total_contributions,
                "current_debt": participant.current_debt,
                "active_loans": participant.active_loans,
                "missed_payments": participant.missed_payments,
                "consecutive_defaults": participant.consecutive_defaults,
                "last_payment_date": participant.last_payment_date.isoformat(),
                "total_borrowed": participant.total_borrowed,
                "total_repaid": participant.total_repaid,
                "is_eligible_for_loan": participant.is_eligible_for_loan,
            }
        
        # Convert state
        state_dict = {
            "current_date": state.current_date.isoformat(),
            "cycle_number": state.cycle_number,
            "month_in_cycle": state.month_in_cycle,
            "active_participants": participants_dict,
            "total_participants_history": state.total_participants_history,
            "treasury_balance": state.treasury_balance,
            "emergency_fund": state.emergency_fund,
            "total_loans_outstanding": state.total_loans_outstanding,
            "total_contributions_received": state.total_contributions_received,
            "total_interest_earned": state.total_interest_earned,
            "default_rate": state.default_rate,
            "loan_recovery_rate": state.loan_recovery_rate,
            "cycle_contributions": state.cycle_contributions,
            "cycle_defaults": state.cycle_defaults,
            "cycle_new_members": state.cycle_new_members,
            "cycle_exits": state.cycle_exits
        }
        
        return state_dict 
    
   # def save_participant_state_to_json(self, state: ParticipantState):
    

    def log_monthly_distribution(self, participant: ParticipantState, amount: float, month: int):
        """Log when a participant receives a monthly distribution"""
        self.console.print(f"[bold green]Monthly Distribution - Month {month}[/bold green]")
        self.console.print(f"Participant {participant.config.name} ({participant.id[:8]}) received ${amount:.2f}")
        self.console.print(f"Total received to date: ${participant.monthly_distributions_received:.2f}")
        self.console.print()

    def log_initial_participants(self, state: TontineState):
        self.console.print("[bold blue]=== INITIAL PARTICIPANTS STATE ===[/bold blue]")
        self._log_detailed_participant_states(state)
    
    
    def log_cycle_end_participants(self, state: TontineState):
        self.console.print("[bold blue]=== CYCLE END PARTICIPANTS STATE ===[/bold blue]")
        self._log_detailed_participant_states(state)
    
    def log_monthly_summary(self, state: TontineState, month_num: int, beneficiary: str,
                            defaults: list, total_collected: float, debt_refunded: float):
        """Log a monthly summary with financial summary, risk metrics, participant summary, cycle statistics,
         and extra monthly info (beneficiary, defaults, totals)."""
        self.console.clear()
        header = f"[bold white on blue] TONTINE STATE - MONTH {month_num} (CYCLE {state.cycle_number}, MONTH {state.month_in_cycle}) [/]"
        self.console.print(Panel(header, expand=False))
        self.console.print()
     
        extra_text = Text()
        extra_text.append("Beneficiary: ", style="white")
        extra_text.append(f"{beneficiary}\n", style="green")
        extra_text.append("Defaults: ", style="white")
        if defaults:
            extra_text.append(", ".join(defaults) + "\n", style="red")
        else:
            extra_text.append("None\n", style="green")
        extra_text.append("Total Collected: ", style="white")
        extra_text.append(f"${total_collected:.2f}\n", style="green")
        extra_text.append("Total Debt Refunded: ", style="white")
        extra_text.append(f"${debt_refunded:.2f}", style="yellow")
        self.console.print(Panel(extra_text, title="Monthly Summary", border_style="magenta"))
        self.console.print()
    
    def log_cycle_summary(self, state: TontineState,  exited_names: list, new_member_names: list):
        """At the end of a cycle, log exit and arrival info along with detailed participant states."""
        self.console.print("[bold blue]=== CYCLE SUMMARY ===[/bold blue]")
        if exited_names:
            self.console.print(f"[bold red]Exited Participants:[/bold red] {', '.join(exited_names)}")
        else:
            self.console.print("[bold red]No participants exited this cycle.[/bold red]")
        if new_member_names:
            self.console.print(f"[bold blue]New Members Arrived:[/bold blue] {', '.join(new_member_names)}")
        else:
            self.console.print("[bold blue]No new members this cycle.[/bold blue]")
        
        #Total contribution
        self.console.print('"')

        
        self.log_cycle_end_participants(state=state)