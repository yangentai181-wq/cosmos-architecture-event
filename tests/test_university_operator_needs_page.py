from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UniversityOperatorNeedsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.lang = None
        self.text = []
        self.tags = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append(tag)
        if tag in {"style", "script"}:
            self._ignored_depth += 1
        if tag == "html":
            self.lang = values.get("lang")
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])

    def handle_data(self, data):
        if not self._ignored_depth:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self._ignored_depth:
            self._ignored_depth -= 1


class UniversityOperatorNeedsPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "needs" / "university" / "index.html"
        cls.source = cls.path.read_text(encoding="utf-8") if cls.path.exists() else ""
        cls.parser = UniversityOperatorNeedsParser()
        cls.parser.feed(cls.source)
        cls.text = " ".join(cls.parser.text)

    def test_route_is_japanese_and_connected_to_the_needs_sequence(self):
        self.assertTrue(self.path.exists(), "needs/university/index.html が未作成")
        self.assertEqual(self.parser.lang, "ja")
        self.assertIn('name="viewport"', self.source)
        self.assertIn("ワークシート②−③", self.text)
        self.assertIn("../", self.parser.links)
        self.assertIn("../parents/", self.parser.links)
        self.assertIn("../../proposal.html", self.parser.links)

        student_source = (ROOT / "needs" / "index.html").read_text(encoding="utf-8")
        parent_source = (ROOT / "needs" / "parents" / "index.html").read_text(
            encoding="utf-8"
        )
        student_parser = UniversityOperatorNeedsParser()
        parent_parser = UniversityOperatorNeedsParser()
        student_parser.feed(student_source)
        parent_parser.feed(parent_source)
        self.assertIn("./university/", student_parser.links)
        self.assertIn("../university/", parent_parser.links)

    def test_reasoning_and_decision_sections_are_addressable(self):
        required = {
            "overview",
            "role-split",
            "current-conditions",
            "finance-basis",
            "evidence-chain",
            "university-needs",
            "operator-needs",
            "responsibility",
            "metrics",
            "tradeoffs",
            "worksheet",
            "validation",
            "sources",
        }
        self.assertTrue(required.issubset(set(self.parser.ids)), required - set(self.parser.ids))
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)), "idが重複している")
        self.assertIn("main", self.parser.tags)
        self.assertIn("nav", self.parser.tags)

    def test_university_and_operator_are_not_treated_as_one_actor(self):
        for phrase in (
            "大学 ≠ 運営者",
            "大学連携は合意済みではない",
            "大学は送客を保証しない",
            "既存2寮との役割分担",
            "教育成果",
            "継続できる事業収支",
            "責任分界",
        ):
            self.assertIn(phrase, self.text)

    def test_local_conditions_are_kept_separate_from_unproven_demand(self):
        for phrase in (
            "歴史的な仮想再提案",
            "OICには2つの国際寮",
            "合計369室",
            "139室",
            "112室満室前提",
            "月300万円",
            "100ペア室・200人",
            "土地込み利回り2.83%",
            "1人月8万9,146円",
            "食費・光熱・ネット等を含まない",
            "募集ページ上の満室は長期需要の証明ではない",
            "混住そのものは差別化にならない",
            "「お互いが、留学先」は仮コンセプト",
            "就職実績・大学ブランドへの効果は未確認",
            "大学は一時的な授業しか提供できない",
            "確認済み",
            "根拠のある推論",
            "未検証仮説",
        ):
            self.assertIn(phrase, self.text)

        self.assertNotIn("合計368室", self.text)

        for finance_evidence in (
            "建設費12億2,410万円",
            "土地代7億円",
            "年間利益5,435.9万円",
            "100,000円 × 100室 × 95% × 12か月",
            "19億2,410万円 × 7%",
            "内部モデルの再現",
        ):
            self.assertIn(finance_evidence, self.text)

        for inferred_condition in (
            "大学方針とは方向が合う",
            "周辺との摩擦は大学の評判にも返る",
        ):
            marker = '<span class="badge inference">根拠のある推論</span>'
            condition_start = self.source.rfind('<article class="condition">', 0, self.source.find(inferred_condition))
            condition_end = self.source.find("</article>", self.source.find(inferred_condition))
            self.assertIn(marker, self.source[condition_start:condition_end])

    def test_responsibility_and_metrics_cover_outcomes_burden_and_risk(self):
        for phrase in (
            "入居率",
            "更新率",
            "中途退去率",
            "相談解決時間",
            "近隣苦情",
            "プログラム参加率だけで評価しない",
            "本人同意",
            "事故・病気・災害",
            "食堂運営主体",
            "RA・RM相当",
            "所有者・開発者",
            "医療判断・警備・法定管理",
            "常駐・電話受付・警備会社駆付け",
        ):
            self.assertIn(phrase, self.text)

    def test_sources_are_direct_and_local_links_resolve(self):
        external_links = [link for link in self.parser.links if link.startswith("https://")]
        self.assertGreaterEqual(len(external_links), 7)
        self.assertTrue(all("google.com/search" not in link for link in external_links))
        official_hosts = {
            "www.ritsumei.ac.jp",
            "www.jasso.go.jp",
            "www.mlit.go.jp",
            "www.ppc.go.jp",
            "www.fdma.go.jp",
            "www.pref.osaka.lg.jp",
        }
        self.assertTrue(official_hosts.issubset({urlsplit(link).netloc for link in external_links}))

        for link in self.parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or link.startswith("#"):
                continue
            local_target = (self.path.parent / parsed.path).resolve()
            self.assertTrue(local_target.exists(), f"ローカルリンク切れ: {link}")

        self.assertNotIn("<script", self.source.lower())
        self.assertNotIn('rel="stylesheet"', self.source.lower())
        self.assertNotIn("<img", self.source.lower())

    def test_page_supports_mobile_print_and_long_source_urls(self):
        self.assertIn("@media (max-width:", self.source)
        self.assertIn("@media print", self.source)
        self.assertIn("overflow-wrap: anywhere", self.source)
        print_css = self.source.partition("@media print")[2]
        self.assertIn("--dark-accent: #111", print_css)
        self.assertIn(".gate p {\n        color: #111;", print_css)
        self.assertIn(".table-wrap {\n        overflow: visible;", print_css)
        self.assertIn("table {\n        min-width: 0;", print_css)


if __name__ == "__main__":
    unittest.main()
