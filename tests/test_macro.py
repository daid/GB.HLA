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
        self.assertEqual(self._simple("#MACRO TEST { db $01 }", "test"), b'\x01')

    def test_param(self):
        self.assertEqual(self._simple("#MACRO TEST _a { db $02, _a }", "test 1"), b'\x02\x01')

    def test_fixed_param(self):
        self.assertEqual(self._simple("#MACRO TEST _a { db $02, _a } #MACRO TEST a { db $03 }", "test a"), b'\x03')

    def test_fixed_param2(self):
        self.assertEqual(self._simple("#MACRO TEST _a, _b { db $02 } #MACRO TEST 1, _b { db $03 }", "test 1, 2"), b'\x03')

    def test_fixed_param3(self):
        self.assertEqual(self._simple("#MACRO TEST _a, _b { db $02 } #MACRO TEST 1, _b { db $03 } #MACRO TEST 1, 1 + _b { db $04 }", "test 1, 1 + 2"), b'\x04')

    def test_reassign(self):
        self.assertEqual(self._simple("#MACRO TEST _a { VAR = 1 + _a\ndb VAR }", "test 1\ntest 2"), b'\x02\x03')
