from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from tokenizer import Token


@dataclass(frozen=True)
class HalsteadMetrics:
    n1: int
    n2: int
    N1: int
    N2: int
    f1j: dict[str, int]
    f2i: dict[str, int]

    @property
    def vocabulary(self) -> int:
        return self.n1 + self.n2

    @property
    def length(self) -> int:
        return self.N1 + self.N2

    @property
    def volume(self) -> float:
        n = self.vocabulary
        return self.length * math.log2(n) if n > 1 else 0.0


def compute_metrics(tokens: list[Token]) -> HalsteadMetrics:
    operators = Counter(t.value for t in tokens if t.kind == "operator")
    operands = Counter(t.value for t in tokens if t.kind == "operand")

    return HalsteadMetrics(
        n1=len(operators),
        n2=len(operands),
        N1=sum(operators.values()),
        N2=sum(operands.values()),
        f1j=dict(operators),
        f2i=dict(operands),
    )
