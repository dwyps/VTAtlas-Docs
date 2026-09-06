"""The mark gate: hold the identity marks in this repo to the rules they were drawn under.

The two logo files under static/img/ are copies of SVG masters kept in the VTSuite repo, where a
lane rasterises each master and demands the plugin icon match it pixel for pixel. Nothing on this
side compared the copies with anything, and the failures that matter here are SILENT in the same
way the Markdown ones are:

1. A <style> block, a transform, an opacity or a stroke changes what the file draws while the file
   keeps loading. The navbar places these as images, so a mark drifting off its master is not a
   build error. It is a different logo on the live site behind a green build.

2. Metadata rides along invisibly. The delivered identity files arrived with a signed C2PA manifest
   embedded, the bulk of each file's bytes, and only the stripped copies ship. A re-export from a
   design tool puts the manifest straight back and nothing about the rendered page changes.

3. The integer and fill-only rules are what let the VTSuite lane rasterise a master by filling
   whole pixels with no SVG renderer. A copy that breaks them has stopped being the master, and
   the icon it is supposed to match can no longer be checked against it.

4. A shape can be in the file and absent from the drawing. A <rect> nested inside another <rect>,
   an element left in the null or a foreign namespace, a rect of zero width, a rect parked off the
   canvas: each of those parses, each satisfies a clause-by-clause reading of the rules below, and
   a browser draws none of them. A gate that counts elements instead of counting what is drawn
   calls such a file clean, which is the failure it exists to catch. The first two are reported by
   name, because a mark has no reason to carry either. The last two are not findings on their own:
   a zero-size or an off-canvas rect is legal SVG that paints nothing, so it is denied only the
   credit of answering for the file, and a mark whose shapes all paint nothing is reported as
   drawing nothing.

The rule set is VT_SUITE_ICON_RULES section 6 and the install brief, restated as checks: the root
is <svg> with viewBox="0 0 128 128" and no width or height; the only shapes are <rect> and
<polygon>, each a leaf element in the SVG namespace, so no <metadata>, <style>, <defs>, <text>,
gradient or group and nothing nested inside a shape; every shape has fill="#RRGGBB" in uppercase
and nothing else colours it (no stroke, style, opacity, class or transform attribute on a shape or
on the root); at most two distinct fills per file; every coordinate and every polygon point is an
integer; rx and ry, where present, are 0; and the string "c2pa" is absent in any case. A <!DOCTYPE
or <!ENTITY is refused by regex before the XML parser sees the text, which is what keeps the stdlib
parser away from entity expansion.

The files are an explicit list, never a glob. docs/media/*.svg are diagrams with titles, text and
strokes that fail every rule here by design, and they are not marks. Pass other paths as arguments
to hold them to the same rules; the plated favicon on vestro.hr is one such file and passes.

Run: python tools/check_marks.py [FILE ...]
     python tools/check_marks.py --self-test
Exit 0 clean. Exit 1 with findings, when a listed file is missing, or when a self-test mutation
survives.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MARKS = (ROOT / "static" / "img" / "logo.svg", ROOT / "static" / "img" / "logo-light.svg")

CANVAS = 128
VIEWBOX = f"0 0 {CANVAS} {CANVAS}"
SVG_NS = "{http://www.w3.org/2000/svg}"
MAX_FILLS = 2

HEX_FILL = re.compile(r"^#[0-9A-F]{6}$")
INTEGER = re.compile(r"^-?\d+$")
# Matched on the raw text, before parsing. A master has no DOCTYPE and no entity, and refusing them
# by regex means the parser never sees one, so entity expansion is not a question this file has to
# answer with a dependency.
DOCTYPE = re.compile(r"<!\s*(DOCTYPE|ENTITY)", re.IGNORECASE)
# Also on the raw text: a manifest can sit in a comment, which the parser drops.
C2PA = re.compile(r"c2pa", re.IGNORECASE)
# And on the raw text for the same reason. ElementTree discards processing instructions, so no
# parsed clause below can see one, and an <?xml-stylesheet?> repaints the whole drawing when the
# file is opened on its own. That is the "nothing else colours it" rule, and it would otherwise
# pass in silence. The XML prolog is the one processing instruction a master carries.
PROCESSING_INSTRUCTION = re.compile(r"<\?(?!xml[\s?])", re.IGNORECASE)

# The whitelists are the whole of "nothing else colours it". Stroke, style, opacity, class and
# transform are each an attribute that makes the drawing differ from a flat fill of the shapes, and
# listing what IS allowed reports every one of them by name. A dedicated transform clause was tried
# beside a whitelist like this in the VTSuite lane and could never change the verdict, so there is
# none here. The root carries xmlns and viewBox only; ElementTree consumes xmlns as a namespace
# declaration, so viewBox is the one attribute it reports, and width or height on the root land
# here too, which is the "sized by the viewBox alone" rule.
ROOT_ATTRIBUTES = {"viewBox"}
RECT_ATTRIBUTES = {"x", "y", "width", "height", "rx", "ry", "fill"}
POLYGON_ATTRIBUTES = {"points", "fill"}
COORDINATES = ("x", "y", "width", "height", "rx", "ry")
SHAPES = {"rect": RECT_ATTRIBUTES, "polygon": POLYGON_ATTRIBUTES}


def _covers_canvas(x0: int, y0: int, x1: int, y1: int) -> bool:
    """Does the box x0..x1 by y0..y1 cover at least one whole pixel of the canvas?

    A shape covering none of it is not a finding, only uncounted. Zero-size and off-canvas shapes
    are legal SVG that happens to paint nothing, the rule sheet forbids neither, and the drawing on
    the page is unchanged by one. What the gate refuses is a file where NOTHING is drawn, so the
    only thing coverage decides is whether a shape may answer for the file as a whole. A shape that
    hangs over an edge covers pixels and counts, once, like any other."""
    return x1 - x0 >= 1 and y1 - y0 >= 1 and x1 > 0 and y1 > 0 and x0 < CANVAS and y0 < CANVAS


def _check_rect(element: ElementTree.Element, findings: list[str]) -> bool:
    """Findings for one <rect>, and whether it draws on the canvas."""
    values: dict[str, int] = {}
    for name in COORDINATES:
        raw = element.get(name, "0")
        if not INTEGER.match(raw):
            findings.append(f"<rect> {name}={raw!r} is not an integer")
            continue
        values[name] = int(raw)
        if name in ("rx", "ry") and values[name]:
            findings.append(f"<rect> has a corner radius {name}={raw}; radius is 0 everywhere")

    if len(values) < len(COORDINATES):
        return False
    return _covers_canvas(values["x"], values["y"],
                          values["x"] + values["width"], values["y"] + values["height"])


def _check_polygon(element: ElementTree.Element, findings: list[str]) -> bool:
    """Findings for one <polygon>, and whether it draws on the canvas."""
    raw = element.get("points", "")
    values = [v for v in re.split(r"[\s,]+", raw.strip()) if v]
    integral = True
    for value in values:
        if not INTEGER.match(value):
            findings.append(f"<polygon> point {value!r} is not an integer")
            integral = False
            break
    if len(values) < 6 or len(values) % 2:
        findings.append(f"<polygon> points={raw!r} is not a list of at least three integer x,y pairs")
        return False
    if not integral:
        return False

    # The bounding box over-estimates: a polygon inside it can still paint nothing, three collinear
    # points being the plain case. That is the right direction for a guard against a file that draws
    # nothing at all, and it never counts a polygon lying wholly off the canvas.
    xs = [int(v) for v in values[0::2]]
    ys = [int(v) for v in values[1::2]]
    return _covers_canvas(min(xs), min(ys), max(xs), max(ys))


def check_text(text: str) -> list[str]:
    """Every way the text departs from the rule set, as clause findings without a path."""
    findings: list[str] = []
    if C2PA.search(text):
        findings.append("carries a C2PA manifest or a mention of one; only the stripped copy ships")
    if PROCESSING_INSTRUCTION.search(text):
        findings.append("carries a processing instruction; the parser drops one and an "
                        "<?xml-stylesheet?> repaints the drawing, so only the XML prolog is allowed")
    if DOCTYPE.search(text):
        return findings + ["carries a DOCTYPE or entity declaration; a mark has neither"]
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        return findings + [f"does not parse as XML ({error})"]

    if root.tag != f"{SVG_NS}svg":
        return findings + [f"root is {root.tag!r}, not an <svg> in the SVG namespace "
                           f"(xmlns=\"http://www.w3.org/2000/svg\")"]
    if root.get("viewBox") != VIEWBOX:
        findings.append(f"viewBox is {root.get('viewBox')!r}, must be {VIEWBOX!r}")
    unknown = sorted(set(root.attrib) - ROOT_ATTRIBUTES)
    if unknown:
        findings.append(f"root carries {', '.join(unknown)}; the root has xmlns and viewBox only "
                        f"and is sized by the viewBox alone")

    # The root's own children, never root.iter(). A browser draws the children of a container
    # element, this rule set allows no container, and so a shape nested inside another shape is
    # simply not drawn: <rect><rect/></rect> paints one rectangle. Walking every descendant counted
    # the nested one and read the file as clean while the live navbar had lost that shape. Nothing
    # is skipped silently, because a shape holding children is reported below.
    drawn = 0
    fills: set[str] = set()
    for element in root:
        if not element.tag.startswith(SVG_NS):
            findings.append(f"<{element.tag}> is not in the SVG namespace "
                            f"(xmlns=\"http://www.w3.org/2000/svg\"); an element outside it is not "
                            f"an SVG shape and does not draw")
            continue
        local = element.tag.removeprefix(SVG_NS)
        if local not in SHAPES:
            findings.append(f"<{local}> is not allowed; a mark is <rect> and <polygon> only")
            continue
        if len(element):
            findings.append(f"<{local}> has children; a shape is a leaf, and a shape nested inside "
                            f"another shape is never drawn")
        unknown = sorted(set(element.attrib) - SHAPES[local])
        if unknown:
            findings.append(f"<{local}> carries {', '.join(unknown)}; its attributes are "
                            f"{', '.join(sorted(SHAPES[local]))} only, and nothing but fill "
                            f"colours a mark")
        fill = element.get("fill")
        if fill is None or not HEX_FILL.match(fill):
            findings.append(f"<{local}> fill {fill!r} is not a six-digit uppercase hex colour "
                            f"(#RRGGBB)")
        else:
            fills.add(fill)
        if local == "rect":
            drawn += _check_rect(element, findings)
        else:
            drawn += _check_polygon(element, findings)

    if len(fills) > MAX_FILLS:
        findings.append(f"{len(fills)} distinct fills, at most {MAX_FILLS} allowed: "
                        f"{', '.join(sorted(fills))}")
    # Not a rule from the sheet: a file with no shapes satisfies every clause above and draws
    # nothing, and a gate that passes an empty mark reads identically to one that checked. Counting
    # elements was not enough, since a rect of zero width and a rect off at x=900 are both
    # well-formed and both paint no pixel, so the count is of shapes that cover the canvas.
    if not drawn:
        findings.append(f"no shape covers a pixel of the {CANVAS}x{CANVAS} canvas; "
                        f"the file draws nothing")
    return findings


def label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def check_file(path: Path) -> list[str]:
    """Findings for one file, each shaped '<path>: <clause>'. A missing file is a finding, never a
    skip: a gate that passes when its input is absent reads identically to one that checked."""
    where = label(path)
    if not path.is_file():
        return [f"{where}: missing or not a file; the mark gate has nothing to hold"]
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        return [f"{where}: is not UTF-8 text ({error.reason} at byte {error.start})"]
    return [f"{where}: {finding}" for finding in check_text(text)]


# The shipped VT Atlas master, verbatim: the same text as static/img/logo.svg. Each mutation below
# breaks one clause and names the word the finding must carry, so the mutation record runs instead
# of being a sentence in a commit message.
MASTER = (
    '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
    '<rect x="16" y="16" width="16" height="32" fill="#F4F6F7"></rect>'
    '<rect x="16" y="16" width="32" height="16" fill="#F4F6F7"></rect>'
    '<rect x="80" y="16" width="32" height="16" fill="#F4F6F7"></rect>'
    '<rect x="96" y="16" width="16" height="32" fill="#F4F6F7"></rect>'
    '<rect x="96" y="80" width="16" height="32" fill="#F4F6F7"></rect>'
    '<rect x="80" y="96" width="32" height="16" fill="#F4F6F7"></rect>'
    '<rect x="16" y="96" width="32" height="16" fill="#F4F6F7"></rect>'
    '<rect x="16" y="80" width="16" height="32" fill="#F4F6F7"></rect>'
    '<rect x="56" y="56" width="16" height="16" fill="#607D29"></rect></svg>'
)
ZONE = '<rect x="56" y="56" width="16" height="16" fill="#607D29"></rect>'
POLYGON = '<polygon points="12,48 36,48 76,88 76,112" fill="#F4F6F7"></polygon>'
# The zone rect is the last shape in the master, so this is the frame rect that precedes it.
LAST_FRAME = 'fill="#F4F6F7"></rect>' + ZONE
OFF_CANVAS = '<rect x="900" y="56" width="16" height="16" fill="#607D29"></rect>'


def _only(text: str, shape: str) -> str:
    """The master with every rect dropped and one shape put back, so that shape is the whole
    drawing. A coverage mutation has to be shaped this way: a single dead rect beside eight live
    ones changes nothing about whether the FILE draws, which is what the guard asks."""
    return re.sub(r"<rect .*?</rect>", "", text).replace("</svg>", shape + "</svg>")


# Positive controls. The clean master must pass, and so must the master with a legal polygon, or
# every mutation below would "die" against a gate that rejects everything. The third control pins
# the decision in _covers_canvas: a shape that paints nothing is uncounted, not a finding.
CONTROLS: list[tuple[str, str]] = [
    ("the master itself", MASTER),
    ("the master plus a legal polygon", MASTER.replace("</svg>", POLYGON + "</svg>")),
    ("the master plus a rect off the canvas", MASTER.replace("</svg>", OFF_CANVAS + "</svg>")),
]

Edit = Callable[[str], str]
MUTATIONS: list[tuple[str, Edit, str]] = [
    ("viewBox is 64", lambda s: s.replace('viewBox="0 0 128 128"', 'viewBox="0 0 64 64"'), "viewBox"),
    ("width on the root", lambda s: s.replace("viewBox=", 'width="128" viewBox='), "width"),
    ("height on the root", lambda s: s.replace("viewBox=", 'height="128" viewBox='), "height"),
    ("transform on the root", lambda s: s.replace("viewBox=", 'transform="scale(1)" viewBox='), "transform"),
    ("no SVG namespace", lambda s: s.replace(' xmlns="http://www.w3.org/2000/svg"', ""), "namespace"),
    ("a metadata element", lambda s: s.replace(ZONE, "<metadata>x</metadata>" + ZONE), "metadata"),
    ("a stylesheet processing instruction",
     lambda s: s.replace("<svg", '<?xml-stylesheet type="text/css" href="repaint.css"?><svg'),
     "processing instruction"),
    ("a style element", lambda s: s.replace(ZONE, "<style>rect{fill:red}</style>" + ZONE), "style"),
    ("a defs element", lambda s: s.replace(ZONE, "<defs></defs>" + ZONE), "defs"),
    ("a text element", lambda s: s.replace(ZONE, '<text x="0" y="0">VT</text>' + ZONE), "text"),
    ("a gradient", lambda s: s.replace(ZONE, '<linearGradient id="g"></linearGradient>' + ZONE), "Gradient"),
    ("a group", lambda s: s.replace(ZONE, "<g>" + ZONE + "</g>"), "<g>"),
    ("a rect nested in a rect", lambda s: s.replace(LAST_FRAME, 'fill="#F4F6F7">' + ZONE + "</rect>"), "children"),
    ("a rect in the null namespace", lambda s: s.replace(ZONE, ZONE.replace("<rect ", '<rect xmlns="" ')), "namespace"),
    ("a rect in a foreign namespace", lambda s: s.replace(ZONE, ZONE.replace("<rect ", '<rect xmlns="http://example.invalid/x" ')), "namespace"),
    ("a circle", lambda s: s.replace(ZONE, '<circle cx="64" cy="64" r="8" fill="#607D29"/>' + ZONE), "circle"),
    ("a path", lambda s: s.replace(ZONE, '<path d="M0 0h8v8z" fill="#607D29"/>' + ZONE), "path"),
    ("stroke on a rect", lambda s: s.replace('fill="#607D29"', 'fill="#607D29" stroke="#000000"'), "stroke"),
    ("opacity on a rect", lambda s: s.replace('fill="#607D29"', 'fill="#607D29" opacity="0.5"'), "opacity"),
    ("fill-opacity on a rect", lambda s: s.replace('fill="#607D29"', 'fill="#607D29" fill-opacity="0.5"'), "opacity"),
    ("transform on a rect", lambda s: s.replace('<rect x="56"', '<rect transform="translate(1 0)" x="56"'), "transform"),
    ("style attribute on a rect", lambda s: s.replace('fill="#607D29"', 'fill="#607D29" style="fill:red"'), "style"),
    ("class on a rect", lambda s: s.replace('<rect x="56"', '<rect class="zone" x="56"'), "class"),
    ("lowercase hex fill", lambda s: s.replace('fill="#607D29"', 'fill="#607d29"'), "hex"),
    ("three-digit hex fill", lambda s: s.replace('fill="#607D29"', 'fill="#672"'), "hex"),
    ("named colour fill", lambda s: s.replace('fill="#607D29"', 'fill="olive"'), "hex"),
    ("rgb() fill", lambda s: s.replace('fill="#607D29"', 'fill="rgb(96,125,41)"'), "hex"),
    ("no fill at all", lambda s: s.replace(' fill="#607D29"', ""), "fill"),
    ("a third fill", lambda s: s.replace(ZONE, ZONE + '<rect x="0" y="0" width="8" height="8" fill="#B6FF00"></rect>'), "3 distinct fills"),
    ("a fractional x", lambda s: s.replace('x="56"', 'x="56.5"'), "integer"),
    ("a width with units", lambda s: s.replace('width="16" height="16"', 'width="16px" height="16"'), "integer"),
    ("rx on a rect", lambda s: s.replace('<rect x="56"', '<rect rx="8" x="56"'), "radius"),
    ("ry on a rect", lambda s: s.replace('<rect x="56"', '<rect ry="8" x="56"'), "radius"),
    ("a fractional polygon point", lambda s: s.replace("</svg>", POLYGON.replace("36,48", "36.5,48") + "</svg>"), "integer"),
    ("an odd polygon point list", lambda s: s.replace("</svg>", POLYGON.replace("36,48 ", "36 ") + "</svg>"), "pairs"),
    ("a polygon in a third fill", lambda s: s.replace("</svg>", POLYGON.replace("#F4F6F7", "#B6FF00") + "</svg>"), "3 distinct fills"),
    ("a DOCTYPE", lambda s: s.replace("<svg", "<!DOCTYPE svg><svg"), "DOCTYPE"),
    ("an entity declaration", lambda s: s.replace("<svg", '<!DOCTYPE svg [<!ENTITY x "y">]><svg'), "DOCTYPE"),
    ("c2pa in a comment", lambda s: s.replace("</svg>", "<!-- c2pa:manifest --></svg>"), "C2PA"),
    ("C2PA in any case", lambda s: s.replace("</svg>", "<!-- C2PA --></svg>"), "C2PA"),
    ("truncated file", lambda s: s[:-6], "parse"),
    ("no shapes", lambda s: re.sub(r"<rect .*?</rect>", "", s), "draws nothing"),
    ("only a zero-width rect", lambda s: _only(s, ZONE.replace('width="16"', 'width="0"')), "draws nothing"),
    ("only a rect off the canvas", lambda s: _only(s, OFF_CANVAS), "draws nothing"),
    ("only a rect in negative space", lambda s: _only(s, ZONE.replace('x="56" y="56"', 'x="-16" y="-16"')), "draws nothing"),
]


def self_test() -> int:
    failures = 0
    for name, text in CONTROLS:
        findings = check_text(text)
        print(f"  {'clean' if not findings else 'RED  '}  {name}")
        for finding in findings:
            print(f"           {finding}")
        failures += bool(findings)

    for name, edit, word in MUTATIONS:
        broken = edit(MASTER)
        findings = check_text(broken)
        if broken == MASTER:
            verdict = "NO-OP   "
        elif any(word in finding for finding in findings):
            verdict = "killed  "
        else:
            verdict = "SURVIVED"
        failures += verdict != "killed  "
        print(f"  {verdict}  {name} -> {word!r}")
        if verdict != "killed  ":
            for finding in findings or ["(no findings)"]:
                print(f"            {finding}")

    print(f"check_marks: self-test {len(CONTROLS)} control(s), {len(MUTATIONS)} mutation(s), "
          f"{failures} failure(s)")
    return 1 if failures else 0


def main(argv: list[str]) -> int:
    if argv == ["--self-test"]:
        return self_test()
    if any(arg.startswith("-") for arg in argv):
        print("usage: python tools/check_marks.py [FILE ...] | --self-test")
        return 2

    targets = [Path(arg) for arg in argv] or list(DEFAULT_MARKS)
    findings: list[str] = []
    for target in targets:
        findings.extend(check_file(target))

    for finding in findings:
        print(f"  {finding}")

    print(f"check_marks: {len(targets)} file(s), {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
