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
            "https://www.ritsumei.ac.jp/international/intl_students/life_info/oicdorm/",
            "https://www.ritsumei.ac.jp/file.jsp?id=426078",
            "https://www.ritsumei.ac.jp/file.jsp?id=426397",
            "https://www.ritsumei.ac.jp/international/intl_students/life_info/oicdorm2/",
            "https://global.support.ritsumei.ac.jp/hc/en-us/articles/53446133085075-Short-Term-Residence-at-International-Houses-and-Global-House",
            "https://www.ritsumei.ac.jp/news/detail/?id=998",
            "https://www.ritsumei.ac.jp/news/detail/?id=1253",
            "https://www.jasso.go.jp/ryugaku/related/kouryu/2016/__icsFiles/afieldfile/2021/02/18/201609yamakawafumi.pdf",
            "https://www.jstage.jst.go.jp/article/jusokenronbunjisen/44/0/44_1520/_article/-char/ja/",
            "https://www.mext.go.jp/a_menu/koutou/ryugaku/1412692_00003.htm",
        ):
            self.assertIn(source, self.parser.links)

    def test_dorm_research_does_not_overstate_unmet_demand(self):
        for phrase in (
            "在学生が国籍を問わず、1学期間",
            "2018年度秋学期は81人",
            "現在の供給不足を証明する数字ではない",
            "大学を問わず",
        ):
            self.assertIn(phrase, self.text)

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
            "15.7年",
            "25.3年",
            "土地取得費7億円",
            "正式要件",
            "仮想再提案",
        ):
            self.assertIn(phrase, self.text)

    def test_current_access_and_official_finance_judgment_are_accurate(self):
        self.assertIn("阪急3分", self.text)
        self.assertIn("モノレール5分", self.text)
        self.assertIn("約3.96%", self.text)
        self.assertNotIn("条件内", self.text)

    def test_high_risk_assumptions_are_explicitly_qualified(self):
        for phrase in ("単純計算で360%", "回答者59人", "139室", "満室前提"):
            self.assertIn(phrase, self.text)

    def test_latest_workshop_concept_and_sheet_values_are_reflected(self):
        for phrase in (
            "お互いが、留学先",
            "留学生 × 国内学生",
            "国内留学型の生活基盤",
            "112室",
            "20㎡ × 112室",
            "6階未満",
            "月300万円",
            "2%・15〜20%・10〜15%",
            "食堂・イベントを誰が運営するか",
            "設定意図",
            "テナント収入",
        ):
            self.assertIn(phrase, self.text)

    def test_sources_are_direct_and_site_image_is_local(self):
        external = [
            link for link in self.parser.links if link.startswith("https://")
        ]
        self.assertGreaterEqual(len(external), 5)
        self.assertTrue(all("google.com/search" not in link for link in external))
        self.assertTrue(
            any(
                image.get("src") == "assets/site-detail.png" and image.get("alt")
                for image in self.parser.images
            )
        )
        self.assertTrue((ROOT / "assets/site-detail.png").exists())

    def test_page_has_no_script_or_external_stylesheet(self):
        self.assertNotIn("<script", self.source.lower())
        self.assertNotIn('rel="stylesheet"', self.source.lower())

    def test_finance_table_reflows_on_narrow_screens(self):
        self.assertIn("td::before", self.source)
        self.assertGreaterEqual(self.source.count("data-label="), 12)

    def test_github_pages_entrypoint_points_to_proposal(self):
        index_path = ROOT / "index.html"
        self.assertTrue(index_path.exists(), "GitHub Pages用のindex.htmlが未作成")
        index_source = index_path.read_text(encoding="utf-8")
        self.assertIn('lang="ja"', index_source)
        self.assertIn("proposal.html", index_source)


if __name__ == "__main__":
    unittest.main()
