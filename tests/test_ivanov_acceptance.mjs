// Тесты компонента mob_acceptance (Иванов А. А.). Запуск: npm test (после сборки tsc).
import test from "node:test";
import assert from "node:assert/strict";
import {
  GridAcceptanceService, ManualMarkAcceptance, MemoryQueue, NoCheckAcceptance, QrScanAcceptance,
} from "../build/ivanov_acceptance.js";

const grid = {
  code: "14-02", pvzCode: 1043,
  units: [
    { barcode: "T-1", kind: "tote_box" }, { barcode: "T-2", kind: "tote_box" },
    { barcode: "R-1", kind: "out_of_tote" }, { barcode: "K-1", kind: "kgt" },
  ],
};

test("скан: недостача и излишки", () => {
  const r = new QrScanAcceptance().accept(grid, { scanned: ["T-1", "T-2", "X-9", "T-1"], manuallyMarked: [] });
  assert.deepEqual(r.accepted, ["T-1", "T-2"]);
  assert.deepEqual(r.missing, ["R-1", "K-1"]);
  assert.deepEqual(r.extra, ["X-9"]);
  assert.equal(r.verified, true);
});

test("ручные отметки засчитываются в пределах лимита", () => {
  const r = new ManualMarkAcceptance(0.3).accept(grid, { scanned: ["T-1", "T-2", "R-1"], manuallyMarked: ["K-1"] });
  assert.deepEqual(r.missing, []);
  assert.throws(() => new ManualMarkAcceptance(0.3).accept(grid, { scanned: [], manuallyMarked: ["T-1", "T-2"] }));
});

test("без проверки: всё принято, но не проверено", () => {
  const r = new NoCheckAcceptance().accept(grid, { scanned: [], manuallyMarked: [] });
  assert.equal(r.accepted.length, 4);
  assert.equal(r.verified, false);
});

test("контекст меняет стратегию и кладёт результат в офлайн-очередь", () => {
  const queue = new MemoryQueue();
  const service = new GridAcceptanceService(new QrScanAcceptance(), queue);
  service.acceptGrid(grid, { scanned: ["T-1"], manuallyMarked: [] });
  service.setStrategy(new NoCheckAcceptance());
  assert.equal(service.mode, "no_check");
  service.acceptGrid(grid, { scanned: [], manuallyMarked: [] });
  assert.equal(queue.items.length, 2);
  assert.equal(queue.items[1].verified, false);
});
