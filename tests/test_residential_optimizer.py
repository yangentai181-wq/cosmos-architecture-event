from decimal import Decimal
from dataclasses import replace
import csv
from pathlib import Path
import tempfile
import unittest

from tools.residential_optimizer import (
    FinanceAssumptions,
    SearchSpace,
    UnitAssumptions,
    available_facade_length,
    build_candidate,
    calculate_finance,
    calculate_unit_area,
    facade_allows_rooms,
    fixture_counts,
    iter_candidates,
    living_area_candidates,
    pareto_frontier,
    select_representative_candidates,
    upper_floor_area_candidates,
)
from tools.generate_residential_optimization import generate_outputs


class FinanceModelTest(unittest.TestCase):
    def test_reproduces_current_spreadsheet_case(self):
        result = calculate_finance(
            private_area=Decimal("2250"),
            purpose_area=Decimal("810"),
            corridor_area=Decimal("540"),
            room_count=112,
            assumptions=FinanceAssumptions(),
        )

        self.assertEqual(result.construction_cost, Decimal("115410"))
        self.assertEqual(result.annual_repair_reserve, Decimal("1154.1"))
        self.assertEqual(result.annual_profit, Decimal("7341.9"))
        self.assertAlmostEqual(float(result.payback_years), 15.7193641973, places=9)
        self.assertAlmostEqual(float(result.yield_percent), 6.3615804523, places=9)

    def test_rejects_an_area_total_that_does_not_match_gfa(self):
        with self.assertRaisesRegex(ValueError, "total_gfa"):
            calculate_finance(
                private_area=Decimal("2250"),
                purpose_area=Decimal("809"),
                corridor_area=Decimal("540"),
                room_count=112,
                assumptions=FinanceAssumptions(),
            )

    def test_rent_is_counted_per_pair_room_not_per_resident(self):
        result = calculate_finance(
            private_area=Decimal("12"),
            purpose_area=Decimal("3048"),
            corridor_area=Decimal("540"),
            room_count=1,
            assumptions=FinanceAssumptions(),
        )

        self.assertEqual(result.monthly_rent, Decimal("10"))


class UnitModelTest(unittest.TestCase):
    def test_fixture_counts_scale_with_residents(self):
        four_people = fixture_counts(2)
        self.assertEqual(
            (four_people.toilets, four_people.showers, four_people.basins, four_people.laundry),
            (1, 1, 1, 1),
        )

        six_people = fixture_counts(3)
        self.assertEqual(
            (six_people.toilets, six_people.showers, six_people.basins, six_people.laundry),
            (2, 2, 2, 2),
        )

        sixteen_people = fixture_counts(8)
        self.assertEqual(
            (
                sixteen_people.toilets,
                sixteen_people.showers,
                sixteen_people.basins,
                sixteen_people.laundry,
            ),
            (4, 4, 4, 4),
        )

    def test_living_candidates_obey_absolute_and_per_resident_bounds(self):
        assumptions = UnitAssumptions()

        self.assertEqual(
            living_area_candidates(2, assumptions),
            (Decimal("8"),),
        )
        sixteen_people = living_area_candidates(8, assumptions)
        self.assertEqual(sixteen_people[0], Decimal("12"))
        self.assertEqual(sixteen_people[-1], Decimal("32"))

    def test_unit_area_includes_rooms_services_and_internal_circulation(self):
        result = calculate_unit_area(
            pairs_per_unit=4,
            pair_room_area=Decimal("12"),
            living_area=Decimal("8"),
            assumptions=UnitAssumptions(),
        )

        self.assertEqual(result.private_area, Decimal("48"))
        self.assertEqual(result.kitchen_area, Decimal("5.0"))
        self.assertEqual(result.service_area, Decimal("18.8"))
        self.assertEqual(result.internal_circulation_area, Decimal("8.976"))
        self.assertEqual(result.total_area, Decimal("83.776"))


