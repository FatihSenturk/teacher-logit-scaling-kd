"""One definition of "+/- sd" for the whole campaign.

WHY THIS FILE EXISTS. Several analysis scripts were originally written with
`statistics.pstdev` -- the POPULATION standard deviation, which divides by n. Our seeds are a
SAMPLE drawn from the distribution of training runs, not the population of all possible runs,
so the correct estimator is the sample sd, which divides by n-1 (Bessel's correction).

The difference is not cosmetic at the n we actually run:

    n = 2  ->  pstdev = sample_sd * sqrt(1/2) = 0.707 * sample_sd   (29% UNDERSTATED)
    n = 3  ->  pstdev = sample_sd * sqrt(2/3) = 0.816 * sample_sd   (18% UNDERSTATED)
    n = 5  ->  pstdev = sample_sd * sqrt(4/5) = 0.894 * sample_sd   (11% UNDERSTATED)

Understating the error bar is the dangerous direction: it makes every effect look more
separated from noise than it is. Reviewers of a Q1/Q2 submission check this.

CONVENTION (binding for every table and figure in the paper):
    error bars, "+/- x" in text, and every *_sd field in every JSON artifact
    = SAMPLE standard deviation (n-1), computed over SEEDS.
    n is always reported alongside. n=1 yields sd = 0.0 by definition here (not an error),
    and any n=1 cell must be labelled as such rather than shown with a fake +/- 0.0000.

`SD_CONVENTION` is written into every JSON artifact so a file can be audited without
re-reading the script that produced it.
"""

import statistics as _st

SD_CONVENTION = "sample sd (n-1, Bessel-corrected), computed over seeds"


def sample_sd(values):
    """Sample standard deviation (n-1). Returns 0.0 for n<2 instead of raising.

    Deliberately NOT `statistics.pstdev`. See the module docstring for why, and for the
    magnitude of the error that substitution causes at n=2 and n=3.
    """
    values = list(values)
    return _st.stdev(values) if len(values) > 1 else 0.0


def mean_sd_n(values):
    """(mean, sample sd, n) -- the triple every table cell in the paper reports."""
    values = list(values)
    if not values:
        return None, None, 0
    return _st.mean(values), sample_sd(values), len(values)


def fmt(values, digits=4, unit=""):
    """'mean +/- sd (n=k)' at a fixed precision; 'mean (n=1)' when there is no sd to show."""
    m, s, n = mean_sd_n(values)
    if n == 0:
        return "n/a"
    if n == 1:
        return f"{m:.{digits}f}{unit} (n=1)"
    return f"{m:.{digits}f} +/- {s:.{digits}f}{unit} (n={n})"


if __name__ == "__main__":
    import math
    for n in (2, 3, 5):
        xs = list(range(n))
        p, s = _st.pstdev(xs), sample_sd(xs)
        print(f"n={n}: pstdev {p:.6f}  sample_sd {s:.6f}  ratio {p / s:.4f} "
              f"(= sqrt({n - 1}/{n}) = {math.sqrt((n - 1) / n):.4f}), "
              f"understatement {100 * (1 - p / s):.1f}%")
