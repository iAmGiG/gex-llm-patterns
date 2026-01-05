"""
Portfolio State Tracker

Manages cash, positions, and trade execution for backtesting.
Refactored from experiment_293 simulate_trading() function (lines 216-298).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Trade:
    """Single trade record."""

    date: str
    action: str  # "BUY" or "SELL"
    shares: float
    price: float
    commission: float = 0.0

    @property
    def value(self) -> float:
        """Trade value (excluding commission)."""
        return self.shares * self.price

    @property
    def total_cost(self) -> float:
        """Trade value including commission."""
        return self.value + self.commission


class Portfolio:
    """
    Portfolio state tracker for backtesting.

    Manages cash, positions, and trade history.
    Refactored from experiment_293 simulate_trading() logic.

    Attributes:
        initial_capital: Starting capital
        cash: Current cash balance
        position: Current position size (shares)
        trades: List of executed trades
        commission_per_share: Commission cost per share (default: 0.005 for Alpaca)
    """

    def __init__(self, initial_capital: float = 10000, commission_per_share: float = 0.005):
        """
        Initialize portfolio.

        Args:
            initial_capital: Starting capital (default: $10,000)
            commission_per_share: Commission per share (default: $0.005 for Alpaca)
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0.0
        self.trades: List[Trade] = []
        self.commission_per_share = commission_per_share

    def reset(self):
        """Reset portfolio to initial state."""
        self.cash = self.initial_capital
        self.position = 0.0
        self.trades = []

    def get_value(self, current_price: float) -> float:
        """
        Calculate current portfolio value.

        Args:
            current_price: Current market price

        Returns:
            Portfolio value (cash + position value)
        """
        return self.cash + (self.position * current_price)

    def can_buy(self, shares: float, price: float) -> bool:
        """
        Check if portfolio has enough cash to buy.

        Args:
            shares: Number of shares to buy
            price: Price per share

        Returns:
            True if sufficient cash available
        """
        cost = shares * price
        commission = shares * self.commission_per_share
        return self.cash >= (cost + commission)

    def can_sell(self, shares: float) -> bool:
        """
        Check if portfolio has enough shares to sell.

        Args:
            shares: Number of shares to sell

        Returns:
            True if sufficient shares available
        """
        return self.position >= shares

    def buy(self, date: str, shares: float, price: float) -> Optional[Trade]:
        """
        Execute buy trade.

        Refactored from experiment_293 simulate_trading() BUY logic (lines 236-251).

        Args:
            date: Trade date
            shares: Number of shares to buy
            price: Price per share

        Returns:
            Trade object if successful, None if insufficient cash
        """
        if shares <= 0:
            return None

        cost = shares * price
        commission = shares * self.commission_per_share
        total_cost = cost + commission

        if self.cash < total_cost:
            # Insufficient cash - buy what we can afford
            affordable_shares = self.cash / (price + self.commission_per_share)
            if affordable_shares < 0.01:  # Min 0.01 shares
                return None
            shares = affordable_shares
            cost = shares * price
            commission = shares * self.commission_per_share
            total_cost = cost + commission

        self.position += shares
        self.cash -= total_cost

        trade = Trade(date=date, action="BUY", shares=shares, price=price, commission=commission)
        self.trades.append(trade)

        return trade

    def sell(self, date: str, shares: float, price: float) -> Optional[Trade]:
        """
        Execute sell trade.

        Refactored from experiment_293 simulate_trading() SELL logic (lines 253-268).

        Args:
            date: Trade date
            shares: Number of shares to sell
            price: Price per share

        Returns:
            Trade object if successful, None if insufficient shares
        """
        if shares <= 0 or self.position <= 0:
            return None

        # Can't sell more than we have
        shares = min(shares, self.position)

        revenue = shares * price
        commission = shares * self.commission_per_share
        net_revenue = revenue - commission

        self.position -= shares
        self.cash += net_revenue

        trade = Trade(date=date, action="SELL", shares=shares, price=price, commission=commission)
        self.trades.append(trade)

        return trade

    def execute_decision(self, date: str, decision: Dict, current_price: float) -> Optional[Trade]:
        """
        Execute trading decision.

        Handles position_size parameter from VoterAgent decisions.
        Refactored from experiment_293 simulate_trading() decision execution logic.

        Args:
            date: Trading date
            decision: Decision dict with keys: action, position_size, confidence, reasoning
            current_price: Current market price

        Returns:
            Trade object if trade executed, None otherwise
        """
        action = decision.get("action", "HOLD")
        position_size = decision.get("position_size", 0.0)

        if action == "BUY" and self.cash > 0:
            # Calculate buy amount based on position_size (0.5 = weak, 1.0 = strong)
            buy_amount = self.cash * position_size
            shares_to_buy = buy_amount / current_price
            return self.buy(date=date, shares=shares_to_buy, price=current_price)

        elif action == "SELL" and self.position > 0:
            # Calculate sell amount based on position_size
            shares_to_sell = self.position * position_size
            return self.sell(date=date, shares=shares_to_sell, price=current_price)

        return None

    def get_trade_summary(self) -> Dict:
        """
        Get summary of all trades.

        Returns:
            Dictionary with trade statistics
        """
        if not self.trades:
            return {
                "num_trades": 0,
                "num_buys": 0,
                "num_sells": 0,
                "total_commission": 0.0,
                "avg_trade_size": 0.0,
            }

        buys = [t for t in self.trades if t.action == "BUY"]
        sells = [t for t in self.trades if t.action == "SELL"]
        total_commission = sum(t.commission for t in self.trades)
        avg_trade_size = sum(t.shares for t in self.trades) / len(self.trades)

        return {
            "num_trades": len(self.trades),
            "num_buys": len(buys),
            "num_sells": len(sells),
            "total_commission": total_commission,
            "avg_trade_size": avg_trade_size,
        }
