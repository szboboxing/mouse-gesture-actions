from __future__ import annotations

import unittest

from display_controls import _step_value


class DisplayValueTests(unittest.TestCase):
    def test_adjustment_uses_five_percent_step(self) -> None:
        self.assertEqual(_step_value(50, 0, 100, 1), 55)
        self.assertEqual(_step_value(50, 0, 100, -1), 45)

    def test_adjustment_stays_inside_monitor_range(self) -> None:
        self.assertEqual(_step_value(99, 0, 100, 1), 100)
        self.assertEqual(_step_value(1, 0, 100, -1), 0)

    def test_invalid_direction_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _step_value(50, 0, 100, 0)


if __name__ == "__main__":
    unittest.main()
