from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NeedsPageParser(HTMLParser):
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


class StudentNeedsPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "needs" / "index.html"
        cls.source = cls.path.read_text(encoding="utf-8") if cls.path.exists() else ""
        cls.parser = NeedsPageParser()
        cls.parser.feed(cls.source)
        cls.text = " ".join(cls.parser.text)

    def test_page_is_a_standalone_japanese_pages_route(self):
        self.assertTrue(self.path.exists(), "needs/index.html が未作成")
        self.assertEqual(self.parser.lang, "ja")
        self.assertIn('name="viewport"', self.source)
        self.assertIn("ワークシート②−①", self.text)
        self.assertIn("../proposal.html", self.parser.links)

    def test_reasoning_chain_is_visible_as_page_sections(self):
        required = {
            "overview",
            "target",
            "conditions",
            "evidence-chain",
            "prioritized-needs",
            "segments",
            "worksheet",
            "boundaries",
            "validation",
            "sources",
        }
        self.assertTrue(required.issubset(self.parser.ids), required - self.parser.ids)

    def test_evidence_strength_and_key_observations_are_preserved(self):
        for phrase in (
            "確認済み",
            "根拠のある推論",
            "未検証仮説",
            "78.9%",
            "67.3%",
            "43.3%",
            "2.5%",
            "3.1%",
            "64,200円",
            "66,976円",
            "10万6,200〜11万7,700円",
            "原則1年",
            "配布資料の「学生の声」は保護者回答",
            "一人になれる居場所",
            "高等教育機関在籍の私費外国人留学生",
            "ニーズの確度",
            "歴史的な仮想再提案",
        ):
            self.assertIn(phrase, self.text)

        for stale_total in ("77.7%", "66.9%", "42.6%", "2.7%", "2.9%"):
            self.assertNotIn(stale_total, self.text)

        reasoning_source = self.source.split('id="evidence-chain"', 1)[1].split(
            'id="prioritized-needs"', 1
        )[0]
        self.assertNotIn("confidence verified", reasoning_source)

    def test_concept_is_not_misrepresented_as_proven_demand(self):
        for phrase in (
            "お互いが、留学先",
            "長期入居需要は未確認",
            "追加家賃を払う意思",
            "相部屋を標準にしない",
            "住居として成立",
            "選べる付加価値",
        ):
            self.assertIn(phrase, self.text)

    def test_sources_are_direct_and_page_has_no_runtime_dependency(self):
        external_links = [
            link for link in self.parser.links if link.startswith("https://")
        ]
        self.assertGreaterEqual(len(external_links), 7)
        self.assertTrue(all("google.com/search" not in link for link in external_links))
        self.assertNotIn("<script", self.source.lower())
        self.assertNotIn('rel="stylesheet"', self.source.lower())

    def test_page_supports_mobile_and_print_review(self):
        self.assertIn("@media (max-width:", self.source)
        self.assertIn("@media print", self.source)
        self.assertIn("overflow-wrap: anywhere", self.source)


if __name__ == "__main__":
    unittest.main()
