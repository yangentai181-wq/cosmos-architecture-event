from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SlideAssetsTest(unittest.TestCase):
    def test_student_needs_visual_has_five_decision_points(self):
        visual = (ROOT / "assets/student-needs-five-points.svg").read_text(
            encoding="utf-8"
        )
        for phrase in (
            "家賃ではなく年間総負担",
            "生活圏全体へ移動",
            "静かに暮らす",
            "入居初日の負担を減らす",
            "生活の選択肢",
            "確認済み",
            "要検証",
        ):
            self.assertIn(phrase, visual)

    def test_svg_sources_do_not_contain_patch_artifacts(self):
        for path in (ROOT / "assets").glob("*.svg"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(r"\n+", source, path.name)


if __name__ == "__main__":
    unittest.main()
