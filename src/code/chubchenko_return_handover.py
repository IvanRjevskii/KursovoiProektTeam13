"""Компонент returns_comp (Backend API): приёмка возвратов на складе.

Автор: Чубченко Д. В. Команда 13, лабораторная работа № 3.
Паттерн «Стратегия»: способ приёмки возвратов подменяется без изменения контекста.
- более 250 позиций — массовая приёмка: работник склада сканирует одну позицию,
  остальные засчитываются автоматически;
- 250 и меньше — самосдача: водитель сканирует каждую позицию сам.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AcceptanceMode(str, Enum):
    BULK = "bulk"
    SELF = "self"


@dataclass(frozen=True)
class ReturnItem:
    barcode: str
    pvz_code: int


@dataclass(frozen=True)
class AcceptanceResult:
    mode: AcceptanceMode
    accepted: list[str]
    missing: list[str]
    accepted_at: datetime = field(default_factory=datetime.now)

    @property
    def is_complete(self) -> bool:
        return not self.missing


class ReturnsAcceptanceStrategy(ABC):
    """Единый контракт для всех способов приёмки возвратов."""

    mode: AcceptanceMode

    @abstractmethod
    def accept(self, items: list[ReturnItem], scanned: set[str]) -> AcceptanceResult:
        """Сверяет ожидаемые возвраты с отсканированными штрихкодами."""


class BulkAcceptanceStrategy(ReturnsAcceptanceStrategy):
    """Массовая приёмка: достаточно одного скана работника склада."""

    mode = AcceptanceMode.BULK

    def accept(self, items: list[ReturnItem], scanned: set[str]) -> AcceptanceResult:
        barcodes = [item.barcode for item in items]
        if scanned & set(barcodes):
            return AcceptanceResult(self.mode, accepted=barcodes, missing=[])
        return AcceptanceResult(self.mode, accepted=[], missing=barcodes)


class SelfAcceptanceStrategy(ReturnsAcceptanceStrategy):
    """Самосдача: засчитывается только то, что водитель отсканировал сам."""

    mode = AcceptanceMode.SELF

    def accept(self, items: list[ReturnItem], scanned: set[str]) -> AcceptanceResult:
        accepted = [item.barcode for item in items if item.barcode in scanned]
        missing = [item.barcode for item in items if item.barcode not in scanned]
        return AcceptanceResult(self.mode, accepted=accepted, missing=missing)


class ReturnsAcceptanceService:
    """Контекст: хранит текущую стратегию и делегирует ей приёмку."""

    BULK_THRESHOLD: int = 250

    def __init__(self, strategy: ReturnsAcceptanceStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> ReturnsAcceptanceStrategy:
        return self._strategy

    def set_strategy(self, strategy: ReturnsAcceptanceStrategy) -> None:
        self._strategy = strategy

    def choose_strategy(self, items_count: int) -> None:
        """Выбирает способ приёмки по количеству позиций."""
        if items_count > self.BULK_THRESHOLD:
            self.set_strategy(BulkAcceptanceStrategy())
        else:
            self.set_strategy(SelfAcceptanceStrategy())

    def accept_returns(self, items: list[ReturnItem], scanned: set[str]) -> AcceptanceResult:
        self.choose_strategy(len(items))
        return self._strategy.accept(items, scanned)


if __name__ == "__main__":
    service = ReturnsAcceptanceService(SelfAcceptanceStrategy())

    small = [ReturnItem(f"R{i:04d}", pvz_code=101) for i in range(40)]
    result = service.accept_returns(small, scanned={f"R{i:04d}" for i in range(38)})
    print(result.mode.value, len(result.accepted), "принято,", len(result.missing), "не хватает")

    big = [ReturnItem(f"R{i:04d}", pvz_code=102) for i in range(300)]
    result = service.accept_returns(big, scanned={"R0007"})
    print(result.mode.value, len(result.accepted), "принято, приёмка завершена:", result.is_complete)
