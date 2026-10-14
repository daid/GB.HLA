import unittest
from main import Assembler, AssemblerException


class TestIf(unittest.TestCase):
    def _full(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'#INCLUDE "gbz80/all.asm"\n#INCLUDE "gbz80/extra/if.asm"\n#SECTION "TEST", ROM0[0] {{ \n{code}\n }}')
        for section in a.link():
            if section.layout.name == "ROM0":
                return section.data
        return b'ERR'

    def test_basic(self):
        rom = self._full("""
        #IF 0 {
            db $F0
        }
        #IF 1 {
            db $0F
        }
        """)
        self.assertEqual(rom, b'\x0F')
    
    def test_else(self):
        rom = self._full("""
        #IF 0 {
            db $F0
        } ELSE {
            db $0F
        }
        """)
        self.assertEqual(rom, b'\x0F')

    def test_nested(self):
        rom = self._full("""
        #IF 1 {
            db $F0
            #IF 1 {
                db $FF
            }
            db $EE
        } ELSE {
            db $0F
        }
        """)
        self.assertEqual(rom, b'\xF0\xFF\xEE')
