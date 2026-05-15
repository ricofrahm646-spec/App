"""
JARVIS Portfolio-Level Risk Analytics.

Provides correlation analysis, exposure monitoring, Value at Risk (VaR),
Expected Shortfall (CVaR), and risk-adjusted return metrics.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PortfolioRisk:
    """Portfolio-level risk analysis for multi-position accounts."""

    def __init__(
        self,
        confidence_level: float = 0.95,
        lookback_days: int = 252,
    ) -> None:
        """
        Args:
            confidence_level: VaR / ES confidence (e.g. 0.95 = 95%).
            lookback_days: Number of historical days for calculations.
        """
        self.confidence_level = confidence_level
        self.lookback_days = lookback_days

    # ── Correlation analysis ─────────────────────────────────────────

    @staticmethod
    def calculate_correlation(
        returns_a: List[float],
        returns_b: List[float],
    ) -> float:
        """Pearson correlation coefficient between two return series.

        Args:
            returns_a: List of periodic returns for asset A.
            returns_b: List of periodic returns for asset B.

        Returns:
            Correlation in [-1, 1].
        """
        n = min(len(returns_a), len(returns_b))
        if n < 2:
            return 0.0

        a = returns_a[:n]
        b = returns_b[:n]
        mean_a = sum(a) / n
        mean_b = sum(b) / n

        cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / (n - 1)
        std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a) / (n - 1))
        std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b) / (n - 1))

        if std_a == 0 or std_b == 0:
            return 0.0

        return round(cov / (std_a * std_b), 6)

    def correlation_matrix(
        self,
        returns_by_symbol: Dict[str, List[float]],
    ) -> Dict[Tuple[str, str], float]:
        """Compute pairwise correlations for all provided symbols.

        Args:
            returns_by_symbol: Mapping of symbol -> list of returns.

        Returns:
            Dict keyed by (symbol_a, symbol_b) with correlation values.
        """
        symbols = sorted(returns_by_symbol.keys())
        matrix: Dict[Tuple[str, str], float] = {}
        for i, sym_a in enumerate(symbols):
            for sym_b in symbols[i:]:
                if sym_a == sym_b:
                    matrix[(sym_a, sym_b)] = 1.0
                else:
                    corr = self.calculate_correlation(
                        returns_by_symbol[sym_a],
                        returns_by_symbol[sym_b],
                    )
                    matrix[(sym_a, sym_b)] = corr
                    matrix[(sym_b, sym_a)] = corr
        return matrix

    # ── Exposure monitoring ──────────────────────────────────────────

    @staticmethod
    def calculate_exposure(
        positions: List[Dict[str, Any]],
        account_balance: float,
    ) -> Dict[str, Any]:
        """Analyse portfolio exposure.

        Args:
            positions: List of position dicts with keys:
                symbol, direction ("BUY"/"SELL"), volume, current_value
            account_balance: Current account balance.

        Returns:
            Dict with gross_exposure, net_exposure, exposure_ratio,
            long_exposure, short_exposure, by_symbol breakdown.
        """
        long_exposure = 0.0
        short_exposure = 0.0
        by_symbol: Dict[str, float] = {}

        for pos in positions:
            value = abs(pos.get("current_value", 0.0))
            direction = pos.get("direction", "BUY").upper()
            symbol = pos.get("symbol", "UNKNOWN")

            if direction == "BUY":
                long_exposure += value
            else:
                short_exposure += value

            by_symbol[symbol] = by_symbol.get(symbol, 0.0) + value

        gross = long_exposure + short_exposure
        net = long_exposure - short_exposure
        ratio = gross / account_balance if account_balance > 0 else 0.0

        return {
            "gross_exposure": round(gross, 2),
            "net_exposure": round(net, 2),
            "exposure_ratio": round(ratio, 4),
            "long_exposure": round(long_exposure, 2),
            "short_exposure": round(short_exposure, 2),
            "by_symbol": by_symbol,
        }

    # ── Value at Risk (parametric) ───────────────────────────────────

    def calculate_var(
        self,
        returns: List[float],
        portfolio_value: float,
        confidence: Optional[float] = None,
    ) -> Dict[str, float]:
        """Parametric (Gaussian) Value at Risk.

        Args:
            returns: Historical portfolio return series (decimal, not %).
            portfolio_value: Current portfolio value.
            confidence: Override default confidence level.

        Returns:
            Dict with var_pct, var_amount, mean_return, volatility.
        """
        conf = confidence or self.confidence_level
        n = len(returns)
        if n < 2:
            return {
                "var_pct": 0.0,
                "var_amount": 0.0,
                "mean_return": 0.0,
                "volatility": 0.0,
            }

        mean_r = sum(returns) / n
        variance = sum((r - mean_r) ** 2 for r in returns) / (n - 1)
        vol = math.sqrt(variance)

        z = self._z_score(conf)
        var_pct = -(mean_r - z * vol)
        var_amount = var_pct * portfolio_value

        return {
            "var_pct": round(var_pct, 6),
            "var_amount": round(var_amount, 2),
            "mean_return": round(mean_r, 6),
            "volatility": round(vol, 6),
        }

    # ── Historical VaR ───────────────────────────────────────────────

    def calculate_historical_var(
        self,
        returns: List[float],
        portfolio_value: float,
        confidence: Optional[float] = None,
    ) -> Dict[str, float]:
        """Non-parametric (historical simulation) VaR.

        Sorts historical returns and picks the loss at the
        (1 - confidence) percentile.
        """
        conf = confidence or self.confidence_level
        n = len(returns)
        if n < 2:
            return {"var_pct": 0.0, "var_amount": 0.0}

        sorted_returns = sorted(returns)
        index = int(math.floor((1 - conf) * n))
        index = max(0, min(index, n - 1))
        var_pct = -sorted_returns[index]
        var_amount = var_pct * portfolio_value

        return {
            "var_pct": round(var_pct, 6),
            "var_amount": round(var_amount, 2),
        }

    # ── Expected Shortfall (CVaR) ────────────────────────────────────

    def calculate_expected_shortfall(
        self,
        returns: List[float],
        portfolio_value: float,
        confidence: Optional[float] = None,
    ) -> Dict[str, float]:
        """Expected Shortfall (Conditional VaR).

        Average loss in the worst (1 - confidence) fraction of scenarios.
        """
        conf = confidence or self.confidence_level
        n = len(returns)
        if n < 2:
            return {"es_pct": 0.0, "es_amount": 0.0}

        sorted_returns = sorted(returns)
        cutoff = int(math.floor((1 - conf) * n))
        cutoff = max(1, cutoff)
        tail = sorted_returns[:cutoff]
        es_pct = -(sum(tail) / len(tail))
        es_amount = es_pct * portfolio_value

        return {
            "es_pct": round(es_pct, 6),
            "es_amount": round(es_amount, 2),
        }

    # ── Risk-adjusted return metrics ─────────────────────────────────

    @staticmethod
    def sharpe_ratio(
        returns: List[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> float:
        """Annualised Sharpe ratio."""
        n = len(returns)
        if n < 2:
            return 0.0

        mean_r = sum(returns) / n
        excess = mean_r - risk_free_rate / periods_per_year
        vol = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / (n - 1))
        if vol == 0:
            return 0.0

        return round(excess / vol * math.sqrt(periods_per_year), 4)

    @staticmethod
    def sortino_ratio(
        returns: List[float],
        risk_free_rate: float = 0.0,
        periods_per_year: int = 252,
    ) -> float:
        """Annualised Sortino ratio (penalises only downside volatility)."""
        n = len(returns)
        if n < 2:
            return 0.0

        mean_r = sum(returns) / n
        excess = mean_r - risk_free_rate / periods_per_year
        downside = [r for r in returns if r < 0]
        if not downside:
            return float("inf") if excess > 0 else 0.0

        down_var = sum(r ** 2 for r in downside) / len(downside)
        down_vol = math.sqrt(down_var)
        if down_vol == 0:
            return 0.0

        return round(excess / down_vol * math.sqrt(periods_per_year), 4)

    @staticmethod
    def calmar_ratio(
        annualised_return: float,
        max_drawdown_pct: float,
    ) -> float:
        """Calmar ratio (return / max drawdown)."""
        if max_drawdown_pct == 0:
            return 0.0
        return round(annualised_return / max_drawdown_pct, 4)

    @staticmethod
    def profit_factor(
        gross_profit: float,
        gross_loss: float,
    ) -> float:
        """Profit factor (gross profit / gross loss)."""
        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0
        return round(abs(gross_profit / gross_loss), 4)

    def full_risk_report(
        self,
        returns: List[float],
        portfolio_value: float,
        positions: List[Dict[str, Any]],
        account_balance: float,
        returns_by_symbol: Optional[Dict[str, List[float]]] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive portfolio risk report.

        Returns a single dict aggregating VaR, ES, exposure, Sharpe,
        Sortino, and optionally correlation data.
        """
        var_data = self.calculate_var(returns, portfolio_value)
        hist_var = self.calculate_historical_var(returns, portfolio_value)
        es_data = self.calculate_expected_shortfall(returns, portfolio_value)
        exposure = self.calculate_exposure(positions, account_balance)
        sharpe = self.sharpe_ratio(returns)
        sortino = self.sortino_ratio(returns)

        report: Dict[str, Any] = {
            "parametric_var": var_data,
            "historical_var": hist_var,
            "expected_shortfall": es_data,
            "exposure": exposure,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
        }

        if returns_by_symbol:
            report["correlations"] = self.correlation_matrix(returns_by_symbol)

        logger.info("Portfolio risk report generated")
        return report

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _z_score(confidence: float) -> float:
        """Approximate inverse-normal z-score for common confidence levels.

        Uses the rational approximation from Abramowitz & Stegun 26.2.23.
        """
        if confidence <= 0 or confidence >= 1:
            raise ValueError("Confidence must be between 0 and 1 exclusive")

        p = 1 - confidence  # tail probability
        if p > 0.5:
            p = 1 - p

        t = math.sqrt(-2.0 * math.log(p))
        c0, c1, c2 = 2.515517, 0.802853, 0.010328
        d1, d2, d3 = 1.432788, 0.189269, 0.001308
        z = t - (c0 + c1 * t + c2 * t * t) / (
            1 + d1 * t + d2 * t * t + d3 * t * t * t
        )
        return z
