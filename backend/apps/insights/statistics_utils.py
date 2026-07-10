"""Small, dependency-free statistics helpers (no numpy/scipy in
requirements.txt) backing the AI Insights endpoints. Plain least-squares
regression and mean/stdev on real historical data -- not a call to an
external LLM, which would need credentials this project doesn't have and
couldn't be verified without them."""

from decimal import Decimal
from statistics import mean, pstdev


def linear_regression(y_values: list[float]) -> tuple[float, float]:
    """Ordinary least squares for y = slope*x + intercept, x = 0..n-1."""
    n = len(y_values)
    if n < 2:
        return 0.0, (y_values[0] if y_values else 0.0)

    x_values = list(range(n))
    x_mean = mean(x_values)
    y_mean = mean(y_values)

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator == 0:
        return 0.0, y_mean

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


def forecast_series(history: list[float], periods: int) -> list[float]:
    """Projects `periods` values forward from a linear fit of `history`,
    clipped at zero since demand can't be negative."""
    slope, intercept = linear_regression(history)
    n = len(history)
    return [max(0.0, slope * (n + i) + intercept) for i in range(periods)]


def mean_and_stdev(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0
    return mean(values), pstdev(values)


def to_float(value) -> float:
    return float(value) if isinstance(value, Decimal) else float(value or 0)
