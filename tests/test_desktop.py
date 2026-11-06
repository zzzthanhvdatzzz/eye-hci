import unittest
from unittest.mock import Mock
from eye_hci.desktop import WindowAPI

class WindowTests(unittest.TestCase):
    def test_compact_floats_and_restores_size(self):
        api=WindowAPI();window=Mock(width=1220,height=860);api._window=window
        self.assertEqual(api.compact(True),{'compact':True,'on_top':True})
        window.resize.assert_called_with(420,540)
        self.assertTrue(window.on_top)
        api.compact(True)  # Repeated requests must not replace the original size.
        api.compact(False)
        window.resize.assert_called_with(1220,860)
        self.assertFalse(window.on_top)
    def test_minimize(self):
        api=WindowAPI();api._window=Mock();api.minimize();api._window.minimize.assert_called_once()
    def test_bad_compact_value(self):
        with self.assertRaises(ValueError):WindowAPI().compact('true')
