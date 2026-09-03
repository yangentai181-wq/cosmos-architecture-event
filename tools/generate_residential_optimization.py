"""Generate auditable CSV and Markdown results for the dormitory optimizer."""

from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Sequence

if __package__:
    from tools.residential_optimizer import (
        Candidate,
        FinanceAssumptions,
        SearchAnalysis,
        SearchSpace,
        UnitAssumptions,
        analyze_candidates,
        calculate_finance,
        iter_candidates,
    )
else:  # Direct execution from the tools directory.
    from residential_optimizer import (  # type: ignore[no-redef]
        Candidate,
        FinanceAssumptions,
        SearchAnalysis,
        SearchSpace,
        UnitAssumptions,
        analyze_candidates,
        calculate_finance,
        iter_candidates,
    )


DEFAULT_CSV_PATH = Path("artifacts/residential-unit-optimization-pareto.csv")
DEFAULT_MARKDOWN_PATH = Path(
    "docs/residential-unit-optimization-results-2026-09-03.md"
)
SENSITIVITY_MARGIN_RATES = (
    Decimal("0.05"),
    Decimal("0.075"),
    Decimal("0.10"),
)

CSV_FIELDS = (
    "pareto_rank",
    "total_floors",
    "residential_floors",
    "upper_floor_area",
    "first_floor_area",
    "first_floor_room_count",
    "pair_room_area",
    "pairs_per_unit",
    "units_per_floor",
    "living_area",
    "living_area_per_resident",
    "toilets_per_unit",
    "showers_per_unit",
    "basins_per_unit",
    "laundry_per_unit",
    "kitchen_area_per_unit",
    "unit_total_area",
    "planning_margin_rate",
    "upper_floor_planning_margin_area",
    "upper_floor_post_margin_slack",
    "rooms_per_floor",
    "total_rooms",
    "total_residents",
    "private_area",
    "purpose_area",
    "corridor_area",
    "first_floor_purpose_area_per_resident",
    "construction_cost",
    "annual_profit",
    "payback_years",
    "yield_percent",
    "sheet_target_pass",
    "available_facade_length",
    "required_facade_length",
    "facade_margin",
)

REPRESENTATIVE_LABELS = {
    "finance_max": "収支最大案",
    "balanced": "推奨バランス案",
    "small_unit": "小ユニット案",
    "spacious": "空間ゆとり案",
}


def _raw(value: Decimal) -> str:
    return format(value, "f")


def _display(value: Decimal, places: int) -> str:
    quantum = Decimal("1").scaleb(-places)
    return format(value.quantize(quantum, rounding=ROUND_HALF_UP), f".{places}f")


def _sheet_target_passes(candidate: Candidate) -> bool:
    return (
        candidate.finance.payback_years <= Decimal("15")
        and candidate.finance.yield_percent >= Decimal("7")
    )


def _candidate_row(rank: int, candidate: Candidate) -> dict[str, str | int]:
    fixtures = candidate.unit_area.fixtures
    return {
        "pareto_rank": rank,
        "total_floors": candidate.total_floors,
        "residential_floors": candidate.residential_floors,
        "upper_floor_area": _raw(candidate.upper_floor_area),
        "first_floor_area": _raw(candidate.first_floor_area),
        "first_floor_room_count": 0,
        "pair_room_area": _raw(candidate.pair_room_area),
        "pairs_per_unit": candidate.pairs_per_unit,
        "units_per_floor": candidate.units_per_floor,
        "living_area": _raw(candidate.living_area),
        "living_area_per_resident": _raw(candidate.living_area_per_resident),
        "toilets_per_unit": fixtures.toilets,
        "showers_per_unit": fixtures.showers,
        "basins_per_unit": fixtures.basins,
        "laundry_per_unit": fixtures.laundry,
        "kitchen_area_per_unit": _raw(candidate.unit_area.kitchen_area),
        "unit_total_area": _raw(candidate.unit_area.total_area),
        "planning_margin_rate": _raw(candidate.planning_margin_rate),
        "upper_floor_planning_margin_area": _raw(
            candidate.upper_floor_planning_margin_area
        ),
        "upper_floor_post_margin_slack": _raw(
            candidate.upper_floor_post_margin_slack
        ),
        "rooms_per_floor": candidate.rooms_per_floor,
        "total_rooms": candidate.total_rooms,
        "total_residents": candidate.total_residents,
        "private_area": _raw(candidate.private_area),
        "purpose_area": _raw(candidate.purpose_area),
        "corridor_area": _raw(candidate.corridor_area),
        "first_floor_purpose_area_per_resident": _raw(
            candidate.first_floor_purpose_area_per_resident
        ),
        "construction_cost": _raw(candidate.finance.construction_cost),
        "annual_profit": _raw(candidate.finance.annual_profit),
        "payback_years": _raw(candidate.finance.payback_years),
        "yield_percent": _raw(candidate.finance.yield_percent),
        "sheet_target_pass": "yes" if _sheet_target_passes(candidate) else "no",
        "available_facade_length": _raw(candidate.available_facade_length),
        "required_facade_length": _raw(candidate.required_facade_length),
        "facade_margin": _raw(candidate.facade_margin),
    }


