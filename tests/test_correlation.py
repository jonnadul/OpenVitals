"""Tests for the pure-Python statistics helpers."""

from vitalframe.analysis.correlation import pearson, pearson_pvalue, slope, mean, median


def test_pearson_perfect_positive():
    assert abs(pearson([1, 2, 3, 4, 5], [2, 4, 6, 8, 10]) - 1.0) < 1e-9


def test_pearson_perfect_negative():
    assert abs(pearson([1, 2, 3], [3, 2, 1]) - (-1.0)) < 1e-9


def test_slope():
    assert abs(slope([0, 1, 2], [1, 3, 5]) - 2.0) < 1e-9


def test_mean_median():
    assert mean([1, 2, 3]) == 2.0
    assert median([3, 1, 2]) == 2.0
    assert median([1, 2, 3, 4]) == 2.5


def test_pearson_constant_y_is_nan():
    # zero variance in y -> undefined correlation
    assert pearson([1, 2, 3], [2, 2, 2]) != pearson([1, 2, 3], [2, 2, 2])


def test_pvalue_significant():
    # Strong but imperfect positive correlation -> significant (p < 0.05)
    xs = list(range(50))
    ys = [2 * x + (0.1 if i % 2 else -0.1) for i, x in enumerate(xs)]
    r = pearson(xs, ys)
    assert r < 1.0
    p = pearson_pvalue(r, len(xs))
    assert p < 0.05


def test_pvalue_perfect_is_nan():
    # Perfect correlation -> undefined p-value (no residual)
    assert pearson_pvalue(1.0, 10) != pearson_pvalue(1.0, 10)  # NaN != NaN
