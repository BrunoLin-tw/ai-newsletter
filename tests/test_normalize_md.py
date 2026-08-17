import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "normalize-md.sh"


class NormalizeMarkdownTest(unittest.TestCase):
    def test_normalizes_titles_without_changing_bodies(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            cases = {
                "output/2026/08/06.md": (
                    "AI Daily Newsletter — old date 8:55\nBody one\n",
                    "# 📰 AI Daily Newsletter — 2026年08月06日 08:55\nBody one\n",
                ),
                "output/2026/08/07.md": (
                    "Wrong title 6:04\nBody two\n",
                    "# 📰 AI Daily Newsletter — 2026年08月07日 06:04\nBody two\n",
                ),
                "output/2026/08/08.md": (
                    "Wrong title\nBody three\n",
                    "# 📰 AI Daily Newsletter — 2026年08月08日 09:00\nBody three\n",
                ),
                "output/2026/02/17.md": (
                    "---\n📰 AI Daily Newsletter — old date 9:05\n---\n\nBody four\n",
                    "# 📰 AI Daily Newsletter — 2026年02月17日 09:05\n\nBody four\n",
                ),
            }
            for relative, (before, _) in cases.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(before, encoding="utf-8")

            invalid = root / "output/2026/8/09.md"
            invalid.parent.mkdir(parents=True)
            invalid.write_text("Invalid path\n", encoding="utf-8")
            empty = root / "output/2026/08/10.md"
            empty.touch()

            result = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            )

            for relative, (_, expected) in cases.items():
                self.assertEqual((root / relative).read_text(encoding="utf-8"), expected)
            self.assertEqual(invalid.read_text(encoding="utf-8"), "Invalid path\n")
            self.assertEqual(empty.read_text(encoding="utf-8"), "")
            self.assertIn("Invalid path", result.stdout)
            self.assertIn("Skipping empty", result.stdout)
            self.assertEqual(list(root.rglob("*.bak")), [])


if __name__ == "__main__":
    unittest.main()
