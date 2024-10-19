import unittest
from main import Assembler, AssemblerException


class TestAssemblerFMacro(unittest.TestCase):
    def _simple(self, macro: str, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'{macro}\n#LAYOUT ROM0[$0000, $4000], AT[0]\n#SECTION "TEST", ROM0[0] {{ {code}\n }}')
        s = a.link()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].base_address, 0)
        return s[0].data

    def test_basic(self):
        self.assertEqual(self._simple("#FMACRO FUNC { 1 }", "db FUNC()"), b'\x01')

    def test_param(self):
        self.assertEqual(self._simple("#FMACRO FUNC _a { _a + 5 }", "db FUNC(1)"), b'\x06')

    def test_param2(self):
        self.assertEqual(self._simple("#FMACRO FUNC _a, _b { _a + _b }", "db FUNC(1, 2)"), b'\x03')

    def test_nested(self):
        self.assertEqual(self._simple("#FMACRO FUNC _a, _b { _a + _b }", "db FUNC(1, FUNC(2, 3))"), b'\x06')

    def test_overload(self):
        self.assertEqual(self._simple("#FMACRO FUNC _a { _a + 1 }\n#FMACRO FUNC 1 { 0 }", "db FUNC(1), FUNC(2)"), b'\x00\x03')
