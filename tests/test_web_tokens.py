"""The design system's rules, checked (ADR 0007).

1. Each sRGB data colour in web/tokens.css names the Radix step it copies in a comment; the hex must
   equal that step in the vendored file. MapLibre cannot read display-p3, so the hex is duplicated
   on purpose, and this test is what stops it drifting.
2. No raw hex colour appears in the pages, scripts or stylesheets, only in tokens.css and vendor/.
"""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
TOKEN_LINE = re.compile(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6});\s*/\*\s*([a-z]+)-(\d+)\s*\*/")


def radix_srgb(scale: str, step: int) -> str:
    css = (WEB / "vendor" / "radix-colors" / f"{scale}.css").read_text()
    # the first definition of a step is the sRGB one; the display-p3 blocks come after it
    return re.search(rf"--{scale}-{step}:\s*(#[0-9a-fA-F]{{6}})", css).group(1).lower()


def test_data_colours_equal_the_radix_step_they_name():
    tokens = TOKEN_LINE.findall((WEB / "tokens.css").read_text())
    assert len(tokens) >= 15  # rooftop/attic/redevelopment, classes and the ramp are all there
    wrong = [
        f"--{name}: {hex_} is not {scale}-{step} ({radix_srgb(scale, int(step))})"
        for name, hex_, scale, step in tokens
        if hex_.lower() != radix_srgb(scale, int(step))
    ]
    assert not wrong, wrong


def test_the_three_category_colours_are_the_validated_ones():
    tokens = {n: h.lower() for n, h, _, _ in TOKEN_LINE.findall((WEB / "tokens.css").read_text())}
    # orange-11, cyan-10, violet-10: run through the colour-blind validator (CVD dE >= 15)
    assert tokens["data-rooftop"] == "#cc4e00"
    assert tokens["data-attic"] == "#0797b9"
    assert tokens["data-redevelopment"] == "#654dc4"


def test_no_raw_hex_outside_tokens_and_vendor():
    offenders = []
    for path in [*WEB.glob("*.css"), *WEB.glob("*.js"), *WEB.glob("*.html")]:
        if path.name == "tokens.css":
            continue
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if (
                re.search(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![\w-])", line)
                and "href=" not in line
            ):
                offenders.append(f"{path.name}:{n}: {line.strip()[:70]}")
    assert not offenders, offenders
