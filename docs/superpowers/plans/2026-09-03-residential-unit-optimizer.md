# Residential Unit Optimizer Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** ユーザー合意済みの寮ユニット条件を有限総当たりし、既存Google収支計算表を再現したうえで、収支最大案・空間品質との比較案・パレート解をローカル成果物として生成する。

**Architecture:** `tools/residential_optimizer.py` に面積・設備・収支・探索を副作用のない関数として集約し、`tools/generate_residential_optimization.py` がそれを呼び出してCSVとMarkdownを生成する。探索条件は不変データとして一か所に置き、Google Sheetへは書き込まない。既存HTMLと未コミット文書は変更しない。

**Tech Stack:** Python 3.14標準ライブラリ（`dataclasses`, `decimal`, `csv`, `argparse`, `math`, `pathlib`, `unittest`）

---

## 前提と実装判断

- 詳細仕様は `docs/superpowers/specs/2026-09-03-residential-unit-optimizer-design.md` を正とする。
- 現在の作業ブランチ `feat/optimize-dorm-units` を使い、ユーザーの既存未コミット変更を保持する。
- 外部依存は追加しない。有限列挙で厳密に解けるため、OR-Tools、PuLP、SciPyは導入しない。
- テストを先に書き、期待した失敗を確認してから実装する。
- 金額は万円、面積は㎡。計算内部は `Decimal` を使い、CSV表示時だけ所定桁へ丸める。

### Task 1: 収支表再現テストをREDにする

**Files:**
- Create: `tests/test_residential_optimizer.py`
- Create later: `tools/residential_optimizer.py`

**Step 1: Write the failing test**

次をテストへ記述する。

- 現行表の入力 `private=2250`, `purpose=810`, `corridor=540`, `rooms=112` を渡す。
- 建設コストが `115410` 万円。
- 年間利益が `7341.9` 万円。
- 回収年数が約 `15.7194` 年。
- 利回りが約 `6.36158%`。

**Step 2: Run test to verify it fails**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.FinanceModelTest -v`
Expected: `ModuleNotFoundError` または未実装関数によるERROR。テスト記述の構文エラーではないことを確認する。

**Step 3: Write minimal implementation**

`tools/residential_optimizer.py` に以下を実装する。

- `FinanceAssumptions`
- `FinanceResult`
- `calculate_finance(private_area, purpose_area, corridor_area, room_count, assumptions)`

既存表と同じ項目・式だけを用いる。

**Step 4: Run test to verify it passes**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.FinanceModelTest -v`
Expected: 対象テストがPASS、終了コード0。

### Task 2: ユニット設備・面積テストをREDからGREENにする

**Files:**
- Modify: `tests/test_residential_optimizer.py`
- Modify: `tools/residential_optimizer.py`

**Step 1: Write the failing tests**

- 2ペア4人はトイレ・シャワー・洗面・洗濯が各1。
- 3ペア6人はトイレ・シャワー・洗面が各2、洗濯が2。
- 8ペア16人はトイレ・シャワー・洗面・洗濯が各4。
- リビング面積の1人あたり下限・上限フィルタが効く。
- ユニット必要面積が、ペア室・共用設備・内部動線12%をすべて含む。

**Step 2: Run test to verify it fails**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.UnitModelTest -v`
Expected: 未実装属性・関数によるFAILまたはERROR。

**Step 3: Write minimal implementation**

以下を実装する。

- `UnitAssumptions`
- `FixtureCounts`
- `UnitAreaResult`
- `fixture_counts(pairs_per_unit)`
- `living_area_candidates(pairs_per_unit)`
- `calculate_unit_area(pairs_per_unit, pair_room_area, living_area, assumptions)`

**Step 4: Run test to verify it passes**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.UnitModelTest -v`
Expected: 対象テストがPASS、終了コード0。

### Task 3: 建物候補と外周代理チェックをREDからGREENにする

**Files:**
- Modify: `tests/test_residential_optimizer.py`
- Modify: `tools/residential_optimizer.py`

**Step 1: Write the failing tests**

- `first_floor_area = 3600 - upper_floor_area × residential_floor_count` を満たす。
- 各階800㎡以下、上階は1階以下。
- 廊下等合計が常に540㎡。
- 専有・目的共用・廊下等の合計が3,600㎡。
- 部屋数は `上階数 × 1フロアユニット数 × 1ユニットペア数` の整数。
- 外周代理チェックが、必要間口超過を除外する。

**Step 2: Run test to verify it fails**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.BuildingModelTest -v`
Expected: 未実装関数によるFAILまたはERROR。

**Step 3: Write minimal implementation**

以下を実装する。

- `SearchSpace`
- `Candidate`
- `upper_floor_area_candidates(total_floors, search_space)`
- `available_facade_length(upper_floor_area, aspect_ratio, usable_ratio)`
- `build_candidate(...)`

不成立理由は `None` だけで捨てず、必要に応じてテスト可能な判定関数へ分ける。

**Step 4: Run test to verify it passes**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.BuildingModelTest -v`
Expected: 対象テストがPASS、終了コード0。

### Task 4: 総当たり探索・代表案・パレート抽出をREDからGREENにする

**Files:**
- Modify: `tests/test_residential_optimizer.py`
- Modify: `tools/residential_optimizer.py`

