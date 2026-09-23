import math
import unittest
import xml.etree.ElementTree as ET
from enhance_snake import (NS, SPLIT, REJOIN, HIDE, enhance, parse_route,
                           position, companion_head, companion_segment)

ROUTE = [(0., (0., 0.)), (40., (800., 0.)), (50., (800., 80.)),
         (90., (0., 80.)), (100., (0., 0.))]
SOURCE = ('<svg xmlns="http://www.w3.org/2000/svg"><desc>snk</desc>'
          '<style>.s{animation:s0 10000ms linear infinite}'
          '@keyframes s0{0%,100%{transform:translate(0px,0px)}'
          '40%{transform:translate(800px,0px)}50%{transform:translate(800px,80px)}'
          '90%{transform:translate(0px,80px)}}'
          '.c{animation:c0 10000ms infinite}</style>'
          '<rect class="c c0" x="2" y="2"/><rect class="s s0" width="14"/></svg>')


class SnakeTests(unittest.TestCase):
    def test_opposite_direction_after_fork(self):
        a0, a1 = position(ROUTE, 24), position(ROUTE, 25)
        b0, b1 = companion_head(ROUTE, 24), companion_head(ROUTE, 25)
        dot = sum((y-x)*(v-u) for x,y,u,v in zip(a0,a1,b0,b1))
        self.assertLess(dot, 0, "heads must move in opposing directions")

    def test_different_routes_until_late_reunion(self):
        for t in range(30, 90):
            a, b = position(ROUTE, t), companion_head(ROUTE, t)
            self.assertGreater(math.dist(a, b), 20, t)
        self.assertEqual(companion_head(ROUTE, SPLIT), position(ROUTE, SPLIT))
        self.assertEqual(companion_head(ROUTE, REJOIN), position(ROUTE, REJOIN))
        self.assertGreater(REJOIN, 90)

    def test_fork_and_reunion_continuity(self):
        for boundary in (SPLIT, REJOIN):
            for delta in (-0.0001, 0.0001):
                self.assertLess(math.dist(companion_head(ROUTE, boundary+delta),
                                          position(ROUTE, boundary)), 0.01)

    def test_body_rejoins_before_disappearing(self):
        for index in range(6):
            self.assertEqual(companion_segment(ROUTE, ROUTE, index, HIDE),
                             position(ROUTE, HIDE))

    def test_preserves_contribution_cells_and_main_path(self):
        root = ET.fromstring(enhance(SOURCE))
        self.assertEqual(root.findall(f"{{{NS}}}rect")[0].attrib,
                         {"class":"c c0", "x":"2", "y":"2"})
        clone = root.find(f"{{{NS}}}g")
        self.assertEqual(clone[0].get("class"), "twin twin-0")
        self.assertEqual(root.findall(f"{{{NS}}}rect")[1].get("class"), "s s0")
        self.assertIn("twin-route-0", root.find(f"{{{NS}}}style").text)

    def test_route_parser_and_interpolation(self):
        css = ET.fromstring(SOURCE).find(f"{{{NS}}}style").text
        self.assertEqual(parse_route(css, "s0"), ROUTE)
        self.assertEqual(position(ROUTE, 20), (400, 0))

    def test_duration_and_reduced_motion(self):
        text = enhance(SOURCE)
        self.assertNotIn("10000ms", text)
        self.assertIn("24000ms", text)
        self.assertIn("prefers-reduced-motion", text)
        self.assertIn("60000ms", enhance(SOURCE.replace("10000", "60000")))

    def test_unsupported_or_repeated_input(self):
        for source in ("<svg/>", SOURCE.replace('class="s s0"', 'class="x"'),
                       SOURCE.replace("c0 10000ms", "c0 5000ms"), enhance(SOURCE),
                       SOURCE.replace("@keyframes s0", "@keyframes missing")):
            with self.assertRaises(ValueError):
                enhance(source)


if __name__ == "__main__":
    unittest.main()
