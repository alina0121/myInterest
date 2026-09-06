"""金额工具：统一 Decimal 计算与四舍五入（每股 4 位、金额 2 位）。"""
from decimal import ROUND_HALF_UP, Decimal

D2 = Decimal("0.01")
D4 = Decimal("0.0001")


def d(x) -> Decimal:
    return Decimal(str(x))


def r2(x) -> float:
    return float(d(x).quantize(D2, rounding=ROUND_HALF_UP))


def r4(x) -> float:
    return float(d(x).quantize(D4, rounding=ROUND_HALF_UP))
