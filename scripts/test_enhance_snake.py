import unittest
import xml.etree.ElementTree as ET
from enhance_snake import enhance, NS

SOURCE = '<svg xmlns="http://www.w3.org/2000/svg"><desc>snk</desc><style>.s{animation:s0 10000ms linear infinite}.c{animation:c0 10000ms infinite}</style><rect class="c c0" x="2" y="2"/><rect class="s s0" width="14"/><rect class="s s1" width="12"/></svg>'


class SnakeTests(unittest.TestCase):
    def test_clone_and_preserve_calendar(self):
        root = ET.fromstring(enhance(SOURCE))
        rects = root.findall(f"{{{NS}}}rect")
        self.assertEqual(len(rects), 3)
        cells = [r for r in rects if "c" in r.get("class").split()]
        self.assertEqual(cells[0].attrib, {"class": "c c0", "x": "2", "y": "2"})
        clone = root.find(f"{{{NS}}}g")
        self.assertEqual(clone.get("id"), "split-companion")
        self.assertEqual(len(clone), 2)
        for original, duplicate in zip(rects[1:], clone):
            self.assertEqual(original.attrib, duplicate.attrib)

    def test_shared_duration_and_merge(self):
        text = enhance(SOURCE)
        self.assertNotIn("10000ms", text)
        self.assertIn("24000ms", text)
        self.assertIn("70%,100%", text)
        self.assertIn("prefers-reduced-motion", text)

    def test_long_animation_not_accelerated(self):
        self.assertIn("60000ms", enhance(SOURCE.replace("10000", "60000")))

    def test_rejects_unsupported_or_duplicate_input(self):
        for source in ("<svg/>", SOURCE.replace('class="s s0"', 'class="x"').replace('class="s s1"', 'class="x"'),
                       SOURCE.replace("c0 10000ms", "c0 5000ms"), enhance(SOURCE)):
            with self.assertRaises(ValueError):
                enhance(source)


if __name__ == "__main__":
    unittest.main()
