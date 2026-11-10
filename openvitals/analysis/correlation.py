"""Statistical helpers for OpenVitals analysis (pure-Python, no SciPy)."""

from __future__ import annotations

from typing import List, Tuple


def mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def median(xs: List[float]) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def pearson(xs: List[float], ys: List[float]) -> float:
    """Pearson correlation coefficient. Returns NaN if undefined."""
    n = len(xs)
    if n != len(ys) or n < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    if dx == 0 or dy == 0:
        return float("nan")
    return num / (dx * dy)


def _betacf(a: float, b: float, x: float, max_iter: int = 200) -> float:
    """Continued-fraction for the incomplete beta function (Numerical Recipes)."""
    fpmin = 1e-30
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < fpmin:
        d = fpmin
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < fpmin:
            d = fpmin
        c = 1.0 + aa / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < 1e-8:
            break
    return h


def _betai(a: float, b: float, x: float) -> float:
    """Incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = (
        _lgamma(a + b) - _lgamma(a) - _lgamma(b)
        + a * __import__("math").log(x) + b * __import__("math").log(1.0 - x)
    )
    bt = __import__("math").exp(lbeta)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _lgamma(x: float) -> float:
    return __import__("math").lgamma(x)


def pearson_pvalue(r: float, n: int) -> float:
    """Two-sided p-value for Pearson r with n samples (Student-t)."""
    if n < 3 or abs(r) >= 1.0:
        return float("nan")
    t = r * ((n - 2) / (1 - r * r)) ** 0.5
    # p = 2 * (1 - t_cdf(|t|, n-2)); use incomplete beta identity
    a = n / 2.0 - 1.0
    x = n / (n + t * t)
    return _betai(a, 0.5, x)


def slope(xs: List[float], ys: List[float]) -> float:
    """Ordinary least-squares slope of y vs x (x assumed evenly spaced)."""
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else float("nan")


def t_critical_two_sided(n: int, alpha: float = 0.05) -> float:
    """Approximate two-sided t critical value for df=n-2 (for significance flags)."""
    # Small-n exact values for common df; falls back to 1.96 for large n.
    table = {1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36,
             8: 2.31, 9: 2.26, 10: 2.23, 15: 2.13, 20: 2.09, 30: 2.04, 60: 2.00}
    df = max(1, n - 2)
    if df in table:
        return table[df]
    return 1.96
