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
        if z {
            db $F0
        }
        if nz {
            db $0F
        }
        """)
        self.assertEqual(rom, b'\x20\x01\xF0\x28\x01\x0F')
    
    def test_else(self):
        rom = self._full("""
        if z {
            db $F0
        } else {
            db $0F
        }
        """)
        self.assertEqual(rom, b'\x20\x03\xF0\x18\x01\x0F')

    def test_nested(self):
        rom = self._full("""
        if z {
            db $F0
            if nz {
                db $FF
            }
            db $EE
        } else {
            db $0F
        }
        """)
        self.assertEqual(rom, b'\x20\x07\xF0\x28\x01\xFF\xEE\x18\x01\x0F')

    def test_prefix(self):
        rom = self._full("""
#MACRO my_if {
    and a
} > if z
#MACRO my_if _cond {
    and b
} > if _cond
        my_if {
            db $F0
        }
        my_if nz {
            db $F0
        } else {
            db $0F
        }
        """)
        self.assertEqual(rom, b'\xA7\x20\x01\xF0\xA0\x28\x03\xF0\x18\x01\x0F')
