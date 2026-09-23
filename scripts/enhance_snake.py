"""Give the contribution snake an independent, counter-running companion."""
import argparse
import copy
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
SPLIT, REJOIN, HIDE = 20.0, 92.0, 97.0
ET.register_namespace("", NS)


def parse_route(css, name):
    """Read the translate keyframes emitted by Platane/snk."""
    match = re.search(r"@keyframes\s+" + re.escape(name) + r"\{((?:[^{}]|\{[^{}]*\})*)\}", css)
    if not match:
        raise ValueError(f"missing route: {name}")
    frames = {}
    for selectors, x, y in re.findall(
        r"([\d.% ,]+)\{transform:translate\((-?[\d.]+)px,\s*(-?[\d.]+)px\)\}",
        match.group(1),
    ):
        for selector in selectors.split(","):
            frames[float(selector.strip().rstrip("%"))] = (float(x), float(y))
    if 0.0 not in frames or len(frames) < 2:
        raise ValueError(f"unsupported route: {name}")
    frames.setdefault(100.0, frames[0.0])
    return sorted(frames.items())


def position(route, percent):
    percent = max(0.0, min(100.0, percent))
    for (ta, a), (tb, b) in zip(route, route[1:]):
        if ta <= percent <= tb:
            weight = (percent - ta) / (tb - ta)
            return tuple(x + (y - x) * weight for x, y in zip(a, b))
    return route[-1][1]


def companion_head(route, percent):
    if percent <= SPLIT or percent >= REJOIN:
        return position(route, percent)
    progress = (percent - SPLIT) / (REJOIN - SPLIT)
    # The main snake travels forward over 72% of its timeline. The companion
    # follows the complementary 28% BACKWARDS, ending at the same late point.
    reverse_phase = (SPLIT - progress * (100 - REJOIN + SPLIT)) % 100
    x, y = position(route, reverse_phase)
    # A separate lane also distinguishes the geometrical paths between forks.
    return x, y + 24 * math.sin(math.pi * progress) ** 2


def companion_segment(head_route, own_route, index, percent):
    original = position(own_route, percent)
    if percent <= SPLIT or percent >= HIDE:
        return original
    # Tail follows the companion's own history instead of copying the main
    # snake's segment animations. Blend only at the fork and final reunion.
    independent = companion_head(head_route, max(0, percent - index * 0.85))
    weight = min(1.0, (percent - SPLIT) / 3, (HIDE - percent) / 3)
    weight = weight * weight * (3 - 2 * weight)
    return tuple(a + (b - a) * weight for a, b in zip(original, independent))


def enhance(source):
    root = ET.fromstring(source)
    if root.find(".//*[@id='split-companion']") is not None:
        raise ValueError("SVG has already been enhanced")
    style = root.find(f"{{{NS}}}style")
    if style is None or not style.text:
        raise ValueError("missing animation stylesheet")
    snakes = [element for element in list(root)
              if "s" in element.get("class", "").split()]
    if not snakes:
        raise ValueError("no snake segments found")
    durations = set(re.findall(r"(\d+)ms", style.text))
    if len(durations) != 1:
        raise ValueError("expected one shared animation duration")
    duration = max(int(next(iter(durations))), 24000)
    routes = []
    for element in snakes:
        names = [c for c in element.get("class", "").split() if re.fullmatch(r"s\d+", c)]
        if len(names) != 1:
            raise ValueError("unsupported snake segment")
        routes.append(parse_route(style.text, names[0]))
    style.text = re.sub(r"\d+ms", f"{duration}ms", style.text)
    style.text += f"""
#split-companion{{opacity:0;animation:companion-visibility {duration}ms linear infinite}}
@keyframes companion-visibility{{
  0%,20%{{opacity:0}}20.1%,96.8%{{opacity:1}}97%,100%{{opacity:0}}
}}
.twin{{shape-rendering:geometricPrecision;fill:#d5b878;
animation-duration:{duration}ms;animation-timing-function:linear;animation-iteration-count:infinite}}
@media(prefers-reduced-motion:reduce){{
.s,.c,.u,.twin,#split-companion{{animation:none!important}}
#split-companion{{display:none}}
}}
"""
    group = ET.Element(f"{{{NS}}}g", {"id": "split-companion", "aria-hidden": "true"})
    # Half-percent samples plus exact fork/merge boundaries make a smooth,
    # self-contained SVG without scripts or external dependencies.
    times = sorted({i / 2 for i in range(201)} | {SPLIT, REJOIN, HIDE})
    for index, (element, route) in enumerate(zip(snakes, routes)):
        duplicate = copy.deepcopy(element)
        duplicate.attrib.pop("id", None)
        duplicate.attrib.pop("style", None)
        duplicate.set("class", f"twin twin-{index}")
        group.append(duplicate)
        frames = []
        for t in times:
            x, y = companion_segment(routes[0], route, index, t)
            frames.append(f"{t:g}%{{transform:translate({x:.3f}px,{y:.3f}px)}}")
        style.text += f"@keyframes twin-route-{index}" + "{" + "".join(frames) + "}"
        style.text += f".twin-{index}{{animation-name:twin-route-{index}}}"
    root.append(group)
    title = ET.Element(f"{{{NS}}}title")
    title.text = "Two snakes take opposite routes and reunite near the end"
    root.insert(0, title)
    desc = root.find(f"{{{NS}}}desc")
    if desc is not None:
        desc.text = ((desc.text or "") +
                     ". A gold companion follows its own reverse route from 20% "
                     "of the loop, reunites at 92%, and becomes one snake by 97%. "
                     "Contribution data is unchanged.")
    return ET.tostring(root, encoding="unicode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    outputs = [(path, enhance(path.read_text(encoding="utf-8-sig"))) for path in args.files]
    for path, text in outputs:
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
