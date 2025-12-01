"""
Advanced Greeks Calculations Module

Implements second-order and third-order Greeks for comprehensive options analysis.
Includes both finite difference and analytical Black-Scholes formulas.
"""

import numpy as np
from scipy.stats import norm


class AdvancedGreeks:
    """
    Calculate advanced Greeks (second and third order) for options.

    Provides both finite difference and analytical methods for
    comprehensive Greeks analysis including Vanna, Charm, Vomma, Veta,
    Speed, Zomma, and Color.
    """

    def __init__(self, risk_free_rate=0.05):
        """
        Initialize Greeks calculator.

        Args:
            risk_free_rate: Risk-free interest rate for calculations
        """
        self.risk_free_rate = risk_free_rate

    # ========== First-Order Greeks (Base) ==========

    def calculate_delta(self, S, K, T, r, sigma, option_type="call"):
        """Calculate option delta."""
        if T <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

        if option_type == "call":
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1

        return delta

    def calculate_gamma(self, S, K, T, r, sigma):
        """Calculate option gamma (same for calls and puts)."""
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

        return gamma

    def calculate_vega(self, S, K, T, r, sigma):
        """Calculate option vega (same for calls and puts)."""
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T)

        return vega

    def calculate_theta(self, S, K, T, r, sigma, option_type="call"):
        """Calculate option theta."""
        if T <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            theta = -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)
        else:
            theta = -S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)

        return theta / 365  # Convert to per day

    # ========== Second-Order Greeks ==========

    def calculate_vanna_analytical(self, S, K, T, r, sigma):
        """
        Calculate Vanna (∂²V/∂S∂σ) using analytical formula.

        Vanna measures delta sensitivity to volatility changes.
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        vanna = -norm.pdf(d1) * d2 / sigma
        return vanna

    def calculate_vanna_finite(self, S, K, T, r, sigma, vol_bump=0.01):
        """
        Calculate Vanna using finite difference method.
        """
        delta_up = self.calculate_delta(S, K, T, r, sigma + vol_bump)
        delta_down = self.calculate_delta(S, K, T, r, sigma - vol_bump)

        vanna = (delta_up - delta_down) / (2 * vol_bump)
        return vanna

    def calculate_charm_analytical(self, S, K, T, r, sigma, option_type="call"):
        """
        Calculate Charm (∂²V/∂S∂τ) using analytical formula.

        Charm measures delta sensitivity to time decay.
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            charm = -norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T)) / (2 * T * sigma * np.sqrt(T))
        else:
            charm = norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T)) / (2 * T * sigma * np.sqrt(T))

        return charm

    def calculate_charm_finite(self, S, K, T, r, sigma, time_bump=1 / 365, option_type="call"):
        """
        Calculate Charm using finite difference method.
        """
        if T <= time_bump:
            return 0.0

        delta_now = self.calculate_delta(S, K, T, r, sigma, option_type)
        delta_later = self.calculate_delta(S, K, T - time_bump, r, sigma, option_type)

        charm = -(delta_later - delta_now) / time_bump
        return charm

    def calculate_vomma_analytical(self, S, K, T, r, sigma):
        """
        Calculate Vomma/Volga (∂²V/∂σ²) using analytical formula.

        Vomma measures vega sensitivity to volatility changes.
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        vomma = S * norm.pdf(d1) * np.sqrt(T) * d1 * d2 / sigma
        return vomma

    def calculate_vomma_finite(self, S, K, T, r, sigma, vol_bump=0.01):
        """
        Calculate Vomma using finite difference method.
        """
        vega_up = self.calculate_vega(S, K, T, r, sigma + vol_bump)
        vega_down = self.calculate_vega(S, K, T, r, sigma - vol_bump)

        vomma = (vega_up - vega_down) / (2 * vol_bump)
        return vomma

    def calculate_veta_analytical(self, S, K, T, r, sigma):
        """
        Calculate Veta (∂²V/∂σ∂τ) using analytical formula.

        Veta measures vega sensitivity to time decay.
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        veta = -S * norm.pdf(d1) * np.sqrt(T) * (r * d1 / (sigma * np.sqrt(T)) - (1 + d1 * d2) / (2 * T))
        return veta

    def calculate_veta_finite(self, S, K, T, r, sigma, time_bump=1 / 365):
        """
        Calculate Veta using finite difference method.
        """
        if T <= time_bump:
            return 0.0

        vega_now = self.calculate_vega(S, K, T, r, sigma)
        vega_later = self.calculate_vega(S, K, T - time_bump, r, sigma)

        veta = -(vega_later - vega_now) / time_bump
        return veta

    # ========== Third-Order Greeks ==========

    def calculate_speed_analytical(self, S, K, T, r, sigma):
        """
        Calculate Speed (∂³V/∂S³) using analytical formula.

        Speed measures gamma sensitivity to underlying price changes.
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

        speed = -norm.pdf(d1) * (d1 / (sigma**2 * T) + 1 / (sigma * np.sqrt(T))) / (S**2)
        return speed

    def calculate_speed_finite(self, S, K, T, r, sigma, price_bump_pct=0.01):
        """
        Calculate Speed using finite difference on gamma.
        """
        price_bump = S * price_bump_pct

        gamma_up = self.calculate_gamma(S + price_bump, K, T, r, sigma)
        gamma_down = self.calculate_gamma(S - price_bump, K, T, r, sigma)

        speed = (gamma_up - gamma_down) / (2 * price_bump)
        return speed

    def calculate_zomma_analytical(self, S, K, T, r, sigma):
        """
        Calculate Zomma (∂³V/∂S²∂σ) using analytical formula.

        Zomma measures gamma sensitivity to volatility changes.
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        zomma = norm.pdf(d1) * (d1 * d2 - 1) / (S * sigma**2 * np.sqrt(T))
        return zomma

    def calculate_zomma_finite(self, S, K, T, r, sigma, vol_bump=0.01):
        """
        Calculate Zomma using finite difference on gamma.
        """
        gamma_up = self.calculate_gamma(S, K, T, r, sigma + vol_bump)
        gamma_down = self.calculate_gamma(S, K, T, r, sigma - vol_bump)

        zomma = (gamma_up - gamma_down) / (2 * vol_bump)
        return zomma

    def calculate_color_analytical(self, S, K, T, r, sigma):
        """
        Calculate Color (∂³V/∂S²∂τ) using analytical formula.

        Color measures gamma sensitivity to time decay.
        """
        if T <= 0 or sigma <= 0:
            return 0.0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        color = (
            -norm.pdf(d1)
            * (2 * r + (2 * r - sigma**2) * d1 / (sigma * np.sqrt(T)) - d1**2 / (sigma**2 * T))
            / (2 * S * T * sigma * np.sqrt(T))
        )
        return color

    def calculate_color_finite(self, S, K, T, r, sigma, time_bump=1 / 365):
        """
        Calculate Color using finite difference on gamma.
        """
        if T <= time_bump:
            return 0.0

        gamma_now = self.calculate_gamma(S, K, T, r, sigma)
        gamma_later = self.calculate_gamma(S, K, T - time_bump, r, sigma)

        color = -(gamma_later - gamma_now) / time_bump
        return color

    # ========== Combined Calculations ==========

    def calculate_all_greeks(self, S, K, T, r, sigma, option_type="call", method="analytical"):
        """
        Calculate all Greeks for an option.

        Args:
            S: Spot price
            K: Strike price
            T: Time to expiration (years)
            r: Risk-free rate
            sigma: Implied volatility
            option_type: 'call' or 'put'
            method: 'analytical' or 'finite_difference'

        Returns:
            Dictionary with all Greeks
        """
        greeks = {}

        # First-order Greeks
        greeks["delta"] = self.calculate_delta(S, K, T, r, sigma, option_type)
        greeks["gamma"] = self.calculate_gamma(S, K, T, r, sigma)
        greeks["vega"] = self.calculate_vega(S, K, T, r, sigma)
        greeks["theta"] = self.calculate_theta(S, K, T, r, sigma, option_type)

        # Second-order Greeks
        if method == "analytical":
            greeks["vanna"] = self.calculate_vanna_analytical(S, K, T, r, sigma)
            greeks["charm"] = self.calculate_charm_analytical(S, K, T, r, sigma, option_type)
            greeks["vomma"] = self.calculate_vomma_analytical(S, K, T, r, sigma)
            greeks["veta"] = self.calculate_veta_analytical(S, K, T, r, sigma)

            # Third-order Greeks
            greeks["speed"] = self.calculate_speed_analytical(S, K, T, r, sigma)
            greeks["zomma"] = self.calculate_zomma_analytical(S, K, T, r, sigma)
            greeks["color"] = self.calculate_color_analytical(S, K, T, r, sigma)
        else:
            greeks["vanna"] = self.calculate_vanna_finite(S, K, T, r, sigma)
            greeks["charm"] = self.calculate_charm_finite(S, K, T, r, sigma, option_type=option_type)
            greeks["vomma"] = self.calculate_vomma_finite(S, K, T, r, sigma)
            greeks["veta"] = self.calculate_veta_finite(S, K, T, r, sigma)

            # Third-order Greeks
            greeks["speed"] = self.calculate_speed_finite(S, K, T, r, sigma)
            greeks["zomma"] = self.calculate_zomma_finite(S, K, T, r, sigma)
            greeks["color"] = self.calculate_color_finite(S, K, T, r, sigma)

        return greeks

    def calculate_greeks_surface(self, spot_range, strike, T, r, sigma, greek_name="gamma"):
        """
        Calculate a Greek across a range of spot prices.

        Args:
            spot_range: Array of spot prices
            strike: Strike price
            T: Time to expiration
            r: Risk-free rate
            sigma: Implied volatility
            greek_name: Name of Greek to calculate

        Returns:
            Array of Greek values
        """
        greek_values = []

        for spot in spot_range:
            if greek_name == "gamma":
                value = self.calculate_gamma(spot, strike, T, r, sigma)
            elif greek_name == "vanna":
                value = self.calculate_vanna_analytical(spot, strike, T, r, sigma)
            elif greek_name == "speed":
                value = self.calculate_speed_analytical(spot, strike, T, r, sigma)
            elif greek_name == "zomma":
                value = self.calculate_zomma_analytical(spot, strike, T, r, sigma)
            elif greek_name == "color":
                value = self.calculate_color_analytical(spot, strike, T, r, sigma)
            else:
                value = 0

            greek_values.append(value)

        return np.array(greek_values)
