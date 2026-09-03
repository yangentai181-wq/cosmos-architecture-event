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

    def handle_starttag(self, tag, attrs):
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
        self.text.append(data)


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
            "logic",
            "value",
            "plan",
            "site",
            "finance",
            "evidence",
            "decisions",
        }
        self.assertTrue(required.issubset(self.parser.ids), required - self.parser.ids)

    def test_certainty_and_finance_caveat_are_visible(self):
        for phrase in (
            "確認済み",
            "解釈",
            "仮説・未検証",
            "13.6年",
            "22.1年",
            "土地取得費7億円",
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


if __name__ == "__main__":
    unittest.main()
