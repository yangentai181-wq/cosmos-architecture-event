from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProposalParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.images = []
        self.lang = None
        self.text = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self._ignored_depth += 1
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "img":
            self.images.append(values)

    def handle_data(self, data):
        if not self._ignored_depth:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self._ignored_depth:
            self._ignored_depth -= 1


class ProposalHtmlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "proposal.html"
        cls.source = cls.path.read_text(encoding="utf-8") if cls.path.exists() else ""
        cls.parser = ProposalParser()
        cls.parser.feed(cls.source)
        cls.text = " ".join(cls.parser.text)

    def test_deliverable_exists_and_is_japanese_html(self):
        self.assertTrue(self.path.exists(), "proposal.html が未作成")
        self.assertEqual(self.parser.lang, "ja")
        self.assertIn('name="viewport"', self.source)

    def test_required_reasoning_sections_exist(self):
        required = {
            "summary",
            "facts",
            "dorm-research",
            "logic",
            "swot",
            "value",
            "plan",
            "site",
            "finance",
            "evidence",
            "decisions",
        }
        self.assertTrue(required.issubset(self.parser.ids), required - self.parser.ids)

    def test_dorm_research_is_reachable_and_links_primary_evidence(self):
        self.assertIn("#dorm-research", self.parser.links)
        for source in (
            "https://www.studyinjapan.go.jp/ja/_mt/2024/10/Seikatsu2023.pdf",
            "https://www.mlit.go.jp/jutakukentiku/house/content/001612669.pdf",
            "https://en.ritsumei.ac.jp/lifecareer/dorm/oic/",
            "https://www.ritsumei.ac.jp/international/intl_students/life_info/oicdorm2/",
            "https://www.jasso.go.jp/ryugaku/related/kouryu/2016/__icsFiles/afieldfile/2021/02/18/201609yamakawafumi.pdf",
            "https://www.jstage.jst.go.jp/article/jusokenronbunjisen/44/0/44_1520/_article/-char/ja/",
            "https://www.mext.go.jp/a_menu/koutou/ryugaku/1412692_00003.htm",
        ):
            self.assertIn(source, self.parser.links)

    def test_completed_needs_and_validation_routes_are_reachable(self):
        for route in (
            "needs/",
            "needs/parents/",
            "validation/",
            "interest/",
        ):
            self.assertIn(route, self.parser.links)

    def test_swot_and_strategy_conversion_are_complete(self):
        for phrase in (
            "Strengths",
            "Weaknesses",
            "Opportunities",
            "Threats",
            "SO戦略",
            "WO戦略",
            "ST戦略",
            "WT戦略",
            "判断のスナップショット",
        ):
            self.assertIn(phrase, self.text)
        self.assertGreaterEqual(self.source.count('class="swot-card'), 4)
        self.assertGreaterEqual(self.source.count('class="strategy-card'), 4)

    def test_certainty_and_finance_caveat_are_visible(self):
        for phrase in (
            "確認済み",
            "解釈",
            "仮説・未検証",
            "13.85年",
            "14.85年",
            "土地取得費7億円",
            "正式要件",
            "仮想再提案",
        ):
            self.assertIn(phrase, self.text)

    def test_operating_cost_interpretations_are_not_conflated(self):
        for phrase in (
            "運営費は足し算しない",
            "共同住宅99戸",
            "15%を包括費として置換",
            "4.61%",
            "20%を包括費として置換",
            "4.30%",
            "食堂10〜15%は算入保留",
            "法規比較値では、楽観的な比較でも7%未達",
        ):
            self.assertIn(phrase, self.text)

    def test_capital_bridge_shows_zero_land_limit(self):
        self.assertIn('id="capital-bridge"', self.source)
        for phrase in (
            "7%許容投資",
            "土地を0円としても現在の建設費だけで7%へ届かない",
            "9億9,374.3万円",
            "10億6,162.9万円",
            "10億9,634.3万円",
            "採否基準自体を再設定する",
        ):
            self.assertIn(phrase, self.text)

    def test_annual_total_costs_are_compared_on_a_visible_basis(self):
        for phrase in (
            "年間総負担を同じ軸で比べる",
            "I-House",
            "77.04万円",
            "G-House",
            "89.04万円",
            "コスモグラシア南茨木",
            "138.84〜153.24万円",
            "家賃だけで年120万円",
            "7%達成に必要な家賃だけで年174.99〜207.79万円",
            "費目が同じではない",
        ):
            self.assertIn(phrase, self.text)

    def test_tenant_income_is_not_assumed_before_a_contract(self):
        for phrase in (
            "テナント収入は契約形態で分ける",
            "固定賃貸借",
            "最低保証＋歩合",
            "運営委託",
            "短期利用・ポップアップ",
            "年間4,395.7〜7,431.4万円",
            "月366.3〜619.3万円",
            "契約前は0円",
            "公開165㎡との競合",
        ):
            self.assertIn(phrase, self.text)

    def test_morning_decision_is_explicit(self):
        for phrase in (
            "朝の判断",
            "残す｜お互いが、留学先",
            "進める｜5・6・7階 × B1/B2",
            "止める｜建設案の確定",
            "外部回答前は確定しない",
            "7%目標を維持するなら、事業条件を変える",
        ):
            self.assertIn(phrase, self.text)

    def test_current_access_and_official_finance_judgment_are_accurate(self):
        self.assertIn("阪急3分", self.text)
        self.assertIn("モノレール5分", self.text)
        self.assertIn("6.73%", self.text)
        self.assertNotIn("条件内", self.text)

    def test_construction_cost_is_not_presented_as_a_quote(self):
        proposal = self.text
        validation = (ROOT / "validation/index.html").read_text(encoding="utf-8")
        for document in (proposal, validation):
            self.assertIn("32.06万円/㎡", document)
            self.assertIn("36.47万円/㎡", document)
            self.assertIn("案件見積では", document)
        self.assertIn("土地込み利回りは6.12%", proposal)
        self.assertIn("建設費の含有・除外表と敷地固有費", proposal)

    def test_high_risk_assumptions_are_explicitly_qualified(self):
        for phrase in ("単純計算で360%", "回答者59人", "139室", "満室は理論上限"):
            self.assertIn(phrase, self.text)

    def test_latest_workshop_concept_and_sheet_values_are_reflected(self):
        for phrase in (
            "お互いが、留学先",
            "留学生 × 国内学生",
            "国内留学型の生活基盤",
            "168室",
            "設計検討幅は84〜99室",
            "24ユニット",
            "13.39㎡",
            "Day2判断表",
            "月300万円",
            "2%・15〜20%・10〜15%",
            "食堂・イベントを誰が運営するか",
            "設定意図",
            "テナント収入",
        ):
            self.assertIn(phrase, self.text)

    def test_three_event_programs_have_operating_conditions(self):
        for phrase in (
            "2つの定例候補＋1つの段階実証",
            "南茨木・多言語防災まち歩き",
            "約25人・90分",
            "学生ペアの学校派遣",
            "1学級・授業1コマ",
            "お互い食堂",
            "居住者12人→招待制18人→外部24人",
            "次の活動への申込30%以上",
            "売上は基本収支へ入れない",
            "食品衛生",
        ):
            self.assertIn(phrase, self.text)

    def test_event_pilot_returns_measured_constraints_to_design(self):
        self.assertIn("event-pilot-measurement", self.parser.ids)
        for phrase in (
            "24人を図面の根拠に変える",
            "受付列・最小通路・居住動線との交差",
            "避難閉塞・専用部侵入は即時停止",
            "運営で解けない寸法だけを165㎡へ戻す",
            "同じ人数条件を2回再現",
        ):
            self.assertIn(phrase, self.text)

    def test_open_corner_design_is_visible_and_uses_a_local_diagram(self):
        self.assertIn("open-corner-design", self.parser.ids)
        self.assertIn("街角にひらく、奥で暮らす", self.text)
        for phrase in (
            "基準165㎡",
            "寄宿舎案では345㎡",
            "共同住宅案では464㎡",
            "目的共用部810㎡の内訳",
        ):
            self.assertIn(phrase, self.text)
        self.assertTrue(
            any(
                image.get("src") == "assets/open-corner-design.svg"
                and image.get("alt")
                for image in self.parser.images
            )
        )
        diagram_path = ROOT / "assets/open-corner-design.svg"
        self.assertTrue(diagram_path.exists())
        self.assertIn("基準165㎡", diagram_path.read_text(encoding="utf-8"))

    def test_site_specific_corner_comparison_keeps_both_locations_open(self):
        self.assertIn("site-specific-corner-test", self.parser.ids)
        for phrase in (
            "B1 交差点寄り",
            "B2 道路中央",
            "同じ165㎡・同じ外構条件で比較",
            "位置は未確定",
        ):
            self.assertIn(phrase, self.text)
        self.assertTrue(
            any(
                image.get("src") == "assets/site-specific-b-comparison.svg"
                and image.get("alt")
                for image in self.parser.images
            )
        )
        diagram_path = ROOT / "assets/site-specific-b-comparison.svg"
        self.assertTrue(diagram_path.exists())
        self.assertIn("基準165㎡", diagram_path.read_text(encoding="utf-8"))

    def test_first_floor_program_closes_the_area_and_route_logic(self):
        self.assertIn("first-floor-165-program", self.parser.ids)
        for phrase in (
            "165㎡の内部構成",
            "65＋35＋18＋20＋27＝165㎡",
            "公開部だけを閉鎖",
            "外部利用者・居住者・搬入を分離",
        ):
            self.assertIn(phrase, self.text)
        self.assertTrue(
            any(
                image.get("src") == "assets/first-floor-165-program.svg"
                and image.get("alt")
                for image in self.parser.images
            )
        )
        diagram_path = ROOT / "assets/first-floor-165-program.svg"
        self.assertTrue(diagram_path.exists())
        diagram = diagram_path.read_text(encoding="utf-8")
        for phrase in ("ラウンジ 65㎡", "キッチン 35㎡", "管理・収納・清掃 27㎡"):
            self.assertIn(phrase, diagram)

    def test_facade_operation_modes_make_open_and_closed_states_explicit(self):
        self.assertIn("facade-operation-modes", self.parser.ids)
        for phrase in (
            "建築の開放性は時間で切り替える",
            "平常日",
            "イベント中",
            "終了後",
            "夜間帰宅",
            "公開交流棟だけを閉鎖",
        ):
            self.assertIn(phrase, self.text)
        self.assertTrue(
            any(
                image.get("src") == "assets/facade-operation-modes.svg"
                and image.get("alt")
                for image in self.parser.images
            )
        )
        diagram_path = ROOT / "assets/facade-operation-modes.svg"
        self.assertTrue(diagram_path.exists())
        diagram = diagram_path.read_text(encoding="utf-8")
        for phrase in ("平常日", "イベント中", "終了後", "夜間帰宅"):
            self.assertIn(phrase, diagram)
        brief_path = ROOT / "docs/facade-operation-brief-2026-09-04.md"
        self.assertTrue(brief_path.exists())
        self.assertIn("公開交流棟だけを閉鎖", brief_path.read_text(encoding="utf-8"))

    def test_single_room_unit_branch_is_explicitly_a_comparison(self):
        self.assertIn("seven-person-unit-branch", self.parser.ids)
        for phrase in (
            "7個室＋共有リビング",
            "3ユニット×4層＝84個室",
            "上階可用510㎡",
            "配置余裕35.8㎡",
            "シート継承2.42%",
            "保守再算定2.32%",
            "同じ158.07㎡は偶然一致",
            "採用案ではない",
        ):
            self.assertIn(phrase, self.text)
        self.assertTrue(
            any(
                image.get("src") == "assets/seven-person-unit.svg"
                and image.get("alt")
                for image in self.parser.images
            )
        )
        diagram_path = ROOT / "assets/seven-person-unit.svg"
        self.assertTrue(diagram_path.exists())
        self.assertIn("共有リビング 24.5㎡", diagram_path.read_text(encoding="utf-8"))

    def test_equal_program_massing_reopens_floor_count_without_selecting_a_winner(self):
        self.assertIn("equal-program-massing", self.parser.ids)
        for phrase in (
            "同じ84室で、5・6・7階を比較する",
            "7階を最初に描く",
            "優位案ではない",
            "最大投影面積",
            "階数別の建設・運営費",
        ):
            self.assertIn(phrase, self.text)
        self.assertTrue(
            any(
                image.get("src") == "assets/equal-program-massing-comparison.svg"
                and image.get("alt")
                for image in self.parser.images
            )
        )

    def test_hero_leads_with_live_room_options_not_rejected_upper_bound(self):
        self.assertIn(
            '<span class="snapshot-label">ROOM OPTIONS</span><strong class="snapshot-value">84 / 91 / 99</strong><span class="snapshot-note">設計比較・行政確認前</span>',
            self.source,
        )
        self.assertNotIn(
            '<span class="snapshot-label">ROOMS</span><strong class="snapshot-value">168室</strong>',
            self.source,
        )
        self.assertIn("建物形状は優位未確定", self.text)
        self.assertNotIn("5階案を数値検証済み", self.text)

    def test_sources_are_direct_and_site_visual_is_original(self):
        self.assertIn("I-House 168室とG-House 201室", self.text)
        self.assertIn("合計369室", self.text)
        self.assertIn("既知の初年度最低84.54万円", self.text)
        self.assertNotIn("既知の初年度最低84.46万円", self.text)
        external = [
            link for link in self.parser.links if link.startswith("https://")
        ]
        self.assertGreaterEqual(len(external), 5)
        self.assertTrue(all("google.com/search" not in link for link in external))
        self.assertIn("公開用の模式図", self.text)
        self.assertFalse(
            any(image.get("src") == "assets/site-detail.png" for image in self.parser.images)
        )
        self.assertFalse((ROOT / "assets/site-detail.png").exists())

    def test_page_has_no_script_or_external_stylesheet(self):
        self.assertNotIn("<script", self.source.lower())
        self.assertNotIn('rel="stylesheet"', self.source.lower())

    def test_finance_table_reflows_on_narrow_screens(self):
        self.assertIn("td::before", self.source)
        self.assertGreaterEqual(self.source.count("data-label="), 12)
        self.assertGreaterEqual(
            self.source.count('class="finance-table-wrap"'),
            2,
            "収益セクション内の表は既存のスマホ用ラッパーを使う",
        )

    def test_github_pages_entrypoint_points_to_proposal(self):
        index_path = ROOT / "index.html"
        self.assertTrue(index_path.exists(), "GitHub Pages用のindex.htmlが未作成")
        index_source = index_path.read_text(encoding="utf-8")
        self.assertIn('lang="ja"', index_source)
        self.assertIn("proposal.html", index_source)


if __name__ == "__main__":
    unittest.main()
