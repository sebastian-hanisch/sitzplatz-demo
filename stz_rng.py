"""Ganzzahliger SplitMix64-Generator (Muster inst_int.py / au_scenario.py): plattformstabil, kein `random`."""

_MASK = (1 << 64) - 1


class SplitMix64:
    def __init__(self, seed):
        self.state = seed & _MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK
        return z ^ (z >> 31)

    def below(self, n):
        """Ganzzahl in 0..n-1 (Modulo-Verzerrung bei n <= 10**6 unter 1e-13)."""
        return self.next() % n

    def uniform(self):
        return (self.next() >> 11) / 9007199254740992.0

    def poisson(self, lam):
        """Knuth; für lam <= 30 (exp(-lam) bleibt darstellbar). Verbraucht eine variable Zahl Ziehungen."""
        limit = _exp_neg(lam)
        k, prod = 0, 1.0
        while True:
            prod *= self.uniform()
            if prod <= limit:
                return k
            k += 1


def _exp_neg(lam):
    import math
    return math.exp(-lam)