class BuildingModelTest(unittest.TestCase):
    def test_default_planning_margin_reserves_ten_percent_of_unit_area(self):
        self.assertEqual(
            SearchSpace().planning_margin_rate,
            Decimal("0.10"),
        )

    def test_negative_planning_margin_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "planning_margin_rate"):
            replace(SearchSpace(), planning_margin_rate=Decimal("-0.01"))

    def test_planning_margin_rejects_a_floor_that_only_just_fits_raw_unit_area(self):
        without_margin = build_candidate(
            total_floors=12,
            upper_floor_area=Decimal("297"),
            pairs_per_unit=6,
            units_per_floor=2,
            pair_room_area=Decimal("12"),
            living_area=Decimal("14"),
            search_space=replace(SearchSpace(), planning_margin_rate=Decimal("0")),
            unit_assumptions=UnitAssumptions(),
            finance_assumptions=FinanceAssumptions(),
        )
        with_default_margin = build_candidate(
            total_floors=12,
            upper_floor_area=Decimal("297"),
            pairs_per_unit=6,
            units_per_floor=2,
            pair_room_area=Decimal("12"),
            living_area=Decimal("14"),
            search_space=SearchSpace(),
            unit_assumptions=UnitAssumptions(),
            finance_assumptions=FinanceAssumptions(),
        )

        self.assertIsNotNone(without_margin)
        assert without_margin is not None
        self.assertEqual(
            without_margin.upper_floor_unallocated_common_area,
            Decimal("0.002"),
        )
        self.assertIsNone(with_default_margin)

    def test_candidate_reports_reserved_margin_and_post_margin_slack(self):
        candidate = build_candidate(
            total_floors=11,
            upper_floor_area=Decimal("327"),
            pairs_per_unit=6,
            units_per_floor=2,
            pair_room_area=Decimal("12"),
            living_area=Decimal("14"),
            search_space=SearchSpace(),
            unit_assumptions=UnitAssumptions(),
            finance_assumptions=FinanceAssumptions(),
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.planning_margin_rate, Decimal("0.10"))
        self.assertEqual(
            candidate.upper_floor_planning_margin_area,
            Decimal("25.2448"),
        )
        self.assertEqual(
            candidate.upper_floor_post_margin_slack,
            Decimal("0.2572"),
        )

    def test_upper_floor_area_candidates_respect_total_area_and_footprint(self):
        search_space = SearchSpace()

        five_floors = upper_floor_area_candidates(5, search_space)
        self.assertEqual(five_floors[0], Decimal("700"))
        self.assertEqual(five_floors[-1], Decimal("720"))

        fifteen_floors = upper_floor_area_candidates(15, search_space)
        self.assertEqual(fifteen_floors[0], Decimal("200"))
        self.assertEqual(fifteen_floors[-1], Decimal("240"))

    def test_build_candidate_preserves_area_and_integer_room_count(self):
        candidate = build_candidate(
            total_floors=6,
            upper_floor_area=Decimal("600"),
            pairs_per_unit=4,
            units_per_floor=2,
            pair_room_area=Decimal("12"),
            living_area=Decimal("8"),
            search_space=SearchSpace(),
            unit_assumptions=UnitAssumptions(),
            finance_assumptions=FinanceAssumptions(),
        )

        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertEqual(candidate.first_floor_area, Decimal("600"))
        self.assertEqual(candidate.rooms_per_floor, 8)
        self.assertEqual(candidate.total_rooms, 40)
        self.assertEqual(candidate.total_residents, 80)
        self.assertEqual(candidate.corridor_area, Decimal("540.00"))
        self.assertEqual(candidate.private_area, Decimal("480"))
        self.assertEqual(candidate.purpose_area, Decimal("2580.00"))
        self.assertEqual(
            candidate.private_area + candidate.purpose_area + candidate.corridor_area,
            Decimal("3600.00"),
        )

    def test_facade_proxy_rejects_more_rooms_than_available_frontage(self):
        available = available_facade_length(Decimal("600"), SearchSpace())

        self.assertTrue(facade_allows_rooms(8, available, SearchSpace()))
        self.assertFalse(facade_allows_rooms(30, available, SearchSpace()))


class SearchTest(unittest.TestCase):
    def setUp(self):
        self.search_space = replace(
            SearchSpace(),
            minimum_floors=5,
            maximum_floors=5,
            minimum_upper_floor_area=Decimal("700"),
            maximum_footprint=Decimal("800"),
            upper_floor_area_step=Decimal("100"),
            minimum_pairs_per_unit=2,
            maximum_pairs_per_unit=4,
            minimum_pair_room_area=Decimal("10.5"),
            maximum_pair_room_area=Decimal("14.0"),
            pair_room_area_step=Decimal("3.5"),
        )

    def test_enumeration_is_deterministic_and_all_candidates_are_feasible(self):
        first = list(
            iter_candidates(
                self.search_space,
                FinanceAssumptions(),
                UnitAssumptions(),
            )
        )
        second = list(
            iter_candidates(
                self.search_space,
                FinanceAssumptions(),
                UnitAssumptions(),
            )
        )

        self.assertGreater(len(first), 0)
        self.assertEqual(first, second)
        for candidate in first:
            self.assertGreaterEqual(candidate.facade_margin, 0)
            self.assertGreaterEqual(candidate.upper_floor_unallocated_common_area, 0)
            self.assertGreaterEqual(candidate.upper_floor_post_margin_slack, 0)
            self.assertEqual(
                candidate.upper_floor_unallocated_common_area,
                candidate.upper_floor_planning_margin_area
                + candidate.upper_floor_post_margin_slack,
            )
            self.assertEqual(
                candidate.total_rooms,
                candidate.residential_floors
                * candidate.units_per_floor
                * candidate.pairs_per_unit,
            )
            self.assertEqual(
                candidate.private_area
                + candidate.purpose_area
                + candidate.corridor_area,
                self.search_space.total_gfa,
            )

    def test_representative_filters_are_enforced(self):
        candidates = tuple(
            iter_candidates(
                self.search_space,
                FinanceAssumptions(),
                UnitAssumptions(),
            )
        )
        representatives = select_representative_candidates(candidates)

        self.assertEqual(
            set(representatives),
            {"finance_max", "balanced", "small_unit", "spacious"},
        )
        self.assertGreaterEqual(representatives["balanced"].pair_room_area, 12)
        self.assertGreaterEqual(
            representatives["balanced"].living_area_per_resident,
            1,
        )
        self.assertGreaterEqual(
            representatives["balanced"].first_floor_purpose_area_per_resident,
            1,
        )
        self.assertLessEqual(representatives["small_unit"].pairs_per_unit, 4)
        self.assertGreaterEqual(representatives["spacious"].pair_room_area, 14)
        self.assertGreaterEqual(
            representatives["spacious"].living_area_per_resident,
            Decimal("1.5"),
        )

    def test_pareto_candidates_are_not_dominated(self):
        candidates = tuple(
            iter_candidates(
                self.search_space,
                FinanceAssumptions(),
                UnitAssumptions(),
            )
        )
        frontier = pareto_frontier(candidates)

        self.assertGreater(len(frontier), 0)
        for candidate in frontier:
            for other in candidates:
                all_at_least_as_good = (
                    other.finance.yield_percent >= candidate.finance.yield_percent
                    and other.pair_room_area >= candidate.pair_room_area
                    and other.living_area_per_resident
                    >= candidate.living_area_per_resident
                )
                any_strictly_better = (
                    other.finance.yield_percent > candidate.finance.yield_percent
                    or other.pair_room_area > candidate.pair_room_area
                    or other.living_area_per_resident
                    > candidate.living_area_per_resident
                )
                self.assertFalse(all_at_least_as_good and any_strictly_better)


