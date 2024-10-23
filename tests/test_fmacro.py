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

    def test_overload_with_macro(self):
        self.assertEqual(self._simple("#FMACRO FUNC _a { _a + 1 }\n#FMACRO FUNC 1 { 0 }\n#MACRO M _a { db 1 }\n#MACRO M 0 { db 2 }", "M FUNC(1)\nM FUNC(2)"), b'\x02\x01')

    def test_nest_builtin(self):
        self.assertEqual(self._simple("#FMACRO FUNC _a { _a + 1 }", 'db FUNC(STRLEN("123"))'), b'\x04')
