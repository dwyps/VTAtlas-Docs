"""The authoring gate: keep docs/ renderable in BOTH Obsidian and Docusaurus, with no per-file switching.

Why this exists rather than trusting discipline. The two worst failures here are SILENT:

1. ANGLE BRACKETS. In CommonMark mode `TArray<FGameplayTag>` builds green and DELETES the type name.
   "returns TArray<FGameplayTag> instead" renders as "returns TArray instead". Obsidian does the same
   thing by the same mechanism. Nothing errors, nothing warns, and the rendered page is quietly wrong.
   For a C++ API reference that is the highest-value check in this file.

2. %%COMMENTS%%. Invisible in Obsidian's editing view, rendered in full on the site. A stray
   "%% Fran: this number is a guess %%" publishes verbatim to docs.vestro.hr.

THE SCANNER MUST UNDERSTAND CODE, or it is worse than nothing. A naive grep for `<[A-Z]\\w*>` flags
`Implements<UVTATLRegionOccupant>()` and `VTATLDumpFootprint <Tag>` in this very corpus, both of which
are correctly inside backticks. That was measured, not imagined: it happened while writing this. A gate
that cries wolf on correct prose gets switched off, so fenced blocks and inline code spans are stripped
before any pattern runs.

Run: python tools/check_markdown.py [--fix-nothing]
Exit 0 clean, 1 with findings.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"

# Constructs that are legal Obsidian and either break or silently misrender in Docusaurus, plus the
# reverse: Docusaurus dialect that shows as literal junk in the vault.
BANNED = [
    (re.compile(r"!?\[\[[^\]]+\]\]"),
     ("Obsidian wikilink or embed. Use a relative [text](./file.md) link; "
      "turn OFF 'Use [[Wikilinks]]' in Obsidian settings.")),
    (re.compile(r"%%"), "Obsidian comment. INVISIBLE in Obsidian's editor and PUBLISHED in full on the site."),
    (re.compile(r"==[^=\n]+=="), "Obsidian highlight. Renders as literal '==' on the site."),
    (re.compile(r"(?m)^:::"),
     ("Docusaurus directive. Renders as literal ':::' lines in Obsidian. "
      "Use an uppercase GitHub alert instead: > [!NOTE]")),
    (re.compile(r"(?m)^!!!\s"), "MkDocs admonition. Renders as literal text in both tools."),
    (re.compile(r"(?m)^import\s+\S+\s+from\s"), "MDX import. Not valid in CommonMark mode and meaningless in Obsidian."),
    (re.compile(r"(?m)^\s*\^[a-zA-Z0-9-]+\s*$"), "Obsidian block id. Meaningless outside Obsidian."),
]

# Checked against the RAW text, since strip_code blanks fenced blocks and this rule is about the
# fence itself. Measured 2026-08-27: a ```mermaid fence renders correctly in Obsidian and is
# replaced by an empty HTML comment on the site, because Docusaurus turns it into a React
# component and CommonMark mode has no JSX to render one. The author sees a diagram, the buyer
# sees nothing, and the build stays green. Commit an SVG instead: it renders in both.
MERMAID_FENCE = re.compile(r"(?m)^ {0,3}```+\s*mermaid\b")

# The C++ hazard. Only uppercase-initial identifiers, so <br> and <https://...> are handled separately.
ANGLE_TYPE = re.compile(r"<([A-Z][A-Za-z0-9_]*)\s*>")

# GitHub alerts are the ONE callout form that renders natively in Obsidian, on GitHub, and degrades to
# a plain blockquote anywhere else. Obsidian lowercases the captured type, so uppercase works in both;
# the lowercase spelling does NOT render as an alert on GitHub.
ALERT = re.compile(r"(?m)^>\s*\[!([a-zA-Z]+)\]")
ALERT_OK = {"NOTE", "TIP", "IMPORTANT", "WARNING", "CAUTION"}

FENCE = re.compile(r"(?ms)^```.*?^```")
INLINE = re.compile(r"`[^`\n]*`")


def strip_code(text: str) -> str:
    """Blank out fenced blocks and inline spans, preserving line numbers so offsets stay usable."""
    def blank(m: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    return INLINE.sub(blank, FENCE.sub(blank, text))


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def check_frontmatter(path: Path, text: str, findings: list[str]) -> None:
    rel = path.relative_to(DOCS.parent)
    if not text.startswith("---"):
        findings.append(f"{rel}:1: no frontmatter. Every page needs a description; it feeds "
                        f"<meta description> and the og card.")
        return

    end = text.find("\n---", 3)
    if end == -1:
        findings.append(f"{rel}:1: frontmatter is not closed.")
        return

    block = text[3:end]
    desc = None
    for raw in block.splitlines():
        line = raw.strip()
        if line.startswith("description:"):
            desc = line[len("description:"):].strip()
    if desc is None:
        findings.append(f"{rel}:1: frontmatter has no 'description'.")
        return
    if not desc:
        findings.append(f"{rel}:1: 'description' is empty.")
        return
    # The exact failure that broke the first build: prose contains colons, and an unquoted value with
    # ': ' in it parses as a nested mapping. The build error names a column, not the cause.
    if not desc.startswith(('"', "'")) and ": " in desc:
        findings.append(f"{rel}:1: unquoted 'description' contains ': ', which YAML reads as a mapping "
                        f"entry and fails the build. Wrap it in double quotes.")


def check_links(path: Path, text: str, findings: list[str]) -> None:
    """Every relative .md link must resolve on disk, because that is the one mechanism holding the
    vault and the site together. Docusaurus throws on these too; catching it here is faster and it
    also catches links Obsidian would follow but Docusaurus never sees."""
    rel = path.relative_to(DOCS.parent)
    for m in re.finditer(r"\]\((\.{1,2}/[^)\s#]+\.md)(#[^)\s]*)?\)", text):
        target = (path.parent / m.group(1)).resolve()
        if not target.is_file():
            findings.append(f"{rel}:{line_of(text, m.start())}: link target does not exist: {m.group(1)}")


def check_file(path: Path) -> list[str]:
    findings: list[str] = []
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(DOCS.parent)

    check_frontmatter(path, text, findings)
    check_links(path, text, findings)

    prose = strip_code(text)

    for m in MERMAID_FENCE.finditer(text):
        findings.append(
            f"{rel}:{line_of(text, m.start())}: mermaid fence. It renders in Obsidian and is "
            f"replaced by an empty comment on the site, because CommonMark mode cannot render the "
            f"React component Docusaurus converts it into. Commit an SVG under media/ instead.")

    for pattern, why in BANNED:
        for m in pattern.finditer(prose):
            findings.append(f"{rel}:{line_of(text, m.start())}: {why}")

    for m in ANGLE_TYPE.finditer(prose):
        findings.append(
            f"{rel}:{line_of(text, m.start())}: <{m.group(1)}> outside code. CommonMark treats it as an "
            f"HTML tag and SILENTLY DELETES it, in Obsidian too. Wrap the whole expression in backticks "
            f"(not a backslash, which prints literally in some renderers).")

    for m in ALERT.finditer(prose):
        if m.group(1) not in ALERT_OK:
            findings.append(
                f"{rel}:{line_of(text, m.start())}: callout [!{m.group(1)}] is not one of "
                f"{'/'.join(sorted(ALERT_OK))} in uppercase. Only those five render natively in both "
                f"Obsidian and GitHub.")

    return findings


def main() -> int:
    if not DOCS.is_dir():
        print(f"check_markdown: {DOCS} not found")
        return 1

    mdx = sorted(DOCS.rglob("*.mdx")) + sorted((DOCS.parent / "src").rglob("*.mdx"))
    findings = [f"{p}: .mdx file present. This project is CommonMark-only; MDX breaks the vault."
                for p in mdx]

    pages = sorted(DOCS.rglob("*.md"))
    for page in pages:
        findings.extend(check_file(page))

    for f in findings:
        print(f"  {f}")

    print(f"check_markdown: {len(pages)} page(s), {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
