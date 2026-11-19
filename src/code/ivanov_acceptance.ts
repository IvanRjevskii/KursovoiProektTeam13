/**
 * Компонент mob_acceptance (мобильное приложение курьера courier_app):
 * приёмка МК при загрузке волны на складе.
 *
 * Автор: Иванов А. А. Команда 13, лабораторная работа № 3.
 *
 * У ворот склада водитель принимает МК своего рейса. В каждой МК — грузоместа
 * одного ПВЗ: тарные ящики (ТЯ), отправления вне тары и крупногабаритный товар (КГТ). Способ приёмки
 * зависит от ситуации, поэтому он вынесен в стратегию:
 *  - QrScanAcceptance     — поштучный скан штрихкода каждого грузоместа (основной);
 *  - ManualMarkAcceptance — штрихкод не читается: скан + ручная отметка номера;
 *  - NoCheckAcceptance    — «принять без проверки»: всё засчитывается, но результат
 *                           помечается как непроверенный, чтобы расхождения не
 *                           превратились в претензию к водителю без оснований.
 * Контекст GridAcceptanceService не знает, какой алгоритм выбран (принцип
 * открытости/закрытости), а результат отдаёт в офлайн-очередь через порт SyncPort
 * (принцип инверсии зависимостей): на складе связь часто пропадает.
 */

export type UnitKind = "tote_box" | "out_of_tote" | "kgt";

export interface ParcelUnit {
  readonly barcode: string;
  readonly kind: UnitKind;
}

export interface Grid {
  /** Номер МК «ряд-место», например «14-02». */
  readonly code: string;
  readonly pvzCode: number;
  readonly units: readonly ParcelUnit[];
}

export type AcceptanceMode = "qr_scan" | "manual_mark" | "no_check";

export interface AcceptanceInput {
  /** Штрихкоды, считанные камерой (компонент mob_scanner). */
  readonly scanned: readonly string[];
  /** Номера, отмеченные вручную, если штрихкод не читается. */
  readonly manuallyMarked: readonly string[];
}

export interface AcceptanceResult {
  readonly gridCode: string;
  readonly mode: AcceptanceMode;
  readonly accepted: readonly string[];
  /** Недостача: есть в составе МК, но не принято. */
  readonly missing: readonly string[];
  /** Излишки: отсканировано, но в составе МК нет (пересортица). */
  readonly extra: readonly string[];
  /** false — приёмка без поштучной проверки. */
  readonly verified: boolean;
}

/** Единый контракт алгоритма приёмки. */
export interface AcceptanceStrategy {
  readonly mode: AcceptanceMode;
  accept(grid: Grid, input: AcceptanceInput): AcceptanceResult;
}

function unique(codes: readonly string[]): string[] {
  return [...new Set(codes)];
}

function compare(grid: Grid, received: readonly string[], mode: AcceptanceMode): AcceptanceResult {
  const expected = new Set(grid.units.map((u) => u.barcode));
  const got = unique(received);
  const gotSet = new Set(got);
  return {
    gridCode: grid.code,
    mode,
    accepted: got.filter((c) => expected.has(c)),
    missing: grid.units.map((u) => u.barcode).filter((c) => !gotSet.has(c)),
    extra: got.filter((c) => !expected.has(c)),
    verified: true,
  };
}

/** Основной способ: засчитывается только отсканированное камерой. */
export class QrScanAcceptance implements AcceptanceStrategy {
  readonly mode: AcceptanceMode = "qr_scan";

  accept(grid: Grid, input: AcceptanceInput): AcceptanceResult {
    return compare(grid, input.scanned, this.mode);
  }
}

/** Скан + ручные отметки; доля ручных отметок ограничена, иначе — ошибка. */
export class ManualMarkAcceptance implements AcceptanceStrategy {
  readonly mode: AcceptanceMode = "manual_mark";

  constructor(private readonly maxManualShare: number = 0.3) {}

  accept(grid: Grid, input: AcceptanceInput): AcceptanceResult {
    const manual = unique(input.manuallyMarked);
    if (grid.units.length > 0 && manual.length / grid.units.length > this.maxManualShare) {
      throw new Error(
        `Слишком много ручных отметок в МК ${grid.code}: нужна проверка супервайзера`,
      );
    }
    return compare(grid, [...input.scanned, ...manual], this.mode);
  }
}

/** «Принять без проверки»: засчитывается весь состав МК, результат не проверен. */
export class NoCheckAcceptance implements AcceptanceStrategy {
  readonly mode: AcceptanceMode = "no_check";

  accept(grid: Grid, _input: AcceptanceInput): AcceptanceResult {
    return {
      gridCode: grid.code,
      mode: this.mode,
      accepted: grid.units.map((u) => u.barcode),
      missing: [],
      extra: [],
      verified: false,
    };
  }
}

/** Порт офлайн-очереди (компонент mob_offline_queue). */
export interface SyncPort {
  enqueue(result: AcceptanceResult): void;
}

/** Контекст стратегии: его вызывает экран волны (mob_wave_screens). */
export class GridAcceptanceService {
  constructor(
    private strategy: AcceptanceStrategy,
    private readonly queue: SyncPort,
  ) {}

  setStrategy(strategy: AcceptanceStrategy): void {
    this.strategy = strategy;
  }

  get mode(): AcceptanceMode {
    return this.strategy.mode;
  }

  acceptGrid(grid: Grid, input: AcceptanceInput): AcceptanceResult {
    const result = this.strategy.accept(grid, input);
    this.queue.enqueue(result);
    return result;
  }
}

/** Очередь в памяти: для демонстрации и тестов вместо хранилища на телефоне. */
export class MemoryQueue implements SyncPort {
  readonly items: AcceptanceResult[] = [];

  enqueue(result: AcceptanceResult): void {
    this.items.push(result);
  }
}
