"""
Pure numerics for the Riemann zeta function. No I/O, no model calls, no state.

Everything here is a plain function from parameters to numbers, so every result
is reproducible from the run record alone: same inputs + same mpmath version =
same output. That property is what lets the gate accept a COMPUTED card.

Conventions
    s = sigma + i t
    rho = 1/2 + i gamma  (a nontrivial zero, under RH)
    theta(t)             Riemann-Siegel theta
    Z(t)                 Hardy Z: real-valued on the critical line, and
                         |Z(t)| = |zeta(1/2 + it)|, so its sign changes ARE
                         zeros on the line. This is the workhorse.
    N(T)                 number of zeros with 0 < gamma <= T
    S(T)                 N(T) - (theta(T)/pi + 1)   — the fluctuating part
    psi(x)               Chebyshev's function, sum of Lambda(n) for n <= x
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Iterable

import mpmath as mp

EULER_GAMMA = 0.5772156649015328606

# --------------------------------------------------------------------------- #
# Core functions on the critical line
# --------------------------------------------------------------------------- #


def theta(t: float, dps: int = 25) -> float:
    """Riemann-Siegel theta: arg Gamma(1/4 + it/2) - (t/2) log pi."""
    with mp.workdps(dps):
        return float(mp.siegeltheta(mp.mpf(t)))


def Z(t: float, dps: int = 25) -> float:
    """Hardy Z(t) = e^{i theta(t)} zeta(1/2 + it). Real; zeros on the line."""
    with mp.workdps(dps):
        return float(mp.siegelz(mp.mpf(t)))


def zeta(s: complex, dps: int = 25) -> complex:
    with mp.workdps(dps):
        return complex(mp.zeta(mp.mpc(s.real, s.imag)))


def zeta_zero(n: int, dps: int = 25) -> float:
    """Imaginary part of the n-th nontrivial zero (n >= 1)."""
    with mp.workdps(dps):
        return float(mp.im(mp.zetazero(n)))


def zeta_zeros(n: int, dps: int = 25) -> list[float]:
    with mp.workdps(dps):
        return [float(mp.im(mp.zetazero(k))) for k in range(1, n + 1)]


def functional_equation_residual(s: complex, dps: int = 30) -> float:
    """
    |zeta(s) - chi(s) zeta(1-s)| with chi(s) = 2^s pi^{s-1} sin(pi s/2) Gamma(1-s).
    A self-test: this should be at the noise floor. If it is not, the precision
    settings are wrong and nothing else in this module should be trusted.
    """
    with mp.workdps(dps):
        S = mp.mpc(s.real, s.imag)
        chi = 2 ** S * mp.pi ** (S - 1) * mp.sin(mp.pi * S / 2) * mp.gamma(1 - S)
        return float(abs(mp.zeta(S) - chi * mp.zeta(1 - S)))


# --------------------------------------------------------------------------- #
# Zero hunting by sign change of Z
# --------------------------------------------------------------------------- #
@dataclass
class SignChange:
    a: float
    b: float
    root: float


def sign_changes(t0: float, t1: float, step: float, dps: int = 20
                 ) -> tuple[list[SignChange], list[tuple[float, float]]]:
    """
    Scan Z on [t0, t1] and bisect every sign change. Returns (roots, samples).

    The scan step matters: zeros near height T are spaced about 2*pi/log(T/2pi)
    apart, so a step larger than that will miss pairs. `recommended_step` below
    gives a safe default.
    """
    ts = []
    # ceil, not floor: with floor the last sample lands short of t1 and any
    # zero in that final sliver is silently missed — which undercounts N(T)
    # at exactly the place the counting experiment cares about.
    n = max(int(math.ceil((t1 - t0) / step)), 1)
    prev_t = t0
    prev_z = Z(t0, dps)
    ts.append((prev_t, prev_z))
    roots: list[SignChange] = []
    for i in range(1, n + 1):
        t = min(t0 + i * step, t1)
        z = Z(t, dps)
        ts.append((t, z))
        if prev_z == 0.0:
            roots.append(SignChange(prev_t, prev_t, prev_t))
        elif (prev_z < 0) != (z < 0):
            r = _bisect(lambda x: Z(x, dps), prev_t, t)
            roots.append(SignChange(prev_t, t, r))
        prev_t, prev_z = t, z
        if t >= t1:
            break
    return roots, ts


def recommended_step(t: float, safety: float = 8.0) -> float:
    """A step `safety` times finer than the mean zero spacing at height t."""
    t = max(t, 10.0)
    spacing = 2 * math.pi / math.log(t / (2 * math.pi))
    return spacing / safety


def _bisect(f: Callable[[float], float], a: float, b: float,
            tol: float = 1e-11, itmax: int = 200) -> float:
    fa, fb = f(a), f(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    for _ in range(itmax):
        m = 0.5 * (a + b)
        fm = f(m)
        if fm == 0 or (b - a) < tol:
            return m
        if (fa < 0) != (fm < 0):
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


# --------------------------------------------------------------------------- #
# Counting: N(T), S(T), and the RH check on an interval
# --------------------------------------------------------------------------- #
def N_smooth(T: float, dps: int = 25) -> float:
    """theta(T)/pi + 1 — the smooth main term of the counting function."""
    return theta(T, dps) / math.pi + 1.0


def S(T: float, actual_count: int, dps: int = 25) -> float:
    """S(T) = N(T) - (theta(T)/pi + 1). Needs the true count on [0, T]."""
    return actual_count - N_smooth(T, dps)


def smooth_count_difference(T0: float, T1: float, dps: int = 25) -> float:
    """
    (theta(T1) - theta(T0)) / pi — the SMOOTH part of the number of zeros with
    T0 < gamma <= T1. Deliberately not called a zero count: the true count is
    this plus S(T1) - S(T0), and the whole point of the exercise is to measure
    that difference against the zeros we actually found by sign change.
    """
    return (theta(T1, dps) - theta(T0, dps)) / math.pi


# --------------------------------------------------------------------------- #
# Gram points, Gram's law, Rosser's rule
# --------------------------------------------------------------------------- #
def gram_point(n: int, dps: int = 25) -> float:
    """
    g_n: the unique t > 7 with theta(t) = n*pi  (n >= -1).
    Solved by Newton from an asymptotic seed.
    """
    with mp.workdps(dps):
        target = mp.pi * n
        # asymptotic seed: theta(t) ~ (t/2)log(t/2pi) - t/2 - pi/8
        t = mp.mpf(2 * mp.pi * mp.e * (n + 1.125)) if n >= 0 else mp.mpf(9.0)
        t = max(t, mp.mpf(8.0))
        for _ in range(80):
            f = mp.siegeltheta(t) - target
            d = mp.diff(mp.siegeltheta, t)
            if d == 0:
                break
            step = f / d
            t = t - step
            if abs(step) < mp.mpf(10) ** (-dps + 5):
                break
        return float(t)


def gram_analysis(n_start: int, n_end: int, dps: int = 20) -> dict:
    """
    Gram's law: Z alternates in sign at consecutive Gram points, i.e. each
    Gram interval [g_n, g_{n+1}) holds exactly one zero. It is a *tendency*,
    not a theorem — it fails infinitely often, and the failures are where the
    interesting behaviour lives (Lehmer pairs, Rosser-rule exceptions).

    A "good" Gram point has (-1)^n Z(g_n) > 0.
    """
    pts, good, bad = [], 0, 0
    for n in range(n_start, n_end + 1):
        g = gram_point(n, dps)
        z = Z(g, dps)
        is_good = ((-1) ** n) * z > 0
        good += is_good
        bad += (not is_good)
        pts.append({"n": n, "g": g, "Z": z, "good": bool(is_good)})

    # zeros per Gram interval — Rosser's rule looks at blocks of intervals
    intervals = []
    for i in range(len(pts) - 1):
        a, b = pts[i]["g"], pts[i + 1]["g"]
        roots, _ = sign_changes(a, b, recommended_step(b, 12.0), dps)
        intervals.append({"n": pts[i]["n"], "a": a, "b": b,
                          "zeros": len(roots),
                          "roots": [r.root for r in roots]})
    violations = [iv for iv in intervals if iv["zeros"] != 1]
    return {"points": pts, "intervals": intervals,
            "good_points": good, "bad_points": bad,
            "gram_law_violations": len(violations),
            "violation_detail": violations[:50]}


def lehmer_pairs(zeros: list[float], factor: float = 0.25) -> list[dict]:
    """
    Unusually close consecutive zeros — spacing below `factor` times the local
    mean. These are the near-counterexamples: a pair that merged would put a
    zero off the line. Lehmer's 1956 pair near 7005 is the classic.
    """
    out = []
    for i in range(len(zeros) - 1):
        g0, g1 = zeros[i], zeros[i + 1]
        mean = 2 * math.pi / math.log(max(g0, 10.0) / (2 * math.pi))
        d = g1 - g0
        if d < factor * mean:
            out.append({"i": i + 1, "gamma_1": g0, "gamma_2": g1,
                        "gap": d, "gap_over_mean": d / mean})
    return out


def normalized_spacings(zeros: list[float]) -> list[float]:
    """
    delta_n = (gamma_{n+1} - gamma_n) * log(gamma_n / 2pi) / (2pi).
    Unit mean by construction. Montgomery's pair-correlation conjecture says
    these follow GUE statistics — the bridge from number theory to random
    matrices, and the reason Hilbert-Polya is taken seriously.
    """
    out = []
    for i in range(len(zeros) - 1):
        g = zeros[i]
        if g <= 2 * math.pi:
            continue
        out.append((zeros[i + 1] - g) * math.log(g / (2 * math.pi)) / (2 * math.pi))
    return out


def gue_wigner_surmise(s: float) -> float:
    """GUE nearest-neighbour density: (32/pi^2) s^2 exp(-4 s^2 / pi)."""
    return (32.0 / math.pi ** 2) * s * s * math.exp(-4.0 * s * s / math.pi)


def poisson_density(s: float) -> float:
    """exp(-s): what you would see if the zeros were random and uncorrelated."""
    return math.exp(-s)


# --------------------------------------------------------------------------- #
# The explicit formula — where the primes come out of the zeros
# --------------------------------------------------------------------------- #
def von_mangoldt_psi(x: float) -> float:
    """psi(x) = sum_{p^k <= x} log p, computed directly."""
    n = int(x)
    if n < 2:
        return 0.0
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    total = 0.0
    for p in range(2, n + 1):
        if sieve[p]:
            for m in range(p * p, n + 1, p):
                sieve[m] = 0
            lp = math.log(p)
            pk = p
            while pk <= n:
                total += lp
                pk *= p
    return total


def psi_explicit(x: float, gammas: Iterable[float]) -> dict:
    """
    psi(x) = x - sum_rho x^rho/rho - log(2pi) - (1/2) log(1 - x^-2)

    Summing over conjugate pairs rho = 1/2 +- i gamma:
        x^rho/rho + conj = 2 sqrt(x) cos(gamma log x - arg(rho)) / |rho|

    Each zero contributes one wave. Add enough of them and the smooth curve x
    turns into a staircase that jumps exactly at the prime powers. This is the
    single most useful thing to look at while learning the subject.
    """
    logx = math.log(x)
    sx = math.sqrt(x)
    main = x - math.log(2 * math.pi) - 0.5 * math.log(1 - x ** -2)
    total = main
    partials = []
    for g in gammas:
        rho_abs = math.hypot(0.5, g)
        arg_rho = math.atan2(g, 0.5)
        total -= 2.0 * sx * math.cos(g * logx - arg_rho) / rho_abs
        partials.append(total)
    return {"x": x, "main_term": main, "psi_approx": total,
            "partials": partials}


# --------------------------------------------------------------------------- #
# Prime counting: pi(x) vs li(x) vs Riemann's R(x)
# --------------------------------------------------------------------------- #
def prime_pi(x: int) -> int:
    if x < 2:
        return 0
    sieve = bytearray([1]) * (x + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, int(x ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytearray(len(sieve[p * p::p]))
    return sum(sieve)


def mobius_list(n: int) -> list[int]:
    """mu(k) for k = 0..n by a linear sieve."""
    mu = [1] * (n + 1)
    primes = []
    is_comp = bytearray(n + 1)
    mu[0] = 0
    for i in range(2, n + 1):
        if not is_comp[i]:
            primes.append(i)
            mu[i] = -1
        for p in primes:
            if i * p > n:
                break
            is_comp[i * p] = 1
            if i % p == 0:
                mu[i * p] = 0
                break
            mu[i * p] = -mu[i]
    return mu


def riemann_R(x: float, terms: int = 40, dps: int = 25) -> float:
    """R(x) = sum_{k>=1} mu(k)/k * li(x^{1/k}) — a far better fit than li(x)."""
    mu = mobius_list(terms)
    with mp.workdps(dps):
        tot = mp.mpf(0)
        for k in range(1, terms + 1):
            if mu[k] == 0:
                continue
            tot += mp.mpf(mu[k]) / k * mp.li(mp.mpf(x) ** (mp.mpf(1) / k))
        return float(tot)


def log_integral(x: float, dps: int = 25) -> float:
    with mp.workdps(dps):
        return float(mp.li(mp.mpf(x)))


# --------------------------------------------------------------------------- #
# RH equivalences you can actually compute
# --------------------------------------------------------------------------- #
def divisor_sigma(n: int) -> int:
    tot, i = 0, 1
    while i * i <= n:
        if n % i == 0:
            tot += i
            j = n // i
            if j != i:
                tot += j
        i += 1
    return tot


def robin_check(n_max: int, n_min: int = 5041) -> dict:
    """
    Robin's criterion (1984): RH holds  <=>  sigma(n) < e^gamma n log log n
    for every n > 5040. A single violation above 5040 would disprove RH — so
    this is a genuine, if hopeless, search. What it is really good for is
    seeing how tight the inequality is: the ratio hovers just under 1 forever.
    """
    egam = math.exp(EULER_GAMMA)
    worst = {"n": 0, "ratio": 0.0}
    violations = []
    samples = []
    for n in range(max(n_min, 3), n_max + 1):
        lln = math.log(math.log(n))
        if lln <= 0:
            continue
        bound = egam * n * lln
        s = divisor_sigma(n)
        ratio = s / bound
        if ratio > worst["ratio"]:
            worst = {"n": n, "ratio": ratio, "sigma": s, "bound": bound}
        if ratio >= 1.0:
            violations.append({"n": n, "sigma": s, "bound": bound, "ratio": ratio})
        if n % max(1, (n_max - n_min) // 400) == 0:
            samples.append((n, ratio))
    return {"n_min": n_min, "n_max": n_max, "worst": worst,
            "violations": violations, "samples": samples,
            "note": ("nijedno kršenje iznad 5040 nije poznato; jedno bi oborilo RH")}


def mertens(x: int) -> dict:
    """
    M(x) = sum_{n<=x} mu(n). Mertens conjectured |M(x)| < sqrt(x); Odlyzko and
    te Riele disproved it in 1985 (without exhibiting a counterexample — the
    smallest one is astronomically large). |M(x)| = O(x^{1/2+eps}) is still
    equivalent to RH. Numerically M(x) stays small, which is exactly why the
    conjecture looked safe for a century.
    """
    mu = mobius_list(x)
    tot, series, worst = 0, [], 0.0
    stride = max(1, x // 500)
    for n in range(1, x + 1):
        tot += mu[n]
        # n=1 gives |M|/sqrt(n) = 1 trivially; the ratio only says something
        # once there are enough terms for cancellation to be meaningful.
        r = abs(tot) / math.sqrt(n)
        if n >= 100:
            worst = max(worst, r)
        if n % stride == 0 or n == x:
            series.append((n, tot, r))
    return {"x": x, "M": tot, "max_ratio": worst, "series": series}
