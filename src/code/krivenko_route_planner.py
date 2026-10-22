"""Компонент route_planner (сервис маршрутизации): порядок объезда ПВЗ в волне.

Автор: Кривенко И. Р. Команда 13, лабораторная работа № 3.
Паттерн «Стратегия»: алгоритм построения маршрута подменяется без изменения контекста:
- по номерам сеток — порядок, в котором сетки стоят на складе;
- ближайший сосед — каждый раз едем к ближайшему непосещённому ПВЗ;
- ближайший сосед с улучшением 2-opt — убирает пересечения в маршруте.
Расстояния стратегии получают через абстракцию DistanceSource: в сервисе это матрица
расстояний по дорогам от компонента matrix_builder, запасной вариант — расстояние по прямой.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt


@dataclass(frozen=True)
class Point:
    code: int
    lat: float
    lon: float
    grid: str = ""  # номер сетки «ряд-место»


class DistanceSource(ABC):
    """Единый контракт получения расстояния между двумя точками."""

    @abstractmethod
    def km(self, a: Point, b: Point) -> float:
        """Возвращает расстояние от a до b в километрах."""


class DistanceMatrix(DistanceSource):
    """Расстояния по дорогам из матрицы, которую собирает компонент matrix_builder."""

    def __init__(self, values: dict[tuple[int, int], float]) -> None:
        self._values = dict(values)

    def km(self, a: Point, b: Point) -> float:
        return self._values[(a.code, b.code)]


class StraightLineDistance(DistanceSource):
    """Расстояние по прямой (формула гаверсинусов): запасной вариант и тесты."""

    def km(self, a: Point, b: Point) -> float:
        dlat, dlon = radians(b.lat - a.lat), radians(b.lon - a.lon)
        h = sin(dlat / 2) ** 2 + cos(radians(a.lat)) * cos(radians(b.lat)) * sin(dlon / 2) ** 2
        return 2 * 6371 * asin(sqrt(h))


def route_length(depot: Point, route: list[Point], dist: DistanceSource) -> float:
    path = [depot, *route]
    return sum(dist.km(path[i], path[i + 1]) for i in range(len(path) - 1))


class RouteBuildingStrategy(ABC):
    """Единый контракт алгоритма построения маршрута."""

    @abstractmethod
    def build(self, depot: Point, stops: list[Point], dist: DistanceSource) -> list[Point]:
        """Возвращает ПВЗ в порядке объезда."""


class GridOrderStrategy(RouteBuildingStrategy):
    def build(self, depot: Point, stops: list[Point], dist: DistanceSource) -> list[Point]:
        return sorted(stops, key=lambda p: p.grid)


class NearestNeighborStrategy(RouteBuildingStrategy):
    def build(self, depot: Point, stops: list[Point], dist: DistanceSource) -> list[Point]:
        left: list[Point] = list(stops)
        route: list[Point] = []
        current = depot
        while left:
            nearest = min(left, key=lambda p: dist.km(current, p))
            route.append(nearest)
            left.remove(nearest)
            current = nearest
        return route


class TwoOptStrategy(RouteBuildingStrategy):
    def __init__(self, start: RouteBuildingStrategy | None = None) -> None:
        self._start = start or NearestNeighborStrategy()

    def build(self, depot: Point, stops: list[Point], dist: DistanceSource) -> list[Point]:
        best = self._start.build(depot, stops, dist)
        improved = True
        while improved:
            improved = False
            for i in range(len(best) - 1):
                for j in range(i + 1, len(best)):
                    candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                    if route_length(depot, candidate, dist) < route_length(depot, best, dist) - 1e-9:
                        best, improved = candidate, True
        return best


class RoutePlanner:
    """Контекст: gRPC-сервер вызывает планировщик, алгоритм задаёт стратегия."""

    def __init__(self, strategy: RouteBuildingStrategy) -> None:
        self._strategy = strategy

    def set_strategy(self, strategy: RouteBuildingStrategy) -> None:
        self._strategy = strategy

    def plan(
        self, depot: Point, stops: list[Point], dist: DistanceSource
    ) -> tuple[list[Point], float]:
        route = self._strategy.build(depot, stops, dist)
        return route, round(route_length(depot, route, dist), 2)


if __name__ == "__main__":
    depot = Point(0, 55.60, 37.60)
    stops = [
        Point(101, 55.61, 37.53, "14-01"), Point(102, 55.77, 37.72, "14-02"),
        Point(103, 55.62, 37.58, "14-03"), Point(104, 55.67, 37.67, "15-01"),
        Point(105, 55.66, 37.65, "15-02"), Point(106, 55.64, 37.60, "15-03"),
        Point(107, 55.69, 37.65, "16-01"),
    ]
    # В сервисе матрицу передаёт matrix_builder; для примера расстояния считаются по прямой.
    dist: DistanceSource = StraightLineDistance()
    planner = RoutePlanner(GridOrderStrategy())
    for strategy in (GridOrderStrategy(), NearestNeighborStrategy(), TwoOptStrategy()):
        planner.set_strategy(strategy)
        route, km = planner.plan(depot, stops, dist)
        print(type(strategy).__name__, [p.code for p in route], km, "км")
