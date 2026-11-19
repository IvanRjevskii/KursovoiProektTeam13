/**
 * Компонент dsp_route_planner (АРМ супервайзера dispatch_web):
 * назначение маршрута водителю накануне смены.
 *
 * Автор: Кобоснидзе С. Г. Команда 13, лабораторная работа № 3.
 *
 * Супервайзер накануне закрепляет за каждым водителем предварительный маршрут —
 * список ПВЗ с МК на волну. Правило выбора зависит от водителя:
 *  - FixedRouteAssignment   — у водителя есть постоянный закреплённый маршрут;
 *  - FreeRouteAssignment    — маршрут из свободного пула: самый загруженный по МК,
 *                             чтобы опытные водители брали длинные рейсы;
 *  - TraineeRouteAssignment — стажёр: первые два дня едет напарником с наставником
 *                             на его маршруте, затем получает урезанный маршрут
 *                             (не больше заданного числа ПВЗ).
 * Стратегии взаимозаменяемы, контекст RouteAssignmentService их не различает.
 * Выбор стратегии по карточке водителя вынесен в StrategyResolver, чтобы новое
 * правило (например, «маршрут после ДТП») добавлялось без правки контекста.
 */

export type DriverStatus = "regular" | "trainee";
export type AssignmentKind = "fixed" | "free" | "trainee_pair" | "trainee_short";

export interface Driver {
  readonly id: number;
  readonly name: string;
  readonly status: DriverStatus;
  /** Постоянный маршрут, если супервайзер закрепил его по просьбе водителя. */
  readonly fixedRouteId?: number;
  /** День стажировки, начиная с 1 (только для стажёров). */
  readonly traineeDay?: number;
  /** Наставник стажёра. */
  readonly mentorId?: number;
}

export interface RouteDraft {
  readonly id: number;
  readonly wave: 1 | 2;
  readonly pvzCodes: readonly number[];
  readonly grids: number;
}

export interface Assignment {
  readonly driverId: number;
  readonly routeId: number;
  readonly kind: AssignmentKind;
  readonly mentorId?: number;
}

/** Состояние планирования на завтра: свободные маршруты и уже сделанные назначения. */
export interface PlanningBoard {
  readonly pool: readonly RouteDraft[];
  readonly assigned: readonly Assignment[];
}

/** Единый контракт правила назначения маршрута. */
export interface RouteAssignmentStrategy {
  readonly kind: AssignmentKind | "trainee";
  assign(driver: Driver, board: PlanningBoard): Assignment;
}

export class FixedRouteAssignment implements RouteAssignmentStrategy {
  readonly kind = "fixed" as const;

  assign(driver: Driver, board: PlanningBoard): Assignment {
    const route = board.pool.find((r) => r.id === driver.fixedRouteId);
    if (route === undefined) {
      throw new Error(`Закреплённый маршрут водителя ${driver.name} уже занят или отменён`);
    }
    return { driverId: driver.id, routeId: route.id, kind: this.kind };
  }
}

export class FreeRouteAssignment implements RouteAssignmentStrategy {
  readonly kind = "free" as const;

  assign(driver: Driver, board: PlanningBoard): Assignment {
    if (board.pool.length === 0) {
      throw new Error("Свободных маршрутов не осталось");
    }
    const route = [...board.pool].sort((a, b) => b.grids - a.grids)[0];
    return { driverId: driver.id, routeId: route.id, kind: this.kind };
  }
}

export class TraineeRouteAssignment implements RouteAssignmentStrategy {
  readonly kind = "trainee" as const;

  constructor(
    private readonly pairDays: number = 2,
    private readonly maxPvz: number = 6,
  ) {}

  assign(driver: Driver, board: PlanningBoard): Assignment {
    const day = driver.traineeDay ?? 1;
    if (day <= this.pairDays) {
      const mentorRoute = board.assigned.find((a) => a.driverId === driver.mentorId);
      if (mentorRoute === undefined) {
        throw new Error(`Сначала назначьте маршрут наставнику стажёра ${driver.name}`);
      }
      return {
        driverId: driver.id,
        routeId: mentorRoute.routeId,
        kind: "trainee_pair",
        mentorId: driver.mentorId,
      };
    }
    const short = board.pool
      .filter((r) => r.pvzCodes.length <= this.maxPvz)
      .sort((a, b) => a.pvzCodes.length - b.pvzCodes.length)[0];
    if (short === undefined) {
      throw new Error(`Нет урезанного маршрута (до ${this.maxPvz} ПВЗ) для стажёра ${driver.name}`);
    }
    return { driverId: driver.id, routeId: short.id, kind: "trainee_short" };
  }
}

/** Выбирает правило по карточке водителя. */
export class StrategyResolver {
  resolve(driver: Driver): RouteAssignmentStrategy {
    if (driver.status === "trainee") {
      return new TraineeRouteAssignment();
    }
    if (driver.fixedRouteId !== undefined) {
      return new FixedRouteAssignment();
    }
    return new FreeRouteAssignment();
  }
}

/** Контекст стратегии: вызывается со страницы планирования (dsp_routes_page). */
export class RouteAssignmentService {
  private board: PlanningBoard;

  constructor(
    pool: readonly RouteDraft[],
    private readonly resolver: StrategyResolver = new StrategyResolver(),
    private strategy?: RouteAssignmentStrategy,
  ) {
    this.board = { pool: [...pool], assigned: [] };
  }

  /** Явно задать правило (супервайзер выбрал вручную); undefined — по карточке водителя. */
  setStrategy(strategy: RouteAssignmentStrategy | undefined): void {
    this.strategy = strategy;
  }

  assign(driver: Driver): Assignment {
    const rule = this.strategy ?? this.resolver.resolve(driver);
    const result = rule.assign(driver, this.board);
    const pool =
      result.kind === "trainee_pair"
        ? this.board.pool
        : this.board.pool.filter((r) => r.id !== result.routeId);
    this.board = { pool, assigned: [...this.board.assigned, result] };
    return result;
  }

  get assignments(): readonly Assignment[] {
    return this.board.assigned;
  }
}
