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

    def test_strlen(self):
        self.assertEqual(self._simple('db STRLEN("123")'), b'\x03')

    def test_bank(self):
        a = Assembler()
        a.process_code('''
        #LAYOUT ROM[$0, $10], AT[0], BANKED[0, 10]
        #SECTION "TEST1", ROM, BANK[0] {
            label0: db BANK(label0), BANK(label1)
        }
        #SECTION "TEST2", ROM, BANK[1] {
            label1: db $23
        }
        ''')
        s = a.link()
        self.assertEqual(len(s), 2)
        self.assertEqual(s[0].bank, 0)
        self.assertEqual(s[0].data, b'\x00\x01')
