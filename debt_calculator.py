import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import pandas as pd


def main():
    csv_file = "debts/emily_loans.csv"

    all_loans = parse_csv(csv_file)
    monthly_payment = 3800

    all_loans.calculate_loans(1000, monthly_payment, showplots="individual balances")
    # all_loans.calculate_breakpoint(ramsay=False, step=100)


def parse_csv(csv):
    df = pd.read_csv(csv)
    loans = []
    for _, row in df.iterrows():
        loan = Loan(
            balance=row["Balance"],
            interest=row["Interest Rate"],
            start=row["Start Month"]
        )
        loans.append(loan)

    all_loans = AllLoans(loans, extract_name(csv))
    return all_loans

def extract_name(s):
    try:
        split = s.split("/", 1)[1].split("_", 1)[0]
        return split[0].upper() + split[1:]
    except IndexError:
        print("Warning: Could not decipher name!")
        return s

class Loan:
    def __init__(self, balance, interest, start):
        '''
        balance (float): starting balance on loan
        interest (float): interest rate of loan (in decimal form)
        start (int): how many months from now until they start accruing interest (0 if they are now)
        '''
        self.start_balance = balance
        self.balance = balance
        self.interest = interest
        self.start = start
        self.balance_archive = [balance]
        self.month_archive = [0]

    # returns if we paid more than we needed
    def calculate_month(self, payment):
        current_month = self.month_archive[-1] + 1

        # check if we're at the start month yet
        if current_month < self.start:
            newbalance = self.balance - payment
        else:
            newbalance = self.balance * np.exp(self.interest * (1 / 12)) - payment

        if newbalance < 0:
            self.balance = 0
            amount_paid = payment + newbalance

            self.balance_archive.append(0)
            self.month_archive.append(current_month)

            return -newbalance, amount_paid

        else:
            self.balance = newbalance
            amount_paid = payment

            self.balance_archive.append(newbalance)
            self.month_archive.append(current_month)
            return 0, amount_paid

    def plot_loan_trajectory(self, ax):
        ax.plot(self.month_archive, self.balance_archive, linewidth=1.5, label=f'${self.start_balance:,} at {self.interest*100:.2f}%')


