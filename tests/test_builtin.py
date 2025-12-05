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

    def _full(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'#LAYOUT ROM0[$0000, $4000], AT[0]\n#SECTION "TEST", ROM0[0] {{ {code}\n }}')
        s = a.link()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].base_address, 0)
        return a.build_rom()

    def test_strlen(self):
        self.assertEqual(self._simple('db STRLEN("123")'), b'\x03')

    def test_bitlength(self):
        self.assertEqual(self._simple('db BIT_LENGTH(1)'), b'\x01')
        self.assertEqual(self._simple('db BIT_LENGTH(2)'), b'\x02')
        self.assertEqual(self._simple('db BIT_LENGTH(3)'), b'\x02')
        self.assertEqual(self._simple('db BIT_LENGTH(255)'), b'\x08')
        self.assertEqual(self._simple('db BIT_LENGTH(256)'), b'\x09')

    def test_checksum(self):
        self.assertEqual(self._full('db 1,2,3,4, CHECKSUM(0, 4)')[0:5], b'\x01\x02\x03\x04\x0A')

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

    def test_defined(self):
        self.assertEqual(self._simple('#IF DEFINED(x) { db 1\n } ELSE { db 2\n }'), b'\x02')
        self.assertEqual(self._simple('x = 1\n#IF DEFINED(x) { db 1\n } ELSE { db 2\n }'), b'\x01')