**Step 1: Write the failing tests**

縮小した探索範囲を使い、次を検証する。

- すべての返却候補が面積・外周・整数条件を満たす。
- 結果順が決定的で、同じ入力から同じ先頭候補を返す。
- 収支最大、推奨バランス、小ユニット、空間ゆとりの選択条件が守られる。
- パレート解の各候補が、別候補に3指標すべてで支配されていない。

**Step 2: Run test to verify it fails**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.SearchTest -v`
Expected: 探索関数未実装によるFAILまたはERROR。

**Step 3: Write minimal implementation**

以下を実装する。

- `iter_candidates(search_space, finance_assumptions, unit_assumptions)`
- `select_representative_candidates(candidates)`
- `pareto_frontier(candidates)`

探索中に全候補を無制限に複製せず、必要な候補データだけを保持する。候補数と採用数を集計する。

**Step 4: Run test to verify it passes**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.SearchTest -v`
Expected: 対象テストがPASS、終了コード0。

### Task 5: CSV・Markdown生成をREDからGREENにする

**Files:**
- Modify: `tests/test_residential_optimizer.py`
- Create: `tools/generate_residential_optimization.py`
- Generate: `artifacts/residential-unit-optimization-pareto.csv`
- Generate: `docs/residential-unit-optimization-results-2026-09-03.md`

**Step 1: Write the failing tests**

- CLIを縮小探索で一時ディレクトリへ実行できる。
- CSVに、階数、上下階面積、ペア室面積、ペア/ユニット、ユニット/階、リビング、設備数、面積内訳、室数、居住者数、建設コスト、年間利益、回収年数、利回り、外周余裕を出す。
- Markdownに、前提、現行表再現、代表4案、パレート件数、再実行コマンド、法規・平面未検証の留保を出す。

**Step 2: Run test to verify it fails**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.ReportTest -v`
Expected: CLIまたは生成関数未実装によるFAILまたはERROR。

**Step 3: Write minimal implementation**

`tools/generate_residential_optimization.py` に以下を実装する。

- 引数なしで正式範囲を探索。
- `--output-csv`, `--output-markdown` で出力先を変更可能。
- テスト用に各探索上限・刻みを引数で縮小可能。
- 生成物に実行日時ではなく固定仕様日を記載し、同じ入力で差分が安定するようにする。

**Step 4: Run test to verify it passes**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer.ReportTest -v`
Expected: 対象テストがPASS、終了コード0。

### Task 6: 正式探索を実行して結果を監査する

**Files:**
- Verify: `artifacts/residential-unit-optimization-pareto.csv`
- Verify: `docs/residential-unit-optimization-results-2026-09-03.md`

**Step 1: Run full optimization**

Run: `/opt/homebrew/bin/python3 tools/generate_residential_optimization.py`
Expected: 面積・外周条件を通過した成立候補数、パレート件数、2つの出力先を表示し、終了コード0。

**Step 2: Audit generated invariants**

Run: `/opt/homebrew/bin/python3 -m unittest tests.test_residential_optimizer -v`
Expected: 今回追加した全テストがPASS、終了コード0。

CSVを機械的に読み、次を確認する。

- 総延床3,600㎡
- 1階住居0
- 廊下等540㎡
- 全代表案の面積差0
- 設備数が `ceil(居住者/4)` 等と一致
- 推奨案の3つの品質条件
- 利回り降順・同率時の決定順

**Step 3: Compare with spreadsheet baseline**

現行112室案と代表案について、建設コスト、年間利益、回収年数、利回りの差を報告書内で確認する。収支表にない項目を正式結果へ混ぜていないことを確認する。

### Task 7: 全体回帰と変更範囲を検証する

**Files:**
- Verify only: repository-wide tests and diff

**Step 1: Run all tests**

Run: `/opt/homebrew/bin/python3 -m unittest discover -s tests -v`
Expected: 既存17件と今回追加分がすべてPASS、終了コード0。

**Step 2: Run static checks**

Run: `/opt/homebrew/bin/python3 -m py_compile tools/residential_optimizer.py tools/generate_residential_optimization.py`
Expected: 無出力、終了コード0。

Run: `git diff --check`
Expected: 無出力、終了コード0。

**Step 3: Scope audit**

Run: `git status --short`
Expected: 今回の新規ファイルに加えて着手前からのユーザー変更が残る。`index.html`、`proposal.html`、既存テスト・既存文書を今回の作業で変更していないことを確認する。

### Task 8: 独立レビューと完了報告

**Files:**
- Review: all new optimizer files and generated outputs

**Step 1: Request read-only reviews**

- KOKO: 既存収支表への準拠、丸め、基準値再現、収支上の誤解を確認。
- IZMまたはrequirements-checker: ユーザー合意事項、計画、実ファイル、テスト証拠の一致を確認。

重大指摘があれば最小修正し、関係テストと全体テストを再実行する。

**Step 2: Report completion**

次を日本語で簡潔に報告する。

- 生成した計画書、実装、結果ファイルへのリンク
- 収支最大案と推奨バランス案の主要数値
- 基準表を再現できたこと
- 実行した検証、件数、終了コード
- 平面・法規・階数割増・食堂運営が未検証であること
- Google Sheet、既存HTML、外部環境へ書き込んでいないこと
