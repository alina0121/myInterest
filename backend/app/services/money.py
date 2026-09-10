"""金额工具：统一 Decimal 计算与四舍五入（每股 4 位、金额 2 位）。

为什么全程 Decimal：float 是二进制近似值（0.1 + 0.2 != 0.3），
金额累加/算税会出现 12.340000000000001 这类尾差，对账时对不上。
落库前统一在 Python 端四舍五入（docs/02 金额约定）。
"""
from decimal import ROUND_HALF_UP, Decimal

D2 = Decimal("0.01")    # 金额精度：2 位小数（元）
D4 = Decimal("0.0001")  # 每股分红精度：4 位小数（美股 dps 常到 4 位）


def d(x) -> Decimal:
    """转 Decimal。必须经 str() 中转：Decimal(0.1) 会带入 float 的二进制误差，
    而 Decimal("0.1") 是精确值。"""
    return Decimal(str(x))


def r2(x) -> float:
    """四舍五入到 2 位小数（金额口径），ROUND_HALF_UP 即数学上的四舍五入。"""
    return float(d(x).quantize(D2, rounding=ROUND_HALF_UP))


def r4(x) -> float:
    """四舍五入到 4 位小数（每股分红 dps 口径）。"""
    return float(d(x).quantize(D4, rounding=ROUND_HALF_UP))
