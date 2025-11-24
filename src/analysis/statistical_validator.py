"""Statistical Validator.

Provides statistical significance testing and validation for pattern analysis. Includes chi-square tests, bootstrap
confidence intervals, and permutation testing.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats
from scipy.stats import chi2

from ..utils.date_utils import now_iso

logger = logging.getLogger(__name__)


class StatisticalValidator:
    """Statistical significance framework for pattern validation.

    Provides robust statistical testing to determine if patterns have statistically significant predictive power vs
    random chance.
    """

    def __init__(self, confidence_level: float = 0.95, min_samples: int = 30):
        """Initialize statistical validator.

        Args:
            confidence_level: Confidence level for statistical tests (default 0.95)
            min_samples: Minimum sample size for reliable testing (default 30)
        """
        self.confidence_level = confidence_level
        self.alpha = 1.0 - confidence_level
        self.min_samples = min_samples

        logger.info(f"StatisticalValidator initialized (α={self.alpha}, min_n={min_samples})")

    def calculate_significance(self, pattern_results: Dict) -> Dict:
        """Determine statistical significance of pattern success rates.

        Args:
            pattern_results: Dictionary with pattern analysis results

        Returns:
            Dictionary with statistical significance results
        """
        logger.info("Calculating statistical significance for pattern results")

        results = {}

        for pattern, data in pattern_results.items():
            if not isinstance(data, dict):
                continue

            valid_returns = data.get("valid_returns", 0)

            if valid_returns < self.min_samples:
                results[pattern] = {
                    "significant": False,
                    "reason": f"Insufficient samples ({valid_returns} < {self.min_samples})",
                    "sample_size": valid_returns,
                }
                continue

            # Extract return data if available
            returns = self._extract_returns_from_results(data)

            if returns is None or len(returns) == 0:
                results[pattern] = {
                    "significant": False,
                    "reason": "No return data available",
                    "sample_size": valid_returns,
                }
                continue

            # Perform statistical tests
            significance_results = self._perform_comprehensive_testing(returns, pattern)
            significance_results["sample_size"] = len(returns)

            results[pattern] = significance_results

        return {
            "analysis_date": now_iso(),
            "confidence_level": self.confidence_level,
            "min_sample_threshold": self.min_samples,
            "patterns_tested": len(results),
            "results": results,
        }

    def chi_square_test(self, observed_outcomes: Dict, expected_probability: float = 0.5) -> Tuple[float, float]:
        """Chi-square test for independence of pattern and positive outcomes.

        Args:
            observed_outcomes: Dictionary with 'positive' and 'negative' outcome counts
            expected_probability: Expected probability of positive outcome under null hypothesis

        Returns:
            Tuple of (chi2_statistic, p_value)
        """
        positive = observed_outcomes.get("positive", 0)
        negative = observed_outcomes.get("negative", 0)
        total = positive + negative

        if total == 0:
            return np.nan, 1.0

        # Expected counts under null hypothesis
        expected_positive = total * expected_probability
        expected_negative = total * (1 - expected_probability)

        # Chi-square test
        observed = np.array([positive, negative])
        expected = np.array([expected_positive, expected_negative])

        # Avoid division by zero
        if np.any(expected == 0):
            return np.nan, 1.0

        chi2_stat = np.sum((observed - expected) ** 2 / expected)
        p_value = 1 - chi2.cdf(chi2_stat, df=1)

        return chi2_stat, p_value

    def bootstrap_ci(self, returns: np.ndarray, statistic_func=np.mean, n_bootstrap: int = 1000) -> Tuple[float, float]:
        """Bootstrap confidence intervals for return statistics.

        Args:
            returns: Array of return values
            statistic_func: Function to calculate statistic (default: mean)
            n_bootstrap: Number of bootstrap samples

        Returns:
            Tuple of (lower_bound, upper_bound) for confidence interval
        """
        if len(returns) == 0:
            return np.nan, np.nan

        bootstrap_stats = []
        n_samples = len(returns)

        for _ in range(n_bootstrap):
            bootstrap_sample = np.random.choice(returns, size=n_samples, replace=True)
            bootstrap_stats.append(statistic_func(bootstrap_sample))

        lower_percentile = (1 - self.confidence_level) / 2 * 100
        upper_percentile = (1 + self.confidence_level) / 2 * 100

        ci_lower = np.percentile(bootstrap_stats, lower_percentile)
        ci_upper = np.percentile(bootstrap_stats, upper_percentile)

        return ci_lower, ci_upper

    def permutation_test(self, returns: np.ndarray, null_mean: float = 0.0, n_permutations: int = 1000) -> float:
        """Permutation test for mean return significance.

        Args:
            returns: Array of return values
            null_mean: Null hypothesis mean (default 0.0)
            n_permutations: Number of permutation samples

        Returns:
            P-value for two-tailed test
        """
        if len(returns) == 0:
            return 1.0

        observed_mean = np.mean(returns)
        centered_returns = returns - null_mean

        permutation_means = []
        for _ in range(n_permutations):
            # Randomly flip signs (two-tailed test)
            signs = np.random.choice([-1, 1], size=len(centered_returns))
            permuted_returns = centered_returns * signs
            permutation_means.append(np.mean(permuted_returns))

        # Two-tailed p-value
        observed_stat = abs(observed_mean - null_mean)
        permutation_stats = [abs(mean) for mean in permutation_means]
        p_value = np.sum(np.array(permutation_stats) >= observed_stat) / n_permutations

        return p_value

    def t_test_one_sample(self, returns: np.ndarray, null_mean: float = 0.0) -> Tuple[float, float]:
        """One-sample t-test for mean return significance.

        Args:
            returns: Array of return values
            null_mean: Null hypothesis mean

        Returns:
            Tuple of (t_statistic, p_value)
        """
        if len(returns) < 2:
            return np.nan, 1.0

        try:
            t_stat, p_value = stats.ttest_1samp(returns, null_mean)
            return t_stat, p_value
        except Exception as e:
            logger.warning(f"T-test failed: {e}")
            return np.nan, 1.0

    def calculate_effect_size(self, returns: np.ndarray, baseline_returns: np.ndarray = None) -> Dict:
        """Calculate effect size measures (Cohen's d, etc.).

        Args:
            returns: Array of pattern returns
            baseline_returns: Array of baseline/random returns (optional)

        Returns:
            Dictionary with effect size measures
        """
        if len(returns) == 0:
            return {"error": "No returns data"}

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        effect_sizes = {
            "mean_return": mean_return,
            "std_return": std_return,
            "standardized_mean": mean_return / std_return if std_return > 0 else np.nan,
        }

        # Cohen's d vs zero (no return)
        if std_return > 0:
            effect_sizes["cohens_d_vs_zero"] = mean_return / std_return

        # Cohen's d vs baseline if provided
        if baseline_returns is not None and len(baseline_returns) > 0:
            baseline_mean = np.mean(baseline_returns)
            baseline_std = np.std(baseline_returns)

            # Pooled standard deviation
            pooled_std = np.sqrt(
                ((len(returns) - 1) * std_return**2 + (len(baseline_returns) - 1) * baseline_std**2)
                / (len(returns) + len(baseline_returns) - 2)
            )

            if pooled_std > 0:
                effect_sizes["cohens_d_vs_baseline"] = (mean_return - baseline_mean) / pooled_std

            effect_sizes["baseline_mean"] = baseline_mean
            effect_sizes["baseline_std"] = baseline_std

        return effect_sizes

    def multiple_testing_correction(self, p_values: List[float], method: str = "bonferroni") -> List[float]:
        """Multiple testing correction for pattern analysis.

        Args:
            p_values: List of p-values from multiple tests
            method: Correction method ('bonferroni', 'fdr_bh')

        Returns:
            List of corrected p-values
        """
        if not p_values:
            return []

        p_values = np.array(p_values)

        if method == "bonferroni":
            # Bonferroni correction
            corrected = p_values * len(p_values)
            corrected = np.minimum(corrected, 1.0)  # Cap at 1.0

        elif method == "fdr_bh":
            # Benjamini-Hochberg (FDR) correction
            n = len(p_values)
            sorted_indices = np.argsort(p_values)
            sorted_p = p_values[sorted_indices]

            # BH critical values
            corrected_sorted = sorted_p * n / (np.arange(1, n + 1))

            # Ensure monotonicity (step-up procedure)
            for i in range(n - 2, -1, -1):
                if corrected_sorted[i] > corrected_sorted[i + 1]:
                    corrected_sorted[i] = corrected_sorted[i + 1]

            # Reorder back to original
            corrected = np.empty_like(corrected_sorted)
            corrected[sorted_indices] = corrected_sorted
            corrected = np.minimum(corrected, 1.0)

        else:
            logger.warning(f"Unknown correction method: {method}")
            return p_values.tolist()

        return corrected.tolist()

    def validate_pattern_stability(self, returns_by_period: Dict[str, np.ndarray]) -> Dict:
        """Test pattern stability across different time periods.

        Args:
            returns_by_period: Dictionary mapping period names to return arrays

        Returns:
            Dictionary with stability analysis results
        """
        logger.info("Validating pattern stability across time periods")

        if len(returns_by_period) < 2:
            return {"error": "Need at least 2 time periods for stability analysis"}

        periods = list(returns_by_period.keys())
        period_stats = {}

        # Calculate statistics for each period
        for period, returns in returns_by_period.items():
            if len(returns) == 0:
                continue

            period_stats[period] = {
                "mean_return": np.mean(returns),
                "std_return": np.std(returns),
                "win_rate": np.sum(returns > 0) / len(returns),
                "sample_size": len(returns),
            }

        # Test for significant differences between periods
        stability_tests = {}

        # Pairwise t-tests for mean returns
        for i, period1 in enumerate(periods):
            for period2 in periods[i + 1 :]:
                if period1 in returns_by_period and period2 in returns_by_period:
                    returns1 = returns_by_period[period1]
                    returns2 = returns_by_period[period2]

                    if len(returns1) >= 5 and len(returns2) >= 5:
                        try:
                            t_stat, p_value = stats.ttest_ind(returns1, returns2)
                            stability_tests[f"{period1}_vs_{period2}"] = {
                                "t_statistic": t_stat,
                                "p_value": p_value,
                                "significantly_different": p_value < self.alpha,
                            }
                        except Exception as e:
                            logger.warning(f"T-test failed for {period1} vs {period2}: {e}")

        # Overall stability score
        significant_differences = sum(
            1 for test in stability_tests.values() if test.get("significantly_different", False)
        )
        total_comparisons = len(stability_tests)

        stability_score = 1.0 - (significant_differences / total_comparisons) if total_comparisons > 0 else 1.0

        return {
            "period_statistics": period_stats,
            "pairwise_tests": stability_tests,
            "stability_score": stability_score,
            "significant_differences": significant_differences,
            "total_comparisons": total_comparisons,
            "interpretation": self._interpret_stability_score(stability_score),
        }

    def _extract_returns_from_results(self, data: Dict) -> Optional[np.ndarray]:
        """Extract return array from pattern results dictionary."""
        # Try different possible keys for return data
        possible_keys = ["returns", "forward_returns", "return_data", "outcomes"]

        for key in possible_keys:
            if key in data and isinstance(data[key], (list, np.ndarray)):
                return np.array(data[key])

        # Try to reconstruct from summary statistics if available
        if all(k in data for k in ["positive_returns", "negative_returns", "avg_winning_return", "avg_losing_return"]):
            # Approximate return distribution from summary stats
            n_positive = data["positive_returns"]
            n_negative = data["negative_returns"]
            avg_win = data["avg_winning_return"]
            avg_loss = data["avg_losing_return"]

            # Create approximate return array
            returns = []
            returns.extend([avg_win] * n_positive)
            returns.extend([avg_loss] * n_negative)

            return np.array(returns)

        return None

    def _perform_comprehensive_testing(self, returns: np.ndarray, pattern_name: str) -> Dict:
        """Perform comprehensive statistical testing on return data."""
        results = {"pattern": pattern_name, "analysis_date": now_iso()}

        # Basic statistics (calculated but not used in this function)
        # mean_return = np.mean(returns)
        # win_rate = np.sum(returns > 0) / len(returns)

        # 1. One-sample t-test (vs zero return)
        t_stat, t_p_value = self.t_test_one_sample(returns, null_mean=0.0)
        results["t_test"] = {
            "t_statistic": t_stat,
            "p_value": t_p_value,
            "significant": t_p_value < self.alpha if not np.isnan(t_p_value) else False,
        }

        # 2. Chi-square test (for win rate vs 50%)
        outcome_counts = {"positive": np.sum(returns > 0), "negative": np.sum(returns <= 0)}
        chi2_stat, chi2_p_value = self.chi_square_test(outcome_counts, expected_probability=0.5)
        results["chi_square_test"] = {
            "chi2_statistic": chi2_stat,
            "p_value": chi2_p_value,
            "significant": chi2_p_value < self.alpha if not np.isnan(chi2_p_value) else False,
        }

        # 3. Permutation test
        perm_p_value = self.permutation_test(returns, null_mean=0.0)
        results["permutation_test"] = {"p_value": perm_p_value, "significant": perm_p_value < self.alpha}

        # 4. Bootstrap confidence intervals
        ci_lower, ci_upper = self.bootstrap_ci(returns, statistic_func=np.mean)
        results["bootstrap_ci"] = {
            "confidence_level": self.confidence_level,
            "lower_bound": ci_lower,
            "upper_bound": ci_upper,
            "excludes_zero": ci_lower > 0 or ci_upper < 0,
        }

        # 5. Effect size
        effect_size = self.calculate_effect_size(returns)
        results["effect_size"] = effect_size

        # 6. Overall significance determination
        significant_tests = [
            results["t_test"]["significant"],
            results["chi_square_test"]["significant"],
            results["permutation_test"]["significant"],
            results["bootstrap_ci"]["excludes_zero"],
        ]

        # Require majority of tests to be significant
        results["overall_significant"] = sum(significant_tests) >= 3
        results["significant_test_count"] = sum(significant_tests)
        results["total_tests"] = len(significant_tests)

        return results

    def _interpret_stability_score(self, stability_score: float) -> str:
        """Provide human-readable interpretation of stability score."""
        if stability_score >= 0.8:
            return "Highly stable across time periods"
        elif stability_score >= 0.6:
            return "Moderately stable with some variation"
        elif stability_score >= 0.4:
            return "Unstable with significant variation across periods"
        else:
            return "Highly unstable - pattern may be period-specific"