def _write_csv(path: Path, candidates: tuple[Candidate, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=CSV_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        for rank, candidate in enumerate(candidates, start=1):
            writer.writerow(_candidate_row(rank, candidate))


def _representative_table(analysis: SearchAnalysis) -> str:
    rows = [
        "| 案 | 階数 | 上階/1階㎡ | ペア室㎡ | ペア/ユニット | ユニット/階 | リビング㎡（1人） | 室/人 | 1階共用㎡/人 | 建設費万円 | 年間利益万円 | 回収年 | 利回り |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in REPRESENTATIVE_LABELS.items():
        candidate = analysis.representatives.get(key)
        if candidate is None:
            rows.append(f"| {label} | 該当なし | | | | | | | | | | | |")
            continue
        rows.append(
            "| {label} | {floors} | {upper}/{first} | {room} | {pairs} | "
            "{units} | {living}（{living_per_person}） | {rooms}/{residents} | "
            "{first_common} | {cost} | {profit} | {payback} | {yield_value}% |".format(
                label=label,
                floors=candidate.total_floors,
                upper=_display(candidate.upper_floor_area, 0),
                first=_display(candidate.first_floor_area, 0),
                room=_display(candidate.pair_room_area, 1),
                pairs=candidate.pairs_per_unit,
                units=candidate.units_per_floor,
                living=_display(candidate.living_area, 1),
                living_per_person=_display(candidate.living_area_per_resident, 2),
                rooms=candidate.total_rooms,
                residents=candidate.total_residents,
                first_common=_display(
                    candidate.first_floor_purpose_area_per_resident,
                    2,
                ),
                cost=_display(candidate.finance.construction_cost, 1),
                profit=_display(candidate.finance.annual_profit, 1),
                payback=_display(candidate.finance.payback_years, 2),
                yield_value=_display(candidate.finance.yield_percent, 2),
            )
        )
    return "\n".join(rows)


def _unit_detail_table(analysis: SearchAnalysis) -> str:
    rows = [
        "| 案 | トイレ | シャワー | 洗面 | 洗濯 | ミニキッチン㎡ | ユニット算定㎡ | 計画余白㎡/階 | 余白後残り㎡/階 | 外周余裕m |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, label in REPRESENTATIVE_LABELS.items():
        candidate = analysis.representatives.get(key)
        if candidate is None:
            continue
        fixtures = candidate.unit_area.fixtures
        rows.append(
            "| {label} | {toilets} | {showers} | {basins} | {laundry} | "
            "{kitchen} | {unit_area} | {planning_margin} | {post_margin_slack} | "
            "{facade_margin} |".format(
                label=label,
                toilets=fixtures.toilets,
                showers=fixtures.showers,
                basins=fixtures.basins,
                laundry=fixtures.laundry,
                kitchen=_display(candidate.unit_area.kitchen_area, 1),
                unit_area=_display(candidate.unit_area.total_area, 2),
                planning_margin=_display(
                    candidate.upper_floor_planning_margin_area,
                    2,
                ),
                post_margin_slack=_display(
                    candidate.upper_floor_post_margin_slack,
                    2,
                ),
                facade_margin=_display(candidate.facade_margin, 2),
            )
        )
    return "\n".join(rows)


def _candidate_summary(candidate: Candidate | None) -> str:
    if candidate is None:
        return "該当なし"
    return (
        f"{candidate.total_floors}階・上階{_display(candidate.upper_floor_area, 0)}㎡・"
        f"ペア室{_display(candidate.pair_room_area, 1)}㎡・"
        f"{candidate.pairs_per_unit}ペア×{candidate.units_per_floor}ユニット"
    )


def _sensitivity_table(
    analyses: dict[Decimal, SearchAnalysis],
) -> str:
    rows = [
        "| 計画余白 | 成立候補 | 推奨バランス案 | 同利回り | 収支最大案 | 同利回り |",
        "| ---: | ---: | --- | ---: | --- | ---: |",
    ]
    for rate in SENSITIVITY_MARGIN_RATES:
        analysis = analyses[rate]
        balanced = analysis.representatives.get("balanced")
        finance_max = analysis.representatives.get("finance_max")
        rows.append(
            "| {rate}% | {count:,} | {balanced} | {balanced_yield} | "
            "{finance_max} | {finance_yield} |".format(
                rate=_display(rate * Decimal("100"), 1),
                count=analysis.candidate_count,
                balanced=_candidate_summary(balanced),
                balanced_yield=(
                    f"{_display(balanced.finance.yield_percent, 2)}%"
                    if balanced is not None
                    else "—"
                ),
                finance_max=_candidate_summary(finance_max),
                finance_yield=(
                    f"{_display(finance_max.finance.yield_percent, 2)}%"
                    if finance_max is not None
                    else "—"
                ),
            )
        )
    return "\n".join(rows)


def _main_conclusion(
    analysis: SearchAnalysis,
    planning_margin_rate: Decimal,
) -> str:
    balanced = analysis.representatives.get("balanced")
    finance_max = analysis.representatives.get("finance_max")
    if balanced is None or finance_max is None:
        return "既定条件では比較に必要な代表案が揃わなかった。"
    return (
        "既定の計画余白"
        f"{_display(planning_margin_rate * Decimal('100'), 1)}%では、主案を"
        f"**{_candidate_summary(balanced)}**（{balanced.total_rooms}室・"
        f"{balanced.total_residents}人、年間利益"
        f"{_display(balanced.finance.annual_profit, 1)}万円、利回り"
        f"{_display(balanced.finance.yield_percent, 2)}%、回収"
        f"{_display(balanced.finance.payback_years, 2)}年）とする。"
        "既存収支表の目標を優先する比較案は"
        f"**{_candidate_summary(finance_max)}**（{finance_max.total_rooms}室・"
        f"{finance_max.total_residents}人、年間利益"
        f"{_display(finance_max.finance.annual_profit, 1)}万円、利回り"
        f"{_display(finance_max.finance.yield_percent, 2)}%、回収"
        f"{_display(finance_max.finance.payback_years, 2)}年）である。"
    )


def _render_markdown(
    analysis: SearchAnalysis,
    search_space: SearchSpace,
    sensitivity_analyses: dict[Decimal, SearchAnalysis],
) -> str:
    finance_assumptions = FinanceAssumptions(total_gfa=search_space.total_gfa)
    baseline = calculate_finance(
        private_area=Decimal("2250"),
        purpose_area=Decimal("810"),
        corridor_area=Decimal("540"),
        room_count=112,
        assumptions=finance_assumptions,
    )
    return f"""# 住居ユニット収支最適化 結果

- **仕様日:** 2026-09-03
- **計算範囲:** 総延床3,600㎡、1階住居なし、2階以上同面積・同構成、5〜15階
- **既定の計画余白:** {_display(search_space.planning_margin_rate * Decimal("100"), 1)}%
- **成立候補:** {analysis.candidate_count:,}件
- **パレート解:** {len(analysis.pareto_candidates):,}件

## 結論の読み方

{_main_conclusion(analysis, search_space.planning_margin_rate)}

「収支最大案」は既存収支表の利回りだけを最大化した算術上の案で、推薦そのものではない。「推奨バランス案」は、ペア室12㎡以上、会話・休息用リビング1人1㎡以上、1階目的共用部1人1㎡以上を追加した中で利回りが最大の案である。

## 代表4案

{_representative_table(analysis)}

### ユニット設備と面積

{_unit_detail_table(analysis)}

1ペア室は、日本人学生1名と留学生1名の同性2人が同室で暮らす最小単位である。片方が退去しても、残る学生は同じペア室に住み続けられる。各ユニットは男女別に割り当て、トイレ・独立シャワー・洗面・洗濯をユニット内で完結させる。ミニキッチンは食事用ではなく、飲み物・夜食用である。食事は1階食堂で取り、2階以上のリビングにはダイニング面積を含めていない。

## 計画余白の感度分析

ユニット算定面積に対して、壁厚、柱型、設備シャフト、納まり調整を吸収するための計画余白を上乗せして配置可否を判定した。これは収支表の面積区分や建設費単価を変えるものではない。

{_sensitivity_table(sensitivity_analyses)}

5%は攻めた初期仮定、7.5%は中間、10%は平面図前の既定値である。余白率を変えて代表案が動くため、旧モデルで上階297㎡にユニット算定面積が0.002㎡だけ残っていた案は採用しない。

## 現行収支表の再現

現行入力の専有2,250㎡、目的共用810㎡、廊下等540㎡、112室を同じ式へ入れた結果である。これは新しい整数配置条件を満たす比較案ではなく、式の回帰テストに使う。

| 項目 | 再現値 |
| --- | ---: |
| 建設コスト | {_display(baseline.construction_cost, 1)}万円 |
| 年間利益 | {_display(baseline.annual_profit, 1)}万円 |
| 回収期間 | {_display(baseline.payback_years, 2)}年 |
| 利回り | {_display(baseline.yield_percent, 4)}% |

## 探索条件

- ペア室: 10.5〜15.0㎡、0.5㎡刻み。水回りを含まず、二段ベッド、机・椅子2組、2人分収納を置く前提。
- ユニット: 2〜8ペア。男女別で、水回り・洗濯・ミニキッチン・リビングを内部に持つ。
- リビング: 8〜32㎡、1㎡刻み、かつ1人0.75〜2.0㎡。食堂は兼ねない。
- 設備数: トイレ・シャワー・洗面は各 `ceil(居住者/4)`、洗濯は `ceil(居住者/5)`。
- 廊下等: 各階15%。総延床が固定なので合計540㎡。
- 計画余白: この出力ではユニット算定面積の{_display(search_space.planning_margin_rate * Decimal("100"), 1)}%を配置条件に加算。5%、7.5%、10%を感度比較。
- 上階面積: 1㎡刻み。1階の残余面積とともに800㎡以下、上階は1階以下。
- 外周代理: 2:1矩形の外周70%を使え、1室2.7mの間口を要するものとして全室分を確認。
- 収支: RC、専有Rank C、目的共用Rank A、廊下Rank C、外構Rank C、家賃10万円/ペア室・月、管理費10%、運営費300万円/月、付帯事業0円。

## パレートCSV

`artifacts/residential-unit-optimization-pareto.csv` に、利回り、ペア室面積、リビング1人あたり面積のいずれかを改善すると他が悪化する候補を保存した。金額・面積は計算途中で丸めず、CSVには生値を出している。

## 重要な未検証事項

- **平面図未検証:** {_display(search_space.planning_margin_rate * Decimal("100"), 1)}%の計画余白と外周長の代理条件に合格しても、すべてのペア室の窓、男女動線、階段、エレベーター、設備シャフト、避難経路が実際に納まるとは断定できない。
- 既存収支表には階数による構造・昇降機・防災コストの割増がない。高層案ほど有利に見える偏りがあり得る。
- 総延床3,600㎡と容積率300%の整合には、容積不算入部分を含む用途別面積検証が必要。
- 1階目的共用部は食堂だけでなくイベント・管理等も含む。厨房、席数、食事時間帯は別途検証が必要。
- 面積枠と設備数は初期計画基準であり、建築基準法上の適合や茨木市との協議結果を示すものではない。
- 男女比は需要調査後に割り当てる。寸法上は各ユニットを男女どちらにも割り当てられる同一仕様とした。

## 再実行

```bash
/opt/homebrew/bin/python3 tools/generate_residential_optimization.py
/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer -v
```

## 根拠と実装境界

- 詳細仕様: `docs/superpowers/specs/2026-09-03-residential-unit-optimizer-design.md`
- 収支正本索引: `docs/source-intake.md`
- 近似事例: [長野県立大学 象山寮](https://www.u-nagano.ac.jp/campuslife/dormitory/facility/)
- 面積効率の参考: [Georgia State Financing and Investment Commission Predesign Guidelines](https://opb.georgia.gov/document/publication/162041300predesignguidelinesapril2001pdf/download)、[LCCC Residence Hall Level II Report](https://www.lccc.wy.edu/Documents/About/accreditation/2018/5-1/5I2_JT_Residence%20Hall%20Level%20II%20Report.pdf)
- 法令確認先: [建築基準法](https://laws.e-gov.go.jp/law/325AC0000000201)、[建築基準法施行令](https://laws.e-gov.go.jp/law/325CO0000000338)、[大阪府建築基準法施行条例](https://www.pref.osaka.lg.jp/houbun/reiki/reiki_honbun/k201RG00000834.html)、[茨木市建築基準法施行細則](https://www.city.ibaraki.osaka.jp/office/hobun/reiki_int/reiki_honbun/k213RG00000395.html)

Google Sheet、既存HTML、外部サービスへの書き戻しは行っていない。
"""


def generate_outputs(
    *,
    search_space: SearchSpace,
    csv_path: Path,
    markdown_path: Path,
) -> SearchAnalysis:
    analysis = analyze_candidates(
        iter_candidates(
            search_space,
            FinanceAssumptions(total_gfa=search_space.total_gfa),
            UnitAssumptions(),
        )
    )
    if analysis.candidate_count == 0:
        raise RuntimeError("no feasible candidates found")
    sensitivity_analyses: dict[Decimal, SearchAnalysis] = {}
    for margin_rate in SENSITIVITY_MARGIN_RATES:
        if margin_rate == search_space.planning_margin_rate:
            sensitivity_analyses[margin_rate] = analysis
            continue
        scenario_search_space = replace(
            search_space,
            planning_margin_rate=margin_rate,
        )
        sensitivity_analyses[margin_rate] = analyze_candidates(
            iter_candidates(
                scenario_search_space,
                FinanceAssumptions(total_gfa=scenario_search_space.total_gfa),
                UnitAssumptions(),
            )
        )
    _write_csv(csv_path, analysis.pareto_candidates)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(
        _render_markdown(analysis, search_space, sensitivity_analyses),
        encoding="utf-8",
    )
    return analysis


def _parser() -> argparse.ArgumentParser:
    defaults = SearchSpace()
    parser = argparse.ArgumentParser(
        description="Enumerate residential-unit configurations and generate results.",
    )
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_MARKDOWN_PATH)
    parser.add_argument("--min-floors", type=int, default=defaults.minimum_floors)
    parser.add_argument("--max-floors", type=int, default=defaults.maximum_floors)
    parser.add_argument(
        "--min-upper-area",
        type=Decimal,
        default=defaults.minimum_upper_floor_area,
    )
    parser.add_argument(
        "--upper-area-step",
        type=Decimal,
        default=defaults.upper_floor_area_step,
    )
    parser.add_argument(
        "--min-pairs",
        type=int,
        default=defaults.minimum_pairs_per_unit,
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=defaults.maximum_pairs_per_unit,
    )
    parser.add_argument(
        "--min-pair-area",
        type=Decimal,
        default=defaults.minimum_pair_room_area,
    )
    parser.add_argument(
        "--max-pair-area",
        type=Decimal,
        default=defaults.maximum_pair_room_area,
    )
    parser.add_argument(
        "--pair-area-step",
        type=Decimal,
        default=defaults.pair_room_area_step,
    )
    parser.add_argument(
        "--planning-margin-rate",
        type=Decimal,
        default=defaults.planning_margin_rate,
        help="Required placement margin as a decimal rate (default: 0.10).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    search_space = replace(
        SearchSpace(),
        minimum_floors=arguments.min_floors,
        maximum_floors=arguments.max_floors,
        minimum_upper_floor_area=arguments.min_upper_area,
        upper_floor_area_step=arguments.upper_area_step,
        minimum_pairs_per_unit=arguments.min_pairs,
        maximum_pairs_per_unit=arguments.max_pairs,
        minimum_pair_room_area=arguments.min_pair_area,
        maximum_pair_room_area=arguments.max_pair_area,
        pair_room_area_step=arguments.pair_area_step,
        planning_margin_rate=arguments.planning_margin_rate,
    )
    analysis = generate_outputs(
        search_space=search_space,
        csv_path=arguments.output_csv,
        markdown_path=arguments.output_markdown,
    )
    print(f"feasible candidates: {analysis.candidate_count:,}")
    print(f"pareto candidates: {len(analysis.pareto_candidates):,}")
    print(
        "planning margin: "
        f"{_display(search_space.planning_margin_rate * Decimal('100'), 1)}%"
    )
    print(f"csv: {arguments.output_csv}")
    print(f"markdown: {arguments.output_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
