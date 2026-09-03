from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CommunityNeedsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.lang = None
        self.tags = []
        self.evidence_levels = []
        self.stakeholders = []
        self.priority_evidence = []
        self.kpi_fields = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        self.tags.append(tag)
        if tag == "html":
            self.lang = values.get("lang")
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if values.get("data-evidence"):
            self.evidence_levels.append(values["data-evidence"])
        if values.get("data-stakeholder"):
            self.stakeholders.append(values["data-stakeholder"])
        if values.get("data-priority"):
            self.priority_evidence.append(
                (
                    values["data-priority"],
                    values.get("data-evidence"),
                    values.get("data-current-demand"),
                )
            )
        if values.get("data-kpi-field"):
            self.kpi_fields.append(values["data-kpi-field"])


class CommunityNeedsPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / "needs" / "community" / "index.html"
        cls.source = cls.path.read_text(encoding="utf-8") if cls.path.exists() else ""
        cls.parser = CommunityNeedsParser()
        cls.parser.feed(cls.source)

    def test_route_is_japanese_and_connected_to_the_needs_sequence(self):
        self.assertTrue(self.path.exists(), "needs/community/index.html が未作成")
        self.assertEqual(self.parser.lang, "ja")
        self.assertIn('name="viewport"', self.source)
        for link in ("../", "../parents/", "../university/", "../../proposal.html"):
            self.assertIn(link, self.parser.links)

        prior_routes = {
            ROOT / "needs" / "index.html": "./community/",
            ROOT / "needs" / "parents" / "index.html": "../community/",
            ROOT / "needs" / "university" / "index.html": "../community/",
        }
        for path, expected_link in prior_routes.items():
            parser = CommunityNeedsParser()
            parser.feed(path.read_text(encoding="utf-8"))
            self.assertIn(expected_link, parser.links, f"導線不足: {path}")

    def test_decision_flow_has_addressable_sections(self):
        required = {
            "overview",
            "evidence-rules",
            "current-conditions",
            "stakeholders",
            "community-needs",
            "benefit-burden",
            "responsibility",
            "metrics",
            "worksheet",
            "validation",
            "sources",
        }
        self.assertTrue(required.issubset(set(self.parser.ids)), required - set(self.parser.ids))
        self.assertEqual(len(self.parser.ids), len(set(self.parser.ids)), "idが重複している")
        self.assertIn("main", self.parser.tags)
        self.assertIn("nav", self.parser.tags)

    def test_stakeholders_and_evidence_levels_are_structurally_separate(self):
        expected_stakeholders = {
            "adjacent-residents",
            "community-organizations",
            "children-caregivers",
            "older-disabled",
            "local-businesses",
            "city-emergency",
        }
        self.assertTrue(
            expected_stakeholders.issubset(set(self.parser.stakeholders)),
            expected_stakeholders - set(self.parser.stakeholders),
        )
        self.assertTrue(
            {"verified", "inference", "unverified"}.issubset(
                set(self.parser.evidence_levels)
            )
        )

    def test_accountability_and_measurement_are_real_tables(self):
        for section_id in ("responsibility", "metrics"):
            self.assertIn(f'id="{section_id}"', self.source)
            start = self.source.index(f'id="{section_id}"')
            end = self.source.find("</section>", start)
            section = self.source[start:end]
            self.assertIn("<table", section)
            self.assertIn("<thead>", section)
            self.assertIn("<tbody>", section)

    def test_priority_evidence_and_kpi_governance_are_explicit(self):
        expected_priorities = {
            ("P0", "inference", None),
            ("P1", "inference", "unverified"),
            ("P2", "unverified", None),
            ("P3", "unverified", None),
        }
        self.assertTrue(
            expected_priorities.issubset(set(self.parser.priority_evidence)),
            expected_priorities - set(self.parser.priority_evidence),
        )
        self.assertIn('data-kpi-policy="operational"', self.source)
        self.assertEqual(
            {
                "definition",
                "owner",
                "source",
                "baseline-target",
                "cadence",
                "stop-resume",
            },
            set(self.parser.kpi_fields),
        )

    def test_small_label_color_meets_normal_text_contrast(self):
        match = re.search(r"--clay:\s*(#[0-9a-fA-F]{6})", self.source)
        self.assertIsNotNone(match)

        def luminance(hex_color):
            channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        foreground = luminance(match.group(1))
        for background in ("#f3efe5", "#fffdf8"):
            back = luminance(background)
            ratio = (max(foreground, back) + 0.05) / (min(foreground, back) + 0.05)
            self.assertGreaterEqual(ratio, 4.5, f"{match.group(1)} on {background}: {ratio:.2f}:1")

    def test_sources_are_direct_and_local_links_resolve(self):
        external_links = [link for link in self.parser.links if link.startswith("https://")]
        self.assertGreaterEqual(len(external_links), 8)
        self.assertTrue(all("google.com/search" not in link for link in external_links))
        hosts = {urlsplit(link).netloc for link in external_links}
        self.assertIn("www.city.ibaraki.osaka.jp", hosts)
        self.assertIn("www.pref.osaka.lg.jp", hosts)

        for link in self.parser.links:
            parsed = urlsplit(link)
            if parsed.scheme or link.startswith("#"):
                continue
            target = (self.path.parent / parsed.path).resolve()
            self.assertTrue(target.exists(), f"ローカルリンク切れ: {link}")

    def test_page_is_static_and_supports_mobile_and_print_review(self):
        lowered = self.source.lower()
        self.assertNotIn("<script", lowered)
        self.assertNotIn('rel="stylesheet"', lowered)
        self.assertNotIn("<img", lowered)
        self.assertIn("@media (max-width:", self.source)
        self.assertIn("@media print", self.source)
        self.assertIn("overflow-wrap: anywhere", self.source)
        print_css = self.source.partition("@media print")[2]
        self.assertIn("overflow: visible", print_css)
        self.assertIn("min-width: 0", print_css)


if __name__ == "__main__":
    unittest.main()
