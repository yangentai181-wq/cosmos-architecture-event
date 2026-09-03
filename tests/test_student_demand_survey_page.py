from html.parser import HTMLParser
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.lang = None
        self.forms = []
        self.fields = []
        self.buttons = []
        self.ids = set()
        self.gates = []
        self.decision_statuses = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "html":
            self.lang = values.get("lang")
        if values.get("id"):
            self.ids.add(values["id"])
        if values.get("data-gate"):
            self.gates.append(values["data-gate"])
        if values.get("data-decision-status"):
            self.decision_statuses.append(values["data-decision-status"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "form":
            self.forms.append(values)
        if tag in {"input", "select", "textarea"}:
            self.fields.append(values)
        if tag == "button":
            self.buttons.append(values)


class StudentDemandSurveyPageTest(unittest.TestCase):
    def test_survey_route_is_reachable_from_the_proposal(self):
        proposal = (ROOT / "proposal.html").read_text(encoding="utf-8")
        parser = LinkParser()
        parser.feed(proposal)

        self.assertIn("survey/", parser.links)

    def test_survey_is_a_standalone_japanese_page(self):
        path = ROOT / "survey/index.html"
        self.assertTrue(path.exists(), "需要調査票のHTMLが未作成")
        source = path.read_text(encoding="utf-8")
        parser = LinkParser()
        parser.feed(source)

        self.assertEqual(parser.lang, "ja")
        self.assertIn('name="viewport"', source)
        self.assertNotIn('rel="stylesheet"', source.lower())

    def test_one_survey_serves_domestic_and_international_students(self):
        source = (ROOT / "survey/index.html").read_text(encoding="utf-8")
        parser = LinkParser()
        parser.feed(source)

        self.assertEqual(len(parser.forms), 1)
        group_choices = {
            field.get("value")
            for field in parser.fields
            if field.get("name") == "student_group"
        }
        self.assertEqual(group_choices, {"domestic", "international"})

    def test_survey_captures_the_four_inputs_needed_for_a_demand_decision(self):
        source = (ROOT / "survey/index.html").read_text(encoding="utf-8")
        parser = LinkParser()
        parser.feed(source)

        field_names = {field.get("name") for field in parser.fields}
        self.assertTrue(
            {"move_in_intent", "monthly_budget", "stay_length", "unmet_needs"}
            <= field_names
        )
        self.assertEqual(
            {
                field.get("value")
                for field in parser.fields
                if field.get("name") == "stay_length"
            },
            {"one_semester", "one_year", "two_years_or_more", "undecided"},
        )

    def test_survey_cannot_transmit_answers_or_collect_personal_fields(self):
        source = (ROOT / "survey/index.html").read_text(encoding="utf-8")
        parser = LinkParser()
        parser.feed(source)

        self.assertEqual(parser.forms[0].get("onsubmit"), "return false")
        self.assertEqual([button.get("type") for button in parser.buttons], ["button"])
        field_names = {field.get("name") for field in parser.fields}
        self.assertTrue(
            {"name", "email", "phone", "address"}.isdisjoint(field_names)
        )
        self.assertNotIn("fetch(", source)
        self.assertNotIn("XMLHttpRequest", source)

    def test_new_build_decision_requires_three_evidence_gates(self):
        source = (ROOT / "survey/index.html").read_text(encoding="utf-8")
        parser = LinkParser()
        parser.feed(source)

        self.assertIn("decision-gate", parser.ids)
        self.assertEqual(
            set(parser.gates), {"survey", "commitment", "alternatives"}
        )
        self.assertEqual(parser.decision_statuses, ["not-proven"])


if __name__ == "__main__":
    unittest.main()
