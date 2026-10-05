from __future__ import annotations

import tkinter as tk
import unittest

from help_browser import HELP_TOPICS, HelpBrowser, open_help_browser
from version import APP_VERSION, VERSION_TAG


class HelpTopicsStructureTests(unittest.TestCase):
    def test_five_modules_present_in_order(self) -> None:
        self.assertEqual(
            list(HELP_TOPICS.keys()),
            ["gesture", "keyboard", "mouse_test", "tools", "window"],
        )

    def test_every_item_has_label_and_sections(self) -> None:
        for module_key, module in HELP_TOPICS.items():
            self.assertTrue(module["label"], module_key)
            self.assertGreaterEqual(len(module["items"]), 1, module_key)
            for item in module["items"]:
                self.assertIn("label", item)
                self.assertIn("sections", item)
                self.assertGreaterEqual(len(item["sections"]), 1)
                for heading, body in item["sections"]:
                    self.assertTrue(heading.strip())
                    self.assertTrue(body.strip())


class HelpBrowserNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.root.destroy()

    def setUp(self) -> None:
        self.browser = open_help_browser(self.root)

    def tearDown(self) -> None:
        try:
            self.browser._on_close()
        except tk.TclError:
            pass

    def _state(self, name: str) -> str:
        return str(getattr(self.browser, name).cget("state"))

    def test_home_initial_states(self) -> None:
        self.assertEqual(self.browser.path, [])
        self.assertEqual(self._state("btn_home"), "disabled")
        self.assertEqual(self._state("btn_up"), "disabled")
        self.assertEqual(self._state("btn_prev"), "disabled")
        self.assertEqual(self._state("btn_next"), "normal")
        self.assertEqual(self.browser.crumb_var.get(), "首页")

    def test_next_then_prev_walks_leaf_order(self) -> None:
        first_key = next(iter(HELP_TOPICS))
        self.browser.go_next()
        self.assertEqual(self.browser.path, [first_key, 0])
        self.assertEqual(self._state("btn_prev"), "disabled")
        self.browser.go_next()
        self.assertEqual(self.browser.path, [first_key, 1])
        self.assertEqual(self._state("btn_prev"), "normal")
        self.browser.go_prev()
        self.assertEqual(self.browser.path, [first_key, 0])

    def test_next_crosses_modules(self) -> None:
        keys = list(HELP_TOPICS)
        last_index_of_first = len(HELP_TOPICS[keys[0]]["items"]) - 1
        self.browser.navigate(keys[0], last_index_of_first)
        self.browser.go_next()
        self.assertEqual(self.browser.path, [keys[1], 0])

    def test_last_leaf_disables_next(self) -> None:
        last_module = list(HELP_TOPICS)[-1]
        last_index = len(HELP_TOPICS[last_module]["items"]) - 1
        self.browser.navigate(last_module, last_index)
        self.assertEqual(self._state("btn_next"), "disabled")
        self.assertEqual(self._state("btn_prev"), "normal")
        self.browser.go_next()
        self.assertEqual(self.browser.path, [last_module, last_index])

    def test_go_up_leaf_to_module_to_home(self) -> None:
        self.browser.navigate("gesture", 1)
        self.browser.go_up()
        self.assertEqual(self.browser.path, ["gesture"])
        self.browser.go_up()
        self.assertEqual(self.browser.path, [])
        self.assertEqual(self._state("btn_up"), "disabled")

    def test_go_home_from_anywhere(self) -> None:
        self.browser.navigate("window", 2)
        self.browser.go_home()
        self.assertEqual(self.browser.path, [])

    def test_module_page_neighbor_targets(self) -> None:
        self.browser.navigate("keyboard")
        start = len(HELP_TOPICS["gesture"]["items"])
        self.assertEqual(self.browser._neighbor_index(-1), start - 1)
        self.assertEqual(self.browser._neighbor_index(1), start)

    def test_navigate_jumps_and_reuses_window(self) -> None:
        again = open_help_browser(self.root, "tools", 0)
        self.assertIs(again, self.browser)
        self.assertEqual(self.browser.path, ["tools", 0])

    def test_close_clears_reference_then_reopens(self) -> None:
        self.browser._on_close()
        self.assertIsNone(getattr(self.root, "_help_browser", None))
        new_browser = open_help_browser(self.root)
        self.assertIsNot(new_browser, self.browser)
        self.assertTrue(new_browser.winfo_exists())
        new_browser._on_close()

    def test_title_contains_version_tag(self) -> None:
        self.assertIn(VERSION_TAG, self.browser.title())
        self.assertEqual(APP_VERSION, "2.5")


if __name__ == "__main__":
    unittest.main()
