# Current Proposal HTML Implementation Plan

> 更新注記（2026-09-04）: この完了済み計画にある `assets/site-detail.png` の再利用手順は、転載許諾を確認できないため撤回した。公開版は自作の `assets/site-specific-b-comparison.svg` を使い、配布画像をコピーしない。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** グループメンバーが学生寮案の論理と根拠を検討できる、自己完結した1ページHTMLを作る。

**Architecture:** 内容は既存の構想文書と資料読込記録から組み立て、単一の意味的HTMLへ埋め込む。自動検査はPython標準ライブラリだけでHTMLの構造、根拠表示、リンク、画像参照を確認する。

**Tech Stack:** HTML5、内部CSS、Python 3 `unittest` / `html.parser`

**Spec:** `docs/superpowers/specs/2026-09-03-current-proposal-html-design.md`

## Global Constraints

- 外部公開やデプロイは行わない。
- JavaScript、外部CSS、Webフォント、追加パッケージを使わない。
- 事実、解釈、仮説・未検証を視覚的にも文章上も区別する。
- 収益は建設費のみと土地取得費込みを併記する。
- 既存の `docs/concept-draft.md` と `docs/source-intake.md` は変更しない。

---

### Task 1: HTMLの受入検査を作る

**Files:**
- Create: `tests/test_proposal_html.py`
- Test: `tests/test_proposal_html.py`

**Interfaces:**
- Consumes: `proposal.html` と `assets/site-detail.png`
- Produces: `python3 -m unittest tests/test_proposal_html.py -v` で実行できる受入検査

- [ ] **Step 1: Write the failing test**

```python
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
        required = {"summary", "facts", "logic", "value", "plan", "site", "finance", "evidence", "decisions"}
        self.assertTrue(required.issubset(self.parser.ids), required - self.parser.ids)

    def test_certainty_and_finance_caveat_are_visible(self):
        for phrase in ("確認済み", "解釈", "仮説・未検証", "13.6年", "22.1年", "土地取得費7億円"):
            self.assertIn(phrase, self.text)

    def test_sources_are_direct_and_site_image_is_local(self):
        external = [link for link in self.parser.links if link.startswith("https://")]
        self.assertGreaterEqual(len(external), 5)
        self.assertTrue(all("google.com/search" not in link for link in external))
        self.assertTrue(any(image.get("src") == "assets/site-detail.png" and image.get("alt") for image in self.parser.images))
        self.assertTrue((ROOT / "assets/site-detail.png").exists())

    def test_page_has_no_script_or_external_stylesheet(self):
        self.assertNotIn("<script", self.source.lower())
        self.assertNotIn('rel="stylesheet"', self.source.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests/test_proposal_html.py -v`

Expected: FAIL because `proposal.html` and `assets/site-detail.png` do not exist.

### Task 2: 根拠チェーン型HTMLを実装する

**Files:**
- Create: `proposal.html`
- Create: `assets/site-detail.png`
- Test: `tests/test_proposal_html.py`

**Interfaces:**
- Consumes: `docs/concept-draft.md`、`docs/source-intake.md`、`tmp/drive-intake/site-detail-1.png`
- Produces: ブラウザで直接開ける `proposal.html`

- [ ] **Step 1: Copy the approved source image**

Run: `mkdir -p assets && cp tmp/drive-intake/site-detail-1.png assets/site-detail.png`

- [ ] **Step 2: Write minimal implementation**

Create semantic sections with IDs `summary`, `facts`, `logic`, `value`, `plan`, `site`, `finance`, `evidence`, and `decisions`. Include a fixed set of certainty badges, the two finance cases, direct source links, accessible image text, responsive CSS, and print CSS.

- [ ] **Step 3: Run test to verify it passes**

Run: `python3 -m unittest tests/test_proposal_html.py -v`

Expected: 5 tests pass with exit code 0.

- [ ] **Step 4: Validate HTML and references**

Run: `tidy -qe proposal.html`

Expected: exit code 0 and no HTML warnings or errors. `xmllint` is not used because its HTML4 parser rejects valid HTML5 semantic elements.

Run: `python3 - <<'PY'
from pathlib import Path
from html.parser import HTMLParser

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"img", "a"}:
            ref = values.get("src") or values.get("href")
            if ref and not ref.startswith(("http://", "https://", "#", "mailto:")):
                self.refs.append(ref)

root = Path(".")
parser = Parser()
parser.feed((root / "proposal.html").read_text(encoding="utf-8"))
missing = [ref for ref in parser.refs if not (root / ref).exists()]
assert not missing, missing
print(f"local references ok: {len(parser.refs)}")
PY`

Expected: exit code 0 and zero missing local references.

### Task 3: 内容と変更範囲を最終照合する

**Files:**
- Modify: `proposal.html` only if the evidence review identifies an overstatement
- Test: `tests/test_proposal_html.py`

**Interfaces:**
- Consumes: 承認済みデザイン仕様と根拠レビュー
- Produces: 完了条件を満たす最終HTML

- [ ] **Step 1: Re-read the spec and evidence review**

Check every completion condition and replace unsupported wording with qualified wording such as `示唆する`, `可能性がある`, or `今後検証する`.

- [ ] **Step 2: Run the complete verification suite**

Run: `python3 -m unittest tests/test_proposal_html.py -v && tidy -qe proposal.html && git diff --check`

Expected: all tests pass, HTML parser reports no errors, diff check is clean, and the combined command exits 0.
