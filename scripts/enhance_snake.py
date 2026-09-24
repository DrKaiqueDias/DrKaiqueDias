"""Add a second contribution snake that takes the opposite way around."""
import argparse
import copy
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
SPLIT, REJOIN, HIDE = 38.0, 88.0, 91.0
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


def path_distance(route, percent):
    percent = max(0.0, min(100.0, percent))
    travelled = 0.0
    for (start_time, start), (end_time, end) in zip(route, route[1:]):
        length = math.dist(start, end)
        if percent >= end_time:
            travelled += length
            continue
        if percent > start_time:
            travelled += length * (percent - start_time) / (end_time - start_time)
        break
    return travelled


def position_at_distance(route, distance):
    total = path_distance(route, 100.0)
    distance %= total
    for (_, start), (_, end) in zip(route, route[1:]):
        length = math.dist(start, end)
        if distance <= length:
            weight = 0.0 if length == 0 else distance / length
            return tuple(a + (b - a) * weight for a, b in zip(start, end))
        distance -= length
    return route[0][1]


def companion_head(route, percent):
    if percent <= SPLIT or percent >= REJOIN:
        return position(route, percent)
    split_distance = path_distance(route, SPLIT)
    travelled = path_distance(route, percent) - split_distance
    return position_at_distance(route, split_distance - travelled)


def companion_segment(head_route, own_route, index, percent):
    original = position(own_route, percent)
    if percent <= SPLIT or percent >= HIDE:
        return original
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
#split-companion{{opacity:0;animation:companion-visibility {duration}ms linear infinite;
filter:drop-shadow(0 0 2px #d5b878)}}
@keyframes companion-visibility{{
  0%,38%{{opacity:0}}38.6%,89.6%{{opacity:1}}91%,100%{{opacity:0}}
}}
.twin{{shape-rendering:geometricPrecision;fill:#e0bc63;
animation-duration:{duration}ms;animation-timing-function:linear;animation-iteration-count:infinite}}
@media(prefers-reduced-motion:reduce){{
.s,.c,.u,.twin,#split-companion{{animation:none!important}}
#split-companion{{display:none}}
}}
"""
    group = ET.Element(f"{{{NS}}}g", {"id": "split-companion", "aria-hidden": "true"})
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
    title.text = "Two snakes circle the contribution graph in opposite directions"
    root.insert(0, title)
    desc = root.find(f"{{{NS}}}desc")
    if desc is not None:
        desc.text = ((desc.text or "") +
                     ". A gold companion takes the opposite direction at the same "
                     "speed, meets the main snake at 88%, and becomes one by 91%. "
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


