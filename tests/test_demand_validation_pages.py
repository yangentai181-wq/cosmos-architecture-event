from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.forms = []
        self.inputs = []
        self.buttons = []
        self.scripts = []
        self.text = []
        self.lang = None
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
        if tag == "form":
            self.forms.append(values)
        if tag in {"input", "select", "textarea"}:
            self.inputs.append(values)
        if tag == "button":
            self.buttons.append(values)
        if tag == "script":
            self.scripts.append(values)

    def handle_data(self, data):
        if not self._ignored_depth:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag in {"style", "script"} and self._ignored_depth:
            self._ignored_depth -= 1


def parse_page(relative_path):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    parser = PageParser()
    parser.feed(source)
    return source, parser, " ".join(parser.text)


class DemandValidationPagesTest(unittest.TestCase):
    def test_internal_model_exposes_demand_finance_and_design_decisions(self):
        source, parser, text = parse_page("validation/index.html")

        self.assertEqual(parser.lang, "ja")
        self.assertIn('name="viewport"', source)
        self.assertIn("./app.mjs", [script.get("src") for script in parser.scripts])
        self.assertIn("../interest/", parser.links)
        for section in (
            "decision",
            "resident-model",
            "commuter-model",
            "finance-model",
            "sensitivity",
            "architecture",
            "limits",
        ):
            self.assertIn(section, parser.ids)
        for phrase in (
            "5階・168室（収支上限）",
            "寄宿舎91室",
            "7個室Unit・84室",
            "共同住宅99戸",
            "土地代を含む",
            "目標利回り7%",
            "満室は理論上限",
            "国内学生84人",
            "設計検討幅84〜99室",
        ):
            self.assertIn(phrase, text)

    def test_interest_page_has_three_local_only_surveys_and_no_personal_fields(self):
        source, parser, text = parse_page("interest/index.html")

        self.assertEqual(parser.lang, "ja")
        self.assertEqual(len(parser.forms), 3)
        self.assertTrue(all("data-local-only" in form for form in parser.forms))
        self.assertTrue(all(not form.get("action") for form in parser.forms))
        self.assertEqual(len(parser.buttons), 3)
        self.assertTrue(all(button.get("type") == "button" for button in parser.buttons))
        self.assertIn("../validation/", parser.links)
        for section in ("commuter", "resident", "parent", "measurement", "privacy"):
            self.assertIn(section, parser.ids)
        for phrase in (
            "通い型",
            "下宿型",
            "保護者",
            "月額総費用",
            "11万円まで（年132万円）",
            "17万円まで（年204万円）",
            "19万円超も検討（年228万円超）",
            "初年度一時費用の上限は？",
            "入館金・保証・保険・契約事務・引越し等",
            "返金可能な予約金",
            "このローカル版は回答を送信・保存しません",
        ):
            self.assertIn(phrase, text)

        forbidden_names = {"name", "email", "phone", "address"}
        actual_names = {field.get("name") for field in parser.inputs}
        self.assertTrue(forbidden_names.isdisjoint(actual_names))
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_pages_are_self_contained_and_mobile_ready(self):
        for relative_path in ("validation/index.html", "interest/index.html"):
            source, _, _ = parse_page(relative_path)
            self.assertIn("@media (max-width:", source)
            self.assertIn("@media print", source)
            self.assertNotIn('rel="stylesheet"', source.lower())
            self.assertNotIn("http://", source)


if __name__ == "__main__":
    unittest.main()
