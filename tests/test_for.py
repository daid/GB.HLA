import unittest
from main import Assembler, AssemblerException


class TestAssemblerFor(unittest.TestCase):
    def _simple(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'#LAYOUT ROM0[$0000, $4000], AT[0]\n#SECTION "TEST", ROM0[0] {{    \n{code}\n }}')
        s = a.link()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].base_address, 0)
        return s[0].data

    def test_basic(self):
        self.assertEqual(self._simple("#FOR n, 0, 10 { db n }"), b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09')

    def test_reverse(self):
        self.assertEqual(self._simple("#FOR n, 10, 0 { db n }"), b'\x0A\x09\x08\x07\x06\x05\x04\x03\x02\x01')

    def test_empty(self):
        self.assertEqual(self._simple("#FOR n, 0, 0 { db n }"), b'')

    def test_math(self):
        self.assertEqual(self._simple("#FOR n, 0, 1 + 2 { db n }"), b'\x00\x01\x02')