class ReportTest(unittest.TestCase):
    def test_custom_margin_rate_is_named_in_the_main_conclusion(self):
        search_space = replace(
            SearchSpace(),
            minimum_floors=5,
            maximum_floors=5,
            minimum_upper_floor_area=Decimal("700"),
            maximum_footprint=Decimal("800"),
            upper_floor_area_step=Decimal("100"),
            minimum_pairs_per_unit=2,
            maximum_pairs_per_unit=4,
            minimum_pair_room_area=Decimal("10.5"),
            maximum_pair_room_area=Decimal("14.0"),
            pair_room_area_step=Decimal("3.5"),
            planning_margin_rate=Decimal("0.075"),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            markdown_path = output_directory / "results.md"
            generate_outputs(
                search_space=search_space,
                csv_path=output_directory / "pareto.csv",
                markdown_path=markdown_path,
            )

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("既定の計画余白7.5%では、主案", markdown)

    def test_generates_auditable_csv_and_markdown(self):
        search_space = replace(
            SearchSpace(),
            minimum_floors=5,
            maximum_floors=5,
            minimum_upper_floor_area=Decimal("700"),
            maximum_footprint=Decimal("800"),
            upper_floor_area_step=Decimal("100"),
            minimum_pairs_per_unit=2,
            maximum_pairs_per_unit=4,
            minimum_pair_room_area=Decimal("10.5"),
            maximum_pair_room_area=Decimal("14.0"),
            pair_room_area_step=Decimal("3.5"),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_directory = Path(temporary_directory)
            csv_path = output_directory / "pareto.csv"
            markdown_path = output_directory / "results.md"

            analysis = generate_outputs(
                search_space=search_space,
                csv_path=csv_path,
                markdown_path=markdown_path,
            )

            self.assertGreater(analysis.candidate_count, 0)
            self.assertTrue(csv_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertNotIn(b"\r\n", csv_path.read_bytes())
            with csv_path.open(encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertGreater(len(rows), 0)
            self.assertTrue(
                {
                    "total_floors",
                    "upper_floor_area",
                    "first_floor_room_count",
                    "pair_room_area",
                    "pairs_per_unit",
                    "living_area",
                    "toilets_per_unit",
                    "total_rooms",
                    "construction_cost",
                    "annual_profit",
                    "payback_years",
                    "yield_percent",
                    "facade_margin",
                    "planning_margin_rate",
                    "upper_floor_planning_margin_area",
                    "upper_floor_post_margin_slack",
                }.issubset(rows[0])
            )

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("現行収支表の再現", markdown)
            self.assertIn("収支最大案", markdown)
            self.assertIn("推奨バランス案", markdown)
            self.assertIn("平面図未検証", markdown)
            self.assertIn("日本人学生1名と留学生1名", markdown)
            self.assertIn("同じペア室に住み続け", markdown)
            self.assertIn("旧比較モデル", markdown)
            self.assertIn("現在の提案主案ではない", markdown)
            self.assertIn("計画余白10.0%", markdown)
            self.assertIn("5.0%", markdown)
            self.assertIn("7.5%", markdown)
            self.assertIn("10.0%", markdown)
            self.assertIn("/opt/homebrew/bin/python3", markdown)


if __name__ == "__main__":
    unittest.main()
