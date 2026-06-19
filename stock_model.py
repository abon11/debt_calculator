"""
Check Joplin notes for all of the math behind this, including Itô's Lemma usage.
"""
import numpy as np
import matplotlib.pyplot as plt

def main():
    # prices = simulate_gbm_path(100, 0.1, 0.1, T)
    # plot_trajectory(prices, T)
    S0 = 1000
    T = 10
    num_sims = 1000
    regimes = {
        "bull": {"mu": 0.12, "sigma": 0.14},
        "bear": {"mu": -0.10, "sigma": 0.28},
    }
    transition_matrix = {
        "bull": {"bull": 0.98, "bear": 0.02},
        "bear": {"bull": 0.05, "bear": 0.95},
    }

    inv = Investment(S0, regimes, transition_matrix)

    prices, money_invested, regime_history = inv.simulate_gbm_path(T, 100)
    plot_trajectory(prices, T, money_invested, regime_history)
    plt.show()


    # all_prices, investments = inv.run_gbm_monte_carlo(S0, mu, sigma, T, num_sims, monthly_addition=100)
    # fig, ax = plt.subplots()
    # for i in range(min(all_prices.shape[0], 100)):
    #     fig = plot_trajectory(all_prices[i], T, fig=fig, alpha=0.1, color='k')
    # fig = plot_trajectory(investments, T, fig, alpha=1, color='orange')

    # final_values = all_prices[:, -1]
    # print(f"Mean final value: ${np.mean(final_values):.2f}")
    # print(f"Median final value: ${np.median(final_values):.2f}")
    # print(f"5th percentile: ${np.percentile(final_values, 5):.2f}")
    # print(f"95th percentile: ${np.percentile(final_values, 95):.2f}")
    # print(f"Probability of losing money: {np.mean(final_values < investments[-1])*100:.2f}%")
    plt.show()

def gbm_step(S_t, mu, sigma, dt):
    """Simulate one Geometric Brownian Motion step"""
    Z = np.random.normal(0, 1)
    S_next = S_t * np.exp(
        (mu - 0.5 * sigma**2) * dt 
        + sigma * np.sqrt(dt) * Z
        )
    return S_next

def plot_trajectory(path, T, money_invested=None, regime_history=None, fig=None, alpha=1, color='k'):
    """
    Plot one GBM price path over time.
    Parameters:
    - path (np.ndarray) Simulated price path
    - T (float): Time horizon of path in years
    """
    if fig is None:
        fig, ax = plt.subplots()
    else:
        ax = fig.get_axes()[0]

    t = np.linspace(0, T, path.shape[0])
    if regime_history is not None:
        for i in range(len(regime_history) - 1):
            if regime_history[i] == "bull":
                ax.axvspan(t[i], t[i+1], color="blue", alpha=0.05)
            else:
                ax.axvspan(t[i], t[i+1], color="red", alpha=0.05)
        ax.plot(t, path, color=color)
    else:
        ax.plot(t, path, alpha=alpha, color=color)

    if money_invested is not None:
        ax.plot(t, money_invested, color='g')
    ax.set_ylabel("Price ($)")
    ax.set_xlabel("Time (years)")
    return fig


class Investment:
    def __init__(self, S0, regimes, transition_matrix, initial_regime="bull"):
        """
        Parameters:
        - S0 (float): Initial stock price or investment value
        - regimes (dict): contains mu and sigma for each regime (bull/bear)
        - transition_matrix (dict): Markov transition probabilities
        - initial_regime (str): starting market regime
        """
        self.S0 = S0
        self.regimes = regimes
        self.transition_matrix = transition_matrix
        self.initial_regime = initial_regime


    def sample_next_regime(self, current_regime):
        """Sample the next regime using Markov transition probabilities."""

        possible_regimes = list(self.transition_matrix[current_regime].keys())
        probabilities = list(self.transition_matrix[current_regime].values())
        return np.random.choice(possible_regimes, p=probabilities)

    def simulate_gbm_path(self, T, monthly_addition=0):
        """
        Simulate one GBM price path using gbm_step.
        Parameters:
        - T (float): Time horizon in years
        - monthly_addition (float): How much extra money you invest into it every month
        Returns:
        - prices (np.ndarray) Simulated price path
        """
        n_steps = T * 252  # set the timestep to be one trading day
        dt = T / n_steps

        prices = np.zeros(n_steps + 1)
        money_invested = np.zeros(n_steps + 1)  # to keep track of how much we are inputting

        prices[0] = self.S0
        money_invested[0] = self.S0

        # regime_history[0] describes the regime going from t=0 -> t=1
        regime_history = np.empty(n_steps + 1, dtype=object)
        current_regime = self.initial_regime
        regime_history[0] = current_regime

        for i in range(n_steps):
            regime_params = self.regimes[current_regime]  # get the (mu, sigma) pair for this regume
            # in here we will eventually change mu and sigma with shocks
            prices[i + 1] = gbm_step(prices[i], regime_params["mu"], regime_params["sigma"], dt)
            money_invested[i + 1] = money_invested[i]

            # there are 21 trading days in a month
            if (i+1) % 21 == 0:
                prices[i + 1] += monthly_addition
                money_invested[i + 1] += monthly_addition

            # update regime for next timestep (if we are at the end it doesn't matter, the value is meaningless)
            current_regime = self.sample_next_regime(current_regime)
            regime_history[i + 1] = current_regime

        return prices, money_invested, regime_history

    def run_gbm_monte_carlo(self, T, n_sims, monthly_addition=0):
        """Run MC on GBM simulations"""
        n_steps = T * 252  # set the timestep to be one day
        paths = np.zeros((n_sims, n_steps + 1))

        for i in range(n_sims):
            paths[i], investments = self.simulate_gbm_path(T, monthly_addition=monthly_addition)

        return paths, investments
    

if __name__ == "__main__":
    main()