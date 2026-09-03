"""Finite-search model for residential unit and spreadsheet finance options."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Iterable, Iterator


@dataclass(frozen=True)
class FinanceAssumptions:
    total_gfa: Decimal = Decimal("3600")
    structure_cost_per_sqm: Decimal = Decimal("25")
    private_fitout_cost_per_sqm: Decimal = Decimal("5")
    purpose_fitout_cost_per_sqm: Decimal = Decimal("12")
    corridor_fitout_cost_per_sqm: Decimal = Decimal("6")
    exterior_area: Decimal = Decimal("200")
    exterior_cost_per_sqm: Decimal = Decimal("6")
    monthly_rent_per_room: Decimal = Decimal("10")
    management_rate: Decimal = Decimal("0.10")
    monthly_operation_cost: Decimal = Decimal("300")
    structure_life_years: Decimal = Decimal("50")
    repair_reserve_divisor: Decimal = Decimal("2")
    annual_ancillary_profit: Decimal = Decimal("0")


@dataclass(frozen=True)
class FinanceResult:
    construction_cost: Decimal
    monthly_rent: Decimal
    monthly_management_cost: Decimal
    monthly_gross_profit: Decimal
    annual_rent_profit: Decimal
    annual_repair_reserve: Decimal
    annual_profit: Decimal
    payback_years: Decimal
    yield_percent: Decimal


@dataclass(frozen=True)
class UnitAssumptions:
    toilet_area: Decimal = Decimal("1.8")
    shower_area: Decimal = Decimal("2.4")
    basin_area: Decimal = Decimal("1.2")
    laundry_area: Decimal = Decimal("1.5")
    kitchen_base_area: Decimal = Decimal("4.0")
    kitchen_area_per_extra_pair: Decimal = Decimal("0.5")
    internal_circulation_rate: Decimal = Decimal("0.12")
    minimum_living_area: Decimal = Decimal("8")
    maximum_living_area: Decimal = Decimal("32")
    living_area_step: Decimal = Decimal("1")
    minimum_living_area_per_resident: Decimal = Decimal("0.75")
    maximum_living_area_per_resident: Decimal = Decimal("2.0")


@dataclass(frozen=True)
class FixtureCounts:
    toilets: int
    showers: int
    basins: int
    laundry: int


@dataclass(frozen=True)
class UnitAreaResult:
    private_area: Decimal
    living_area: Decimal
    kitchen_area: Decimal
    service_area: Decimal
    internal_circulation_area: Decimal
    total_area: Decimal
    fixtures: FixtureCounts


@dataclass(frozen=True)
class SearchSpace:
    total_gfa: Decimal = Decimal("3600")
    minimum_floors: int = 5
    maximum_floors: int = 15
    minimum_upper_floor_area: Decimal = Decimal("200")
    maximum_footprint: Decimal = Decimal("800")
    upper_floor_area_step: Decimal = Decimal("1")
    corridor_rate: Decimal = Decimal("0.15")
    planning_margin_rate: Decimal = Decimal("0.10")
    facade_aspect_ratio: Decimal = Decimal("2")
    facade_usable_ratio: Decimal = Decimal("0.70")
    minimum_room_frontage: Decimal = Decimal("2.7")
    minimum_pairs_per_unit: int = 2
    maximum_pairs_per_unit: int = 8
    minimum_pair_room_area: Decimal = Decimal("10.5")
    maximum_pair_room_area: Decimal = Decimal("15.0")
    pair_room_area_step: Decimal = Decimal("0.5")

    def __post_init__(self) -> None:
        if not Decimal("0") <= self.planning_margin_rate <= Decimal("1"):
            raise ValueError("planning_margin_rate must be between 0 and 1")


@dataclass(frozen=True)
class Candidate:
    total_floors: int
    residential_floors: int
    upper_floor_area: Decimal
    first_floor_area: Decimal
    pairs_per_unit: int
    units_per_floor: int
    pair_room_area: Decimal
    living_area: Decimal
    living_area_per_resident: Decimal
    unit_area: UnitAreaResult
    rooms_per_floor: int
    total_rooms: int
    total_residents: int
    private_area: Decimal
    purpose_area: Decimal
    corridor_area: Decimal
    first_floor_purpose_area: Decimal
    first_floor_purpose_area_per_resident: Decimal
    upper_floor_unit_area_used: Decimal
    upper_floor_unallocated_common_area: Decimal
    planning_margin_rate: Decimal
    upper_floor_planning_margin_area: Decimal
    upper_floor_post_margin_slack: Decimal
    available_facade_length: Decimal
    required_facade_length: Decimal
    facade_margin: Decimal
    finance: FinanceResult


@dataclass(frozen=True)
class SearchAnalysis:
    candidate_count: int
    representatives: dict[str, Candidate]
    pareto_candidates: tuple[Candidate, ...]


def fixture_counts(pairs_per_unit: int) -> FixtureCounts:
    """Return the planning fixture counts for a same-gender unit."""
    if pairs_per_unit <= 0:
        raise ValueError("pairs_per_unit must be positive")
    residents = pairs_per_unit * 2
    shared_fixture_count = (residents + 3) // 4
    laundry_count = (residents + 4) // 5
    return FixtureCounts(
        toilets=shared_fixture_count,
        showers=shared_fixture_count,
        basins=shared_fixture_count,
        laundry=laundry_count,
    )


def _decimal_range(start: Decimal, stop: Decimal, step: Decimal) -> tuple[Decimal, ...]:
    if step <= 0:
        raise ValueError("step must be positive")
    values: list[Decimal] = []
    current = start
    while current <= stop:
        values.append(current)
        current += step
    return tuple(values)


def living_area_candidates(
    pairs_per_unit: int,
    assumptions: UnitAssumptions,
) -> tuple[Decimal, ...]:
    """Return living areas that satisfy absolute and per-resident bounds."""
    if pairs_per_unit <= 0:
        raise ValueError("pairs_per_unit must be positive")
    residents = Decimal(pairs_per_unit * 2)
    return tuple(
        area
        for area in _decimal_range(
            assumptions.minimum_living_area,
            assumptions.maximum_living_area,
            assumptions.living_area_step,
        )
        if area / residents >= assumptions.minimum_living_area_per_resident
        and area / residents <= assumptions.maximum_living_area_per_resident
    )


def calculate_unit_area(
    *,
    pairs_per_unit: int,
    pair_room_area: Decimal,
    living_area: Decimal,
    assumptions: UnitAssumptions,
) -> UnitAreaResult:
    """Calculate the room, shared-service, and internal-circulation area."""
    if pair_room_area <= 0:
        raise ValueError("pair_room_area must be positive")
    if living_area not in living_area_candidates(pairs_per_unit, assumptions):
        raise ValueError("living_area is outside the configured range")

    fixtures = fixture_counts(pairs_per_unit)
    private_area = pair_room_area * Decimal(pairs_per_unit)
    kitchen_area = (
        assumptions.kitchen_base_area
        + assumptions.kitchen_area_per_extra_pair
        * Decimal(max(0, pairs_per_unit - 2))
    )
    service_area = (
        Decimal(fixtures.toilets) * assumptions.toilet_area
        + Decimal(fixtures.showers) * assumptions.shower_area
        + Decimal(fixtures.basins) * assumptions.basin_area
        + Decimal(fixtures.laundry) * assumptions.laundry_area
        + kitchen_area
    )
    subtotal = private_area + living_area + service_area
    internal_circulation_area = subtotal * assumptions.internal_circulation_rate
    total_area = subtotal + internal_circulation_area
    return UnitAreaResult(
        private_area=private_area,
        living_area=living_area,
        kitchen_area=kitchen_area,
        service_area=service_area,
        internal_circulation_area=internal_circulation_area,
        total_area=total_area,
        fixtures=fixtures,
    )


def upper_floor_area_candidates(
    total_floors: int,
    search_space: SearchSpace,
) -> tuple[Decimal, ...]:
    """Return upper-floor areas whose first-floor residual also fits the site."""
    if not search_space.minimum_floors <= total_floors <= search_space.maximum_floors:
        return ()
    return tuple(
        upper_area
        for upper_area in _decimal_range(
            search_space.minimum_upper_floor_area,
            search_space.maximum_footprint,
            search_space.upper_floor_area_step,
        )
        if _upper_floor_area_is_valid(total_floors, upper_area, search_space)
    )


def _upper_floor_area_is_valid(
    total_floors: int,
    upper_floor_area: Decimal,
    search_space: SearchSpace,
) -> bool:
    if not search_space.minimum_floors <= total_floors <= search_space.maximum_floors:
        return False
    if not (
        search_space.minimum_upper_floor_area
        <= upper_floor_area
        <= search_space.maximum_footprint
    ):
        return False
    residential_floors = Decimal(total_floors - 1)
    first_floor_area = (
        search_space.total_gfa - upper_floor_area * residential_floors
    )
    return (
        upper_floor_area
        <= first_floor_area
        <= search_space.maximum_footprint
    )


def available_facade_length(
    upper_floor_area: Decimal,
    search_space: SearchSpace,
) -> Decimal:
    """Estimate usable facade on a rectangular floor plate."""
    if upper_floor_area <= 0:
        raise ValueError("upper_floor_area must be positive")
    short_side = (upper_floor_area / search_space.facade_aspect_ratio).sqrt()
    long_side = short_side * search_space.facade_aspect_ratio
    perimeter = Decimal("2") * (short_side + long_side)
    return perimeter * search_space.facade_usable_ratio


def facade_allows_rooms(
    rooms_per_floor: int,
    facade_length: Decimal,
    search_space: SearchSpace,
) -> bool:
    if rooms_per_floor < 0:
        raise ValueError("rooms_per_floor must be non-negative")
    required_length = Decimal(rooms_per_floor) * search_space.minimum_room_frontage
    return required_length <= facade_length


def build_candidate(
    *,
    total_floors: int,
    upper_floor_area: Decimal,
    pairs_per_unit: int,
    units_per_floor: int,
    pair_room_area: Decimal,
    living_area: Decimal,
    search_space: SearchSpace,
    unit_assumptions: UnitAssumptions,
    finance_assumptions: FinanceAssumptions,
) -> Candidate | None:
    """Build a candidate or return None when a hard planning check fails."""
    if units_per_floor <= 0:
        return None
    if not _upper_floor_area_is_valid(
        total_floors,
        upper_floor_area,
        search_space,
    ):
        return None
    if not (
        search_space.minimum_pairs_per_unit
        <= pairs_per_unit
        <= search_space.maximum_pairs_per_unit
    ):
        return None
    if not (
        search_space.minimum_pair_room_area
        <= pair_room_area
        <= search_space.maximum_pair_room_area
    ):
        return None

    unit_area = calculate_unit_area(
        pairs_per_unit=pairs_per_unit,
        pair_room_area=pair_room_area,
        living_area=living_area,
        assumptions=unit_assumptions,
    )
    usable_rate = Decimal("1") - search_space.corridor_rate
    upper_floor_usable_area = upper_floor_area * usable_rate
    upper_floor_unit_area_used = unit_area.total_area * Decimal(units_per_floor)
    upper_floor_planning_margin_area = (
        upper_floor_unit_area_used * search_space.planning_margin_rate
    )
    upper_floor_required_area = (
        upper_floor_unit_area_used + upper_floor_planning_margin_area
    )
    if upper_floor_required_area > upper_floor_usable_area:
        return None

    rooms_per_floor = pairs_per_unit * units_per_floor
    facade_length = available_facade_length(upper_floor_area, search_space)
    required_facade_length = (
        Decimal(rooms_per_floor) * search_space.minimum_room_frontage
    )
    if not facade_allows_rooms(rooms_per_floor, facade_length, search_space):
        return None

    residential_floors = total_floors - 1
    first_floor_area = (
        search_space.total_gfa
        - upper_floor_area * Decimal(residential_floors)
    )
    total_rooms = rooms_per_floor * residential_floors
    total_residents = total_rooms * 2
    private_area = Decimal(total_rooms) * pair_room_area
    corridor_area = search_space.total_gfa * search_space.corridor_rate
    purpose_area = search_space.total_gfa - corridor_area - private_area
    if purpose_area < 0:
        return None

    first_floor_purpose_area = first_floor_area * usable_rate
    first_floor_purpose_area_per_resident = (
        first_floor_purpose_area / Decimal(total_residents)
    )
    upper_floor_unallocated_common_area = (
        upper_floor_usable_area - upper_floor_unit_area_used
    )
    upper_floor_post_margin_slack = (
        upper_floor_usable_area - upper_floor_required_area
    )
    finance = calculate_finance(
        private_area=private_area,
        purpose_area=purpose_area,
        corridor_area=corridor_area,
        room_count=total_rooms,
        assumptions=finance_assumptions,
    )
    return Candidate(
        total_floors=total_floors,
        residential_floors=residential_floors,
        upper_floor_area=upper_floor_area,
        first_floor_area=first_floor_area,
        pairs_per_unit=pairs_per_unit,
        units_per_floor=units_per_floor,
        pair_room_area=pair_room_area,
        living_area=living_area,
        living_area_per_resident=living_area / Decimal(pairs_per_unit * 2),
        unit_area=unit_area,
        rooms_per_floor=rooms_per_floor,
        total_rooms=total_rooms,
        total_residents=total_residents,
        private_area=private_area,
        purpose_area=purpose_area,
        corridor_area=corridor_area,
        first_floor_purpose_area=first_floor_purpose_area,
        first_floor_purpose_area_per_resident=first_floor_purpose_area_per_resident,
        upper_floor_unit_area_used=upper_floor_unit_area_used,
        upper_floor_unallocated_common_area=upper_floor_unallocated_common_area,
        planning_margin_rate=search_space.planning_margin_rate,
        upper_floor_planning_margin_area=upper_floor_planning_margin_area,
        upper_floor_post_margin_slack=upper_floor_post_margin_slack,
        available_facade_length=facade_length,
        required_facade_length=required_facade_length,
        facade_margin=facade_length - required_facade_length,
        finance=finance,
    )


def _maximum_whole_units(numerator: Decimal, denominator: Decimal) -> int:
    if numerator < 0 or denominator <= 0:
        return 0
    return int((numerator / denominator).to_integral_value(rounding=ROUND_FLOOR))


def iter_candidates(
    search_space: SearchSpace,
    finance_assumptions: FinanceAssumptions,
    unit_assumptions: UnitAssumptions,
) -> Iterator[Candidate]:
    """Yield every candidate that passes area, integer, and facade checks."""
    pair_room_areas = _decimal_range(
        search_space.minimum_pair_room_area,
        search_space.maximum_pair_room_area,
        search_space.pair_room_area_step,
    )
    usable_rate = Decimal("1") - search_space.corridor_rate
    for total_floors in range(
        search_space.minimum_floors,
        search_space.maximum_floors + 1,
    ):
        for upper_floor_area in upper_floor_area_candidates(
            total_floors,
            search_space,
        ):
            upper_floor_usable_area = upper_floor_area * usable_rate
            facade_length = available_facade_length(upper_floor_area, search_space)
            for pairs_per_unit in range(
                search_space.minimum_pairs_per_unit,
                search_space.maximum_pairs_per_unit + 1,
            ):
                max_units_by_facade = _maximum_whole_units(
                    facade_length,
                    Decimal(pairs_per_unit) * search_space.minimum_room_frontage,
                )
                for pair_room_area in pair_room_areas:
                    for living_area in living_area_candidates(
                        pairs_per_unit,
                        unit_assumptions,
                    ):
                        unit_area = calculate_unit_area(
                            pairs_per_unit=pairs_per_unit,
                            pair_room_area=pair_room_area,
                            living_area=living_area,
                            assumptions=unit_assumptions,
                        )
                        max_units_by_area = _maximum_whole_units(
                            upper_floor_usable_area,
                            unit_area.total_area
                            * (Decimal("1") + search_space.planning_margin_rate),
                        )
                        maximum_units = min(
                            max_units_by_area,
                            max_units_by_facade,
                        )
                        for units_per_floor in range(1, maximum_units + 1):
                            candidate = build_candidate(
                                total_floors=total_floors,
                                upper_floor_area=upper_floor_area,
                                pairs_per_unit=pairs_per_unit,
                                units_per_floor=units_per_floor,
                                pair_room_area=pair_room_area,
                                living_area=living_area,
                                search_space=search_space,
                                unit_assumptions=unit_assumptions,
                                finance_assumptions=finance_assumptions,
                            )
                            if candidate is not None:
                                yield candidate


def _candidate_rank_key(candidate: Candidate) -> tuple[Decimal | int, ...]:
    """Deterministic ranking: sheet yield first, then quality and simplicity."""
    return (
        candidate.finance.yield_percent,
        candidate.finance.annual_profit,
        candidate.total_rooms,
        candidate.pair_room_area,
        candidate.living_area_per_resident,
        candidate.first_floor_purpose_area_per_resident,
        candidate.facade_margin,
        -candidate.total_floors,
        -candidate.units_per_floor,
        -candidate.upper_floor_area,
    )


def _best_candidate(candidates: Iterable[Candidate]) -> Candidate | None:
    return max(candidates, key=_candidate_rank_key, default=None)


def _representative_selectors():
    return {
        "finance_max": lambda candidate: True,
        "balanced": lambda candidate: (
            candidate.pair_room_area >= Decimal("12")
            and candidate.living_area_per_resident >= Decimal("1")
            and candidate.first_floor_purpose_area_per_resident >= Decimal("1")
        ),
        "small_unit": lambda candidate: candidate.pairs_per_unit <= 4,
        "spacious": lambda candidate: (
            candidate.pair_room_area >= Decimal("14")
            and candidate.living_area_per_resident >= Decimal("1.5")
        ),
    }


def select_representative_candidates(
    candidates: Iterable[Candidate],
) -> dict[str, Candidate]:
    """Select the four documented comparison cases."""
    materialized = tuple(candidates)
    selected: dict[str, Candidate] = {}
    for name, selector in _representative_selectors().items():
        candidate = _best_candidate(
            item for item in materialized if selector(item)
        )
        if candidate is not None:
            selected[name] = candidate
    return selected


def pareto_frontier(candidates: Iterable[Candidate]) -> tuple[Candidate, ...]:
    """Return one deterministic geometry for each non-dominated objective point."""
    best_by_objective: dict[tuple[Decimal, Decimal, Decimal], Candidate] = {}
    for candidate in candidates:
        objective = (
            candidate.finance.yield_percent,
            candidate.pair_room_area,
            candidate.living_area_per_resident,
        )
        current = best_by_objective.get(objective)
        if current is None or _candidate_rank_key(candidate) > _candidate_rank_key(current):
            best_by_objective[objective] = candidate

    ordered = sorted(
        best_by_objective.values(),
        key=lambda candidate: (
            candidate.finance.yield_percent,
            candidate.pair_room_area,
            candidate.living_area_per_resident,
        ),
        reverse=True,
    )
    maximum_living_by_pair_area: dict[Decimal, Decimal] = {}
    frontier: list[Candidate] = []
    for candidate in ordered:
        dominated = any(
            pair_area >= candidate.pair_room_area
            and maximum_living >= candidate.living_area_per_resident
            for pair_area, maximum_living in maximum_living_by_pair_area.items()
        )
        if not dominated:
            frontier.append(candidate)
        previous_maximum = maximum_living_by_pair_area.get(
            candidate.pair_room_area,
            Decimal("-Infinity"),
        )
        maximum_living_by_pair_area[candidate.pair_room_area] = max(
            previous_maximum,
            candidate.living_area_per_resident,
        )
    return tuple(sorted(frontier, key=_candidate_rank_key, reverse=True))


def analyze_candidates(candidates: Iterable[Candidate]) -> SearchAnalysis:
    """Analyze a large candidate stream without retaining every geometry."""
    selectors = _representative_selectors()
    representatives: dict[str, Candidate] = {}
    best_by_objective: dict[tuple[Decimal, Decimal, Decimal], Candidate] = {}
    candidate_count = 0
    for candidate in candidates:
        candidate_count += 1
        for name, selector in selectors.items():
            if not selector(candidate):
                continue
            current = representatives.get(name)
            if current is None or _candidate_rank_key(candidate) > _candidate_rank_key(current):
                representatives[name] = candidate

        objective = (
            candidate.finance.yield_percent,
            candidate.pair_room_area,
            candidate.living_area_per_resident,
        )
        current_objective_candidate = best_by_objective.get(objective)
        if (
            current_objective_candidate is None
            or _candidate_rank_key(candidate)
            > _candidate_rank_key(current_objective_candidate)
        ):
            best_by_objective[objective] = candidate

    return SearchAnalysis(
        candidate_count=candidate_count,
        representatives=representatives,
        pareto_candidates=pareto_frontier(best_by_objective.values()),
    )


def calculate_finance(
    *,
    private_area: Decimal,
    purpose_area: Decimal,
    corridor_area: Decimal,
    room_count: int,
    assumptions: FinanceAssumptions,
) -> FinanceResult:
    """Reproduce the formulas used by the current simple finance sheet."""
    if min(private_area, purpose_area, corridor_area) < 0:
        raise ValueError("area values must be non-negative")
    if room_count < 0:
        raise ValueError("room_count must be non-negative")
    if private_area + purpose_area + corridor_area != assumptions.total_gfa:
        raise ValueError("area values must sum to total_gfa")

    construction_cost = (
        assumptions.total_gfa * assumptions.structure_cost_per_sqm
        + private_area * assumptions.private_fitout_cost_per_sqm
        + purpose_area * assumptions.purpose_fitout_cost_per_sqm
        + corridor_area * assumptions.corridor_fitout_cost_per_sqm
        + assumptions.exterior_area * assumptions.exterior_cost_per_sqm
    )
    monthly_rent = Decimal(room_count) * assumptions.monthly_rent_per_room
    monthly_management_cost = monthly_rent * assumptions.management_rate
    monthly_gross_profit = (
        monthly_rent
        - monthly_management_cost
        - assumptions.monthly_operation_cost
    )
    annual_rent_profit = monthly_gross_profit * Decimal("12")
    annual_repair_reserve = (
        construction_cost
        / assumptions.structure_life_years
        / assumptions.repair_reserve_divisor
    )
    annual_profit = (
        annual_rent_profit
        - annual_repair_reserve
        + assumptions.annual_ancillary_profit
    )
    if annual_profit > 0:
        payback_years = construction_cost / annual_profit
    else:
        payback_years = Decimal("Infinity")
    yield_percent = annual_profit / construction_cost * Decimal("100")

    return FinanceResult(
        construction_cost=construction_cost,
        monthly_rent=monthly_rent,
        monthly_management_cost=monthly_management_cost,
        monthly_gross_profit=monthly_gross_profit,
        annual_rent_profit=annual_rent_profit,
        annual_repair_reserve=annual_repair_reserve,
        annual_profit=annual_profit,
        payback_years=payback_years,
        yield_percent=yield_percent,
    )