# This is a list of all of the loans
class AllLoans:
    def __init__(self, all_loans, title):
        self.all_loans = all_loans
        self.title = title
        self.total_balance = self.calc_total_balance()
        self.total_balance_archive = [self.total_balance]
        self.month_archive = [0]
        self.total_amount_paid = 0

    def order_loans(self, current_month, ramsay=False):
        """
        Orders loans for repayment.

        Args:
            current_month (int): Current month of simulation.
            pay_smallest_first (bool): 
                - True: Pay loans from smallest balance to largest (snowball method).
                - False: Pay loans from highest interest to lowest, but only include loans 
                that are currently accruing. Non-accruing loans are appended to the end.

        Returns:
            List[Loan]: Ordered list of loans to target this month.
        """
        # get all loans with balance remaining
        active_loans = [loan for loan in self.all_loans if loan.balance > 0]

        if ramsay:
            # include all active loans regardless of start time
            ordered_list = sorted(active_loans, key=lambda loan: loan.balance)
        else:
            # interest-rate ordering (accruing first, non-accruing later)
            accruing_loans = [loan for loan in active_loans if current_month > loan.start]
            non_accruing_loans = [loan for loan in active_loans if current_month <= loan.start]

            # Sort accruing loans by descending interest rate
            ordered_list = sorted(accruing_loans, key=lambda loan: loan.interest, reverse=True)

            # Append non-accruing loans at the end
            ordered_list.extend(non_accruing_loans)

        return ordered_list

    def calc_total_balance(self):
        total_balance = 0
        for loan in self.all_loans:
            total_balance += loan.balance
        
        # self.total_balance = total_balance
        return total_balance

    def calculate_breakpoint(self, ramsay, P_max=20000, step=1):
        """
        Uses binary search to find the smallest P where:
            I(P) - I(P + step) < step

        step = resolution of the search (like ΔP)
        """
        def I(P):
            loans = [Loan(l.balance, l.interest, l.start) for l in self.all_loans]
            return float(self.calc_hypothetical_loan(loans, P, ramsay=ramsay))
        # define the monotone predicate
        def good(P):
            """True if adding 'step' dollars no longer saves at least 'step' dollars."""
            interest_P      = I(P)
            interest_Pstep  = I(P + step)
            M = interest_P - interest_Pstep
            return M < step
        # binary search on integer grid
        lo, hi = 0, P_max
        while lo < hi:
            mid = (lo + hi) // 2

            if good(mid):
                hi = mid
            else:
                lo = mid + 1
        # 'lo' is the first P that satisfies the condition
        return lo

    @staticmethod
    def calc_hypothetical_loan(ordered_loans, monthly_payment, ramsay, max_months=1000):
        def total_bal(loans):
            return sum(float(loan.balance) for loan in loans)
        
        original_balance = total_bal(ordered_loans)
        total_paid = 0.0

        for month in range(1, max_months + 1):
            active = [ln for ln in ordered_loans if ln.balance > 0.0]
            if not active:
                break

            # Choose payoff order for this month
            if ramsay:
                # smallest balance first
                pay_order = sorted(active, key=lambda ln: ln.balance)
            else:
                # interest accruing first by highest rate, then non accruing
                accruing = [ln for ln in active if month > ln.start]
                non_accruing = [ln for ln in active if month <= ln.start]
                pay_order = sorted(accruing, key=lambda ln: ln.interest, reverse=True) + non_accruing

            # make payments this month in chosen order
            rollover = float(monthly_payment)
            for i, loan in enumerate(pay_order):
                rollover, amount_paid = loan.calculate_month(rollover)
                total_paid += float(amount_paid)
                if rollover <= 0.0:
                    # no more cash to deploy this month
                    # but keep looping if your loan.calculate_month can return negative rollover by design
                    rollover = 0.0

            if total_bal(ordered_loans) <= 0.0:
                break

        principal_reduction = original_balance - total_bal(ordered_loans)
        total_interest_paid = round(total_paid - principal_reduction, 2)
        return total_interest_paid

    def calculate_loans(self, months, monthly_payment, showplots="None", ramsay=False, print_balances=False):
        total_amount_paid = 0
        rollover_cash = 0
        for month in range(1, months+1):
            ordered_loans = self.order_loans(month, ramsay=ramsay)
            for i, loan in enumerate(ordered_loans):
                if i == 0:
                    rollover_cash, amount_paid = loan.calculate_month(monthly_payment)
                else:
                    rollover_cash, amount_paid = loan.calculate_month(rollover_cash)

                total_amount_paid += amount_paid

            self.total_balance = self.calc_total_balance()
            self.total_balance_archive.append(self.total_balance)
            self.month_archive.append(month)
            if self.total_balance == 0:
                break

        self.total_interest_paid = round(total_amount_paid - (self.total_balance_archive[0] - self.total_balance), 2)

        if ramsay:
            print(f"{self.title}'s starting loan total: ${self.total_balance_archive[0]:,.2f}. These numbers are using the Ramsay debt-snowball method.")
        else:
            print(f"{self.title}'s starting loan total: ${self.total_balance_archive[0]:,.2f}. These numbers are assuming we pay the highest interest loan first.")
        print(f"Paying ${monthly_payment} per month will result in achieving a balance of ${self.total_balance:,.2f} after {self.month_archive[-1]} months ({np.trunc(self.month_archive[-1]/12):.0f}y {(self.month_archive[-1]%12):.0f}m).") 
        print(f"This resulted in paying a total of ${total_amount_paid:,.2f}, which means we paid ${self.total_interest_paid:,.2f} in interest.\n")

        self.total_amount_paid = total_amount_paid

        if print_balances:
            print("\nIndividual loan balances:")
            for i, loan in enumerate(self.all_loans):
                print(f"Loan {i+1}: ${loan.balance:.2f} at {loan.interest*100:.2f}%")

        if showplots.lower() == "balances":
            fig, ax = plt.subplots(figsize=(10, 6))
            self.make_balance_plot(ax, monthly_payment)
            self.plot_all_loans(ax)
            self.plot_total_loan(ax)
            ax.legend()
            plt.show()
        elif showplots.lower() == "total balance":
            fig, ax = plt.subplots(figsize=(10, 6))
            self.make_balance_plot(ax, monthly_payment)
            self.plot_total_loan(ax)
            ax.legend()
            plt.show()
        elif showplots.lower() == "individual balances":
            fig, ax = plt.subplots(figsize=(10, 6))
            self.make_balance_plot(ax, monthly_payment)
            self.plot_all_loans(ax)
            ax.legend()
            plt.show()
        elif showplots.lower() == "pie":
            fig, ax = plt.subplots(figsize=(6, 6))
            self.plot_piechart(ax)
            plt.show()
        elif showplots.lower() == "all":
            fig, (ax_b, ax_p) = plt.subplots(
                1, 2,
                figsize=(14, 6),
                gridspec_kw={'width_ratios': [3, 1]}  # ax_b 3x wider than ax_p
            )
            self.make_balance_plot(ax_b, monthly_payment)
            self.plot_all_loans(ax_b)
            self.plot_total_loan(ax_b)
            self.plot_piechart(ax_p)
            ax_b.legend()
            fig.tight_layout()
            plt.show()
        else:
            if showplots.lower() != "none":
                print(f"Warning: Did not recognize '{showplots}' as a valid input. Valid inputs are:")
                print(f"'balances', 'individual balances', 'total balance', 'pie', or 'all'.")
                print(f"Defaulting to no plots...")
    
    def make_balance_plot(self, ax, monthly_payment):
        ax.set_xlabel('Months', fontsize=12)
        ax.set_ylabel('Balance ($)', fontsize=12)
        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        ax.grid(True)
        ax.set_title(f"{self.title}'s Loans: ${monthly_payment:,}/Month Payment, \\${self.total_interest_paid:,.2f} paid in interest", fontsize=14)
    
    def plot_all_loans(self, ax):
        for i in range(len(self.all_loans)):
            self.all_loans[i].plot_loan_trajectory(ax)

    def plot_total_loan(self, ax):
        ax.plot(self.month_archive, self.total_balance_archive, linewidth=3, label=f'Total Loan Balance')

    def plot_piechart(self, ax):
        # Pie chart of interest vs principal
        wedges, texts, autotexts = ax.pie(
            [self.total_balance_archive[0], self.total_interest_paid],
            labels=[f'Principal:\n${self.total_balance_archive[0]:,.2f}', f'Interest:\n${self.total_interest_paid:,.2f}'],
            colors=["#33b43a", '#d92b25'],
            autopct=lambda p: f'{p:.2f}%',
            startangle=90,
            wedgeprops={'width': 0.5, 'edgecolor': 'black', 'linewidth': 1},
            explode = (0, 0.05),
            pctdistance=0.25
        )

        # Set label font size (outside the pie)
        for text in texts:
            text.set_fontsize(12)

        # Set number font size (inside the pie)
        for autotext in autotexts:
            autotext.set_fontsize(10)

        # Set title font size
        ax.set_title(f"{self.title}'s Payment Breakdown:\n ${(self.total_balance_archive[0] + self.total_interest_paid):,.2f} paid total", fontsize=14)


if __name__ == "__main__":
    main()