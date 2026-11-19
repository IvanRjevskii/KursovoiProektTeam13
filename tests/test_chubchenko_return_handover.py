"""Тесты компонента return_comp (Чубченко Д. В.)."""
import unittest
from collections.abc import Sequence

from chubchenko_return_handover import (
    HandoverMode, HandoverStrategySelector, ReturnBatch, ReturnHandoverService,
    ReturnItem, SelfHandoverStrategy, WarehouseScanStrategy,
)


class FakeWarehouse:
    def __init__(self) -> None:
        self.calls: list[tuple[int, tuple[str, ...], HandoverMode]] = []

    def confirm_returns(self, shift_id: int, barcodes: Sequence[str], mode: HandoverMode) -> None:
        self.calls.append((shift_id, tuple(barcodes), mode))


def batch(n: int, shift: int = 1) -> ReturnBatch:
    return ReturnBatch(shift, 7, tuple(ReturnItem(f"R{i:05d}", 1000 + i % 4, "14-02") for i in range(n)))


class SelectorTest(unittest.TestCase):
    def test_threshold_250(self) -> None:
        s = HandoverStrategySelector()
        self.assertIsInstance(s.select(batch(250)), SelfHandoverStrategy)
        self.assertIsInstance(s.select(batch(251)), WarehouseScanStrategy)

    def test_custom_threshold(self) -> None:
        self.assertIsInstance(HandoverStrategySelector(10).select(batch(11)), WarehouseScanStrategy)


class StrategyTest(unittest.TestCase):
    def test_self_handover_reports_missing_and_surplus(self) -> None:
        b = batch(5)
        scanned = ["R00000", "R00001", "R00001", "X99999"]
        r = SelfHandoverStrategy().accept(b, scanned)
        self.assertEqual(r.accepted, ("R00000", "R00001"))
        self.assertEqual(r.surplus, ("X99999",))
        self.assertEqual(len(r.missing), 3)
        self.assertFalse(r.is_clean)

    def test_warehouse_scan_counts_whole_batch(self) -> None:
        b = batch(300)
        r = WarehouseScanStrategy().accept(b, ["R00010"])
        self.assertEqual(len(r.accepted), 300)
        self.assertTrue(r.is_clean)

    def test_warehouse_scan_foreign_item_blocks_autocount(self) -> None:
        r = WarehouseScanStrategy().accept(batch(300), ["ZZZ"])
        self.assertEqual(r.accepted, ())
        self.assertEqual(r.surplus, ("ZZZ",))

    def test_warehouse_scan_requires_one_scan(self) -> None:
        with self.assertRaises(ValueError):
            WarehouseScanStrategy().accept(batch(300), [])


class ServiceTest(unittest.TestCase):
    def test_context_selects_strategy_and_confirms_in_wms(self) -> None:
        wms = FakeWarehouse()
        service = ReturnHandoverService(wms, HandoverStrategySelector())
        b = batch(3, shift=42)
        r = service.hand_over(b, [i.barcode for i in b.items])
        self.assertTrue(r.is_clean)
        self.assertEqual(wms.calls[0][0], 42)
        self.assertEqual(wms.calls[0][2], HandoverMode.SELF_HANDOVER)

    def test_explicit_strategy_overrides_selector(self) -> None:
        wms = FakeWarehouse()
        service = ReturnHandoverService(wms, HandoverStrategySelector())
        service.set_strategy(SelfHandoverStrategy())
        r = service.hand_over(batch(400), ["R00001"])
        self.assertEqual(r.mode, HandoverMode.SELF_HANDOVER)
        self.assertEqual(len(r.missing), 399)

    def test_nothing_accepted_nothing_sent(self) -> None:
        wms = FakeWarehouse()
        ReturnHandoverService(wms, HandoverStrategySelector()).hand_over(batch(2), [])
        self.assertEqual(wms.calls, [])


if __name__ == "__main__":
    unittest.main()
