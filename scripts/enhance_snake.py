"""Add a split-and-rejoin companion to Platane/snk SVGs."""
import argparse
import copy
import re
from pathlib import Path
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def enhance(source: str) -> str:
    root = ET.fromstring(source)
    if root.find(f".//*[@id='split-companion']") is not None:
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
    # Keep contribution-cell clearing, progress and both snakes synchronized.
    duration = max(int(next(iter(durations))), 24000)
    style.text = re.sub(r"\d+ms", f"{duration}ms", style.text)
    style.text += f"""
#split-companion {{
  opacity:0;
  animation:split-rejoin {duration}ms linear infinite;
}}
#split-companion .s {{ fill:#d5b878; }}
@keyframes split-rejoin {{
  0%,20% {{opacity:0;transform:translate(0,0)}}
  22% {{opacity:1;transform:translate(0,0)}}
  28%,60% {{opacity:1;transform:translate(0,16px)}}
  69% {{opacity:1;transform:translate(0,0)}}
  70%,100% {{opacity:0;transform:translate(0,0)}}
}}
@media(prefers-reduced-motion:reduce) {{
  .s,.c,.u,#split-companion {{animation:none!important}}
  #split-companion {{display:none}}
}}
"""
    companion = ET.Element(f"{{{NS}}}g", {"id": "split-companion", "aria-hidden": "true"})
    for element in snakes:
        duplicate = copy.deepcopy(element)
        duplicate.attrib.pop("id", None)
        companion.append(duplicate)
    root.append(companion)
    title = ET.Element(f"{{{NS}}}title")
    title.text = "GitHub contributions: one snake, two paths, one again"
    root.insert(0, title)
    desc = root.find(f"{{{NS}}}desc")
    if desc is not None:
        desc.text = ((desc.text or "") +
                     ". Custom visual effect: a gold companion splits off and rejoins "
                     "the main snake during each loop. Contribution data is unchanged.")
    return ET.tostring(root, encoding="unicode")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    # Transform all files successfully before overwriting any.
    outputs = [(path, enhance(path.read_text(encoding="utf-8"))) for path in args.files]
    for path, text in outputs:
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
