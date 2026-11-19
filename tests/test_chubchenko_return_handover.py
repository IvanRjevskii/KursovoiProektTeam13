"""Модульные тесты компонента приёмки возвратов (Чубченко Д. В., ЛР3)."""
import unittest

from chubchenko_return_handover import (
    AcceptanceMode,
    BulkAcceptanceStrategy,
    ReturnItem,
    ReturnsAcceptanceService,
    SelfAcceptanceStrategy,
)


def make_items(count: int, pvz: int = 101) -> list[ReturnItem]:
    return [ReturnItem(barcode=f"R{i:04d}", pvz_code=pvz) for i in range(count)]


class ReturnsAcceptanceTest(unittest.TestCase):
    def test_self_acceptance_for_up_to_250_items(self) -> None:
        service = ReturnsAcceptanceService(BulkAcceptanceStrategy())
        items = make_items(250)
        scanned = {item.barcode for item in items[:-2]}
        result = service.accept_returns(items, scanned)
        self.assertEqual(result.mode, AcceptanceMode.SELF)
        self.assertEqual(len(result.accepted), 248)
        self.assertEqual(len(result.missing), 2)
        self.assertFalse(result.is_complete)

    def test_bulk_acceptance_for_over_250_items_with_single_scan(self) -> None:
        service = ReturnsAcceptanceService(SelfAcceptanceStrategy())
        items = make_items(251)
        result = service.accept_returns(items, scanned={"R0010"})
        self.assertEqual(result.mode, AcceptanceMode.BULK)
        self.assertEqual(len(result.accepted), 251)
        self.assertEqual(result.missing, [])
        self.assertTrue(result.is_complete)

    def test_bulk_acceptance_rejects_foreign_barcode(self) -> None:
        strategy = BulkAcceptanceStrategy()
        items = make_items(300)
        result = strategy.accept(items, scanned={"FOREIGN-999"})
        self.assertEqual(result.accepted, [])
        self.assertEqual(len(result.missing), 300)
        self.assertFalse(result.is_complete)

    def test_set_strategy_switches_algorithm(self) -> None:
        service = ReturnsAcceptanceService(SelfAcceptanceStrategy())
        service.set_strategy(BulkAcceptanceStrategy())
        self.assertIsInstance(service.strategy, BulkAcceptanceStrategy)


if __name__ == "__main__":
    unittest.main()
