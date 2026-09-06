"""分红归属核心算法纯函数测试（docs/03 §2）。"""
from app.models import Lot
from app.services.dividend_service import compute_eligible


def _lot(id, trade_date, direction, shares):
    return Lot(id=id, user_id=1, holding_id=1, trade_date=trade_date,
               direction=direction, shares=shares, price=0)


def test_two_batches_before_and_after_record_date():
    """原型中的茅台场景：登记日后的批次不参与分红。"""
    lots = [_lot(1, "2022-03-15", "buy", 60), _lot(2, "2023-09-20", "buy", 40)]
    remaining, eligible = compute_eligible(lots, "2023-06-27")
    assert eligible == 60
    assert remaining == {1: 60.0}


def test_fifo_sell_consumes_earliest_batch():
    """卖出按 FIFO 核销最早买入批次。"""
    lots = [_lot(1, "2022-03-15", "buy", 60),
            _lot(2, "2022-10-01", "buy", 40),
            _lot(3, "2023-05-01", "sell", 30)]
    remaining, eligible = compute_eligible(lots, "2024-06-27")
    assert remaining == {1: 30.0, 2: 40.0}
    assert eligible == 70


def test_sell_all_batches_leaves_zero():
    lots = [_lot(1, "2022-03-15", "buy", 60), _lot(2, "2023-01-01", "sell", 60)]
    remaining, eligible = compute_eligible(lots, "2024-06-27")
    assert eligible == 0
    assert remaining == {1: 0.0}  # FIFO 全额核销，余量为 0


def test_sell_after_record_date_ignored():
    """登记日之后的卖出不影响本次归属。"""
    lots = [_lot(1, "2022-03-15", "buy", 60), _lot(2, "2024-01-01", "sell", 30)]
    remaining, eligible = compute_eligible(lots, "2023-06-27")
    assert eligible == 60
    assert remaining == {1: 60.0}


def test_empty_lots_zero():
    remaining, eligible = compute_eligible([], "2024-06-27")
    assert eligible == 0 and remaining == {}
