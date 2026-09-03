from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRECTORIES = {".git", ".pytest_cache", "__pycache__", "tmp"}
TEXT_SUFFIXES = {".css", ".html", ".js", ".md", ".mjs", ".py", ".svg", ".txt"}
EMAIL_ADDRESS = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)
PUBLIC_CONTACT_MAILBOXES = {
    "oic-dorm@st.ritsumei.ac.jp",
    "saito-pluscafe@forc-c.co.jp",
    "shinsashido@city.ibaraki.lg.jp",
}
HIGH_CONFIDENCE_SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})"),
    "aws-access-key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "google-api-key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "openai-api-key": re.compile(r"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}"),
    "anthropic-api-key": re.compile(r"sk-ant-[A-Za-z0-9_-]{32,}"),
    "slack-token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
}
PRIVATE_WORKSPACE_URL = re.compile(
    r"https://(?:docs\.google\.com|drive\.google\.com|app\.notion\.com)(?:/|\b)",
    re.IGNORECASE,
)


def publication_candidate_paths():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(ROOT).parts):
            continue
        yield path


class PublicationBoundaryTest(unittest.TestCase):
    def test_publication_candidates_only_embed_approved_public_mailboxes(self):
        exposures = []
        for path in publication_candidate_paths():
            source = path.read_text(encoding="utf-8")
            unexpected = {
                match.group(0).lower()
                for match in EMAIL_ADDRESS.finditer(source)
                if match.group(0).lower() not in PUBLIC_CONTACT_MAILBOXES
            }
            if unexpected:
                exposures.append(str(path.relative_to(ROOT)))

        self.assertEqual(
            exposures,
            [],
            "公開候補ファイルには承認済みの公開窓口以外のメールアドレスを保存しない",
        )

    def test_publication_candidates_do_not_embed_high_confidence_secrets(self):
        exposures = []
        for path in publication_candidate_paths():
            source = path.read_text(encoding="utf-8")
            for label, pattern in HIGH_CONFIDENCE_SECRET_PATTERNS.items():
                if pattern.search(source):
                    exposures.append(f"{path.relative_to(ROOT)} ({label})")

        self.assertEqual(
            exposures,
            [],
            "公開候補ファイルには秘密情報らしい値を保存しない",
        )

    def test_publication_candidates_do_not_link_private_workspaces(self):
        exposures = []
        for path in publication_candidate_paths():
            source = path.read_text(encoding="utf-8")
            if PRIVATE_WORKSPACE_URL.search(source):
                exposures.append(str(path.relative_to(ROOT)))

        self.assertEqual(
            exposures,
            [],
            "公開候補ファイルからGoogle共有資料・Notionへの直リンクを外す",
        )


if __name__ == "__main__":
    unittest.main()
