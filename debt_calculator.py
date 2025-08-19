import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


def main():
    # emily_loans = []
    # emily_loans.append(Loan(3500, 0.0505, 12))
    # emily_loans.append(Loan(2304.61, 0.0505, 0))  # 2278.08
    # emily_loans.append(Loan(4500, 0.0453, 12))
    # emily_loans.append(Loan(2180.33, 0.0453, 0))  # 2156.53
    # emily_loans.append(Loan(2978, 0.0275, 12))
    # emily_loans.append(Loan(4736.66, 0.0275, 0))  # 4703.98
    # emily_loans.append(Loan(1867, 0.0373, 12))
    # emily_loans.append(Loan(5995.70, 0.0373, 0))  # 5940.49
    # emily_loans.append(Loan(22368.89, 0.0528, 0))  # 22084.42
    # emily_loans.append(Loan(22643.28, 0.0705, 0))  # 22263.43
    # emily_loans.append(Loan(39243.71, 0.0754, 0))  # updated from 38555.59
    # emily_loans.append(Loan(4181.82, 0.0805, 0))  # updated from 17808.59

    # all_loans = AllLoans(emily_loans, 'Emily')

    csv_file = "debts/tristan_loans.csv"

    loan_list, all_loans = parse_csv(csv_file)
    monthly_payment = 3500

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlabel('Months')
    ax.set_ylabel('Balance ($)')
    
    ax.grid(True)
    # fig.tight_layout()

    interest_paid = all_loans.calculate_loans(24, monthly_payment)
    ax.set_title(f"{extract_name(csv_file)}'s Loans: ${monthly_payment}/Month Payment, \\${interest_paid} paid in interest")
    for i in range(len(loan_list)):
        loan_list[i].plot_loan_trajectory(ax)

    all_loans.plot_total_loan(ax)

    ax.legend()
    plt.show()


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
    return loans, all_loans

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
        ax.plot(self.month_archive, self.balance_archive, linewidth=2, label=f'${self.start_balance} at {self.interest}%')


# This is a list of all of the loans
class AllLoans:
    def __init__(self, all_loans, title):
        self.all_loans = all_loans
        self.title = title
        self.calc_total_balance()
        self.total_balance_archive = [self.total_balance]
        self.month_archive = [0]

    # order the loan list based on target loans
    def order_loans(self, current_month):
        ordered_list = []

        full_loans = []
        for i, loan in enumerate(self.all_loans):
            if loan.balance > 0:
                full_loans.append(loan)

        num_full_loans = len(full_loans)


        for j in range(num_full_loans):
            max_interest = 0
            max_loan = 0
            for i, loan in enumerate(full_loans):
                if (loan.interest > max_interest) and (current_month > loan.start):
                    max_interest = loan.interest
                    max_loan = i
            ordered_list.append(full_loans[max_loan])
            full_loans.pop(max_loan)
        
        return ordered_list

    def calc_total_balance(self):
        total_balance = 0
        for loan in self.all_loans:
            total_balance += loan.balance
        
        self.total_balance = total_balance

    def calculate_loans(self, months, monthly_payment):
        total_amount_paid = 0
        rollover_cash = 0
        for month in range(1, months+1):
            ordered_loans = self.order_loans(month)
            for i, loan in enumerate(ordered_loans):
                if i == 0:
                    rollover_cash, amount_paid = loan.calculate_month(monthly_payment)
                else:
                    rollover_cash, amount_paid = loan.calculate_month(rollover_cash)

                total_amount_paid += amount_paid

            self.calc_total_balance()
            self.total_balance_archive.append(self.total_balance)
            self.month_archive.append(month)
            if self.total_balance == 0:
                break

        print(f"For {self.title}, starting loan total = ${self.total_balance_archive[0]:.2f}. Paying ${monthly_payment} per month will")
        print(f"result in achieving a balance of ${self.total_balance:.2f} after {self.month_archive[-1]} months ({(self.month_archive[-1]/12):.1f} years).") 
        print(f"This resulted in paying a total of ${total_amount_paid:.2f}, which means we paid ${(total_amount_paid - (self.total_balance_archive[0] - self.total_balance)):.2f} in interest.\n")

        return round(total_amount_paid - (self.total_balance_archive[0] - self.total_balance), 2)

    def plot_total_loan(self, ax):
        ax.plot(self.month_archive, self.total_balance_archive, linewidth=2, label=f'Total Loan Balance ({self.title})')


if __name__ == "__main__":
    main()