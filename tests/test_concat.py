import unittest
from main import Assembler, AssemblerException


class TestAssemblerBuiltin(unittest.TestCase):
    def _simple(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'#LAYOUT ROM0[$0000, $4000], AT[0]\n#SECTION "TEST", ROM0[0] {{ {code}\n }}')
        s = a.link()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].base_address, 0)
        return s[0].data


    def test_basicconcat(self):
        self.assertEqual(self._simple(
            '''
            a = 1
            b = 2
            ab = 3
            db ab, a ## b
            '''), b'\x03\x03')
