from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ParentNeedsPageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.lang = None
        self.text = []
        self._ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"style", "script"}:
            self._ignored_depth += 1
        if tag == "html":
            self.lang = values.get("lang")
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])

    def handle_data(self, data):
        if not self._ignored_depth:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self._ignored_depth:
            self._ignored_depth -= 1


class ParentNeedsPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "needs" / "parents" / "index.html"
        cls.source = cls.path.read_text(encoding="utf-8") if cls.path.exists() else ""
        cls.parser = ParentNeedsPageParser()
        cls.parser.feed(cls.source)
        cls.text = " ".join(cls.parser.text)

    def test_route_is_japanese_and_reachable_from_student_needs(self):
        self.assertTrue(self.path.exists(), "needs/parents/index.html が未作成")
        self.assertEqual(self.parser.lang, "ja")
        self.assertIn('name="viewport"', self.source)
        self.assertIn("ワークシート②−②", self.text)
        self.assertIn("../", self.parser.links)
        self.assertIn("../../proposal.html", self.parser.links)

        student_source = (ROOT / "needs" / "index.html").read_text(encoding="utf-8")
        student_parser = ParentNeedsPageParser()
        student_parser.feed(student_source)
        self.assertIn("./parents/", student_parser.links)

    def test_reasoning_flow_is_visible_as_page_sections(self):
        required = {
            "overview",
            "role-split",
            "source-correction",
            "conditions",
            "evidence-chain",
            "prioritized-needs",
            "tradeoffs",
            "segments",
            "worksheet",
            "validation",
            "sources",
        }
        self.assertTrue(required.issubset(self.parser.ids), required - self.parser.ids)

    def test_current_parent_evidence_and_local_costs_are_preserved(self):
        for phrase in (
            "55,076人",
            "75.7%",
            "67.5%",
            "61.4%",
            "49.1%",
            "61,730円",
            "245,050円",
            "43,190円",
            "332,740円",
            "10万5,700〜11万7,200円",
            "10万6,200〜11万7,700円",
            "138万8,400〜153万2,400円",
            "管理人日勤",
            "医療機関への同伴はRMの業務外",
            "大阪中央環状線",
            "夜間動線",
            "敷地境界の騒音・浸水条件は未確定",
        ):
            self.assertIn(phrase, self.text)

        for wrong_regional_value in ("52,450円", "185,350円"):
            self.assertNotIn(wrong_regional_value, self.text)

    def test_parent_roles_and_evidence_strength_are_not_conflated(self):
        for phrase in (
            "保護者・保証人・費用負担者は同じとは限らない",
            "18歳で成年",
            "本人の同意",
            "確認済み",
            "根拠のある推論",
            "未検証仮説",
            "南茨木の保護者への直接調査は未実施",
            "国際交流への追加支払意思は未確認",
            "歴史的な仮想再提案",
        ):
            self.assertIn(phrase, self.text)

        reasoning_source = self.source.partition('id="evidence-chain"')[2].partition(
            'id="prioritized-needs"'
        )[0]
        self.assertNotIn("confidence verified", reasoning_source)

    def test_page_sets_safety_privacy_and_support_boundaries(self):
        for phrase in (
            "設備ではなく責任表",
            "日常監視をしない",
            "連絡条件を先に合意",
            "24時間対応は未確認",
            "交流は安全・費用・健康の後",
            "食事提供と健康保証は同義ではない",
        ):
            self.assertIn(phrase, self.text)

    def test_sources_are_direct_and_page_has_no_runtime_dependency(self):
        external_links = [
            link for link in self.parser.links if link.startswith("https://")
        ]
        self.assertGreaterEqual(len(external_links), 6)
        self.assertTrue(all("google.com/search" not in link for link in external_links))
        self.assertNotIn("<script", self.source.lower())
        self.assertNotIn('rel="stylesheet"', self.source.lower())

    def test_page_supports_mobile_and_print_review(self):
        self.assertIn("@media (max-width:", self.source)
        self.assertIn("@media print", self.source)
        self.assertIn("overflow-wrap: anywhere", self.source)

        print_css = self.source.partition("@media print")[2]
        self.assertIn("--dark-accent: #111", print_css)
        self.assertGreaterEqual(self.source.count("color: var(--dark-accent)"), 7)


if __name__ == "__main__":
    unittest.main()
