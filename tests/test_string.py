import unittest
from main import Assembler, AssemblerException


class TestStringSupport(unittest.TestCase):
    def _simple(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'#LAYOUT ROM0[$0000, $4000], AT[0]\n#SECTION "TEST", ROM0[0] {{\n{code}\n}}')
        s = a.link()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].base_address, 0)
        return s[0].data

    def test_basic(self):
        self.assertEqual(self._simple('db "123"'), b'123')
        self.assertEqual(self._simple(r'db "\\"'), b'\\')
        self.assertEqual(self._simple(r'db "\n"'), b'\n')
        self.assertEqual(self._simple(r'db "\""'), b'\"')
        self.assertEqual(self._simple(r'db "complex\"escape\""'), b'complex\"escape\"')

    def test_variable(self):
        self.assertEqual(self._simple('VAR = "123"\ndb VAR'), b'123')
