"""Тесты компонента route_planner (ЛР3). Автор: Кривенко И. Р., команда 13."""
import unittest

from krivenko_route_planner import (
    DistanceMatrix,
    GridOrderStrategy,
    NearestNeighborStrategy,
    Point,
    RoutePlanner,
    StraightLineDistance,
    TwoOptStrategy,
    route_length,
)

DEPOT = Point(0, 55.60, 37.60)
STOPS = [
    Point(101, 55.61, 37.53, "14-01"),
    Point(102, 55.77, 37.72, "14-02"),
    Point(103, 55.62, 37.58, "14-03"),
    Point(104, 55.67, 37.67, "15-01"),
    Point(105, 55.66, 37.65, "15-02"),
    Point(106, 55.64, 37.60, "15-03"),
    Point(107, 55.69, 37.65, "16-01"),
]
DIST = StraightLineDistance()


class RoutePlannerTest(unittest.TestCase):
    def test_every_strategy_visits_each_stop_once(self) -> None:
        for strategy in (GridOrderStrategy(), NearestNeighborStrategy(), TwoOptStrategy()):
            route = strategy.build(DEPOT, STOPS, DIST)
            self.assertEqual(sorted(p.code for p in route), sorted(p.code for p in STOPS))

    def test_grid_order_follows_grid_numbers(self) -> None:
        route = GridOrderStrategy().build(DEPOT, list(reversed(STOPS)), DIST)
        self.assertEqual([p.grid for p in route], sorted(p.grid for p in STOPS))

    def test_nearest_neighbor_starts_from_closest_to_depot(self) -> None:
        route = NearestNeighborStrategy().build(DEPOT, STOPS, DIST)
        closest = min(STOPS, key=lambda p: DIST.km(DEPOT, p))
        self.assertEqual(route[0], closest)

    def test_nearest_neighbor_shorter_than_grid_order(self) -> None:
        grid = route_length(DEPOT, GridOrderStrategy().build(DEPOT, STOPS, DIST), DIST)
        near = route_length(DEPOT, NearestNeighborStrategy().build(DEPOT, STOPS, DIST), DIST)
        self.assertLess(near, grid)

    def test_two_opt_not_longer_than_nearest_neighbor(self) -> None:
        near = route_length(DEPOT, NearestNeighborStrategy().build(DEPOT, STOPS, DIST), DIST)
        opt = route_length(DEPOT, TwoOptStrategy().build(DEPOT, STOPS, DIST), DIST)
        self.assertLessEqual(opt, near + 1e-9)

    def test_two_opt_removes_crossing(self) -> None:
        # Склад в начале координат, точки на прямой: оптимальный порядок — по возрастанию.
        pts = [Point(1, 0.0, 3.0), Point(2, 0.0, 1.0), Point(3, 0.0, 2.0)]
        route = TwoOptStrategy(start=GridOrderStrategy()).build(Point(0, 0.0, 0.0), pts, DIST)
        self.assertEqual([p.code for p in route], [2, 3, 1])

    def test_planner_swaps_strategy_without_changing_context(self) -> None:
        planner = RoutePlanner(GridOrderStrategy())
        _, km_grid = planner.plan(DEPOT, STOPS, DIST)
        planner.set_strategy(NearestNeighborStrategy())
        _, km_near = planner.plan(DEPOT, STOPS, DIST)
        self.assertLess(km_near, km_grid)

    def test_plan_returns_length_rounded_to_two_digits(self) -> None:
        route, km = RoutePlanner(NearestNeighborStrategy()).plan(DEPOT, STOPS, DIST)
        self.assertEqual(km, round(route_length(DEPOT, route, DIST), 2))

    def test_empty_wave_gives_empty_route(self) -> None:
        route, km = RoutePlanner(TwoOptStrategy()).plan(DEPOT, [], DIST)
        self.assertEqual((route, km), ([], 0.0))

    def test_distance_matrix_is_used_instead_of_straight_line(self) -> None:
        a, b = Point(1, 0.0, 0.0), Point(2, 0.0, 1.0)
        matrix = DistanceMatrix({(0, 1): 7.0, (1, 2): 3.0})
        self.assertEqual(route_length(Point(0, 0.0, 0.0), [a, b], matrix), 10.0)


if __name__ == "__main__":
    unittest.main()
