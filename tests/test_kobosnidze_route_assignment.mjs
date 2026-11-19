// Тесты компонента dsp_route_planner (Кобоснидзе С. Г.). Запуск: npm test (после сборки tsc).
import test from "node:test";
import assert from "node:assert/strict";
import {
  FixedRouteAssignment, FreeRouteAssignment, RouteAssignmentService, TraineeRouteAssignment,
} from "../build/kobosnidze_route_assignment.js";

const pool = [
  { id: 1, wave: 1, pvzCodes: [1, 2, 3, 4, 5, 6, 7, 8, 9], grids: 13 },
  { id: 2, wave: 1, pvzCodes: [10, 11, 12, 13], grids: 6 },
  { id: 3, wave: 1, pvzCodes: [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24], grids: 17 },
];
const mentor = { id: 10, name: "Петров", status: "regular" };
const fixed = { id: 11, name: "Сидоров", status: "regular", fixedRouteId: 1 };

test("закреплённый маршрут", () => {
  const s = new RouteAssignmentService(pool);
  assert.deepEqual(s.assign(fixed), { driverId: 11, routeId: 1, kind: "fixed" });
});

test("свободный маршрут — самый загруженный по МК", () => {
  const s = new RouteAssignmentService(pool);
  assert.equal(s.assign(mentor).routeId, 3);
});

test("стажёр: два дня напарником, потом урезанный маршрут", () => {
  const s = new RouteAssignmentService(pool);
  s.assign(mentor);
  const day1 = s.assign({ id: 20, name: "Стажёр", status: "trainee", traineeDay: 1, mentorId: 10 });
  assert.equal(day1.kind, "trainee_pair");
  assert.equal(day1.routeId, 3);
  const day3 = s.assign({ id: 21, name: "Стажёр-2", status: "trainee", traineeDay: 3, mentorId: 10 });
  assert.deepEqual([day3.kind, day3.routeId], ["trainee_short", 2]);
});

test("явная стратегия перекрывает выбор по карточке", () => {
  const s = new RouteAssignmentService(pool);
  s.setStrategy(new FreeRouteAssignment());
  assert.equal(s.assign(fixed).kind, "free");
  assert.throws(() => new FixedRouteAssignment().assign({ ...fixed, fixedRouteId: 99 }, { pool, assigned: [] }));
  assert.throws(() => new TraineeRouteAssignment().assign({ id: 5, name: "X", status: "trainee", traineeDay: 1, mentorId: 77 }, { pool, assigned: [] }));
});
