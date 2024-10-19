import unittest
from main import Assembler, AssemblerException


class TestAssemblerLayout(unittest.TestCase):
    def _build(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(code)
        a.link()
        return a.build_rom()

    def test_simple(self):
        self.assertEqual(self._build(
"""
    #LAYOUT ROM[0,4], AT[0]
    #SECTION "TEST", ROM {
        db 1, 2
    }
"""), b'\x01\x02\x00\x00')
        
    def test_two(self):
        self.assertEqual(self._build(
"""
    #LAYOUT ROM[0,4], AT[0]
    #SECTION "TEST", ROM {
        db 1, 2
    }
    #SECTION "TEST2", ROM {
        db 3, 4 
    }
"""), b'\x01\x02\x03\x04')
        
    def test_fixed(self):
        self.assertEqual(self._build(
"""
    #LAYOUT ROM[0,4], AT[0]
    #SECTION "TEST", ROM[2] {
        db 1, 2
    }
"""), b'\x00\x00\x01\x02')

    def test_banked(self):
        self.assertEqual(self._build(
"""
    #LAYOUT ROM[0,4], AT[0], BANKED[0, 2]
    #SECTION "TEST", ROM {
        db 1, 2
    }
    #SECTION "TEST", ROM, BANK[1] {
        db 3, 4
    }
    #SECTION "TEST", ROM {
        db 4, 5
    }
    #SECTION "TEST", ROM {
        db 6, 7
    }
"""), b'\x01\x02\x04\x05\x03\x04\x06\x07')


    def test_size(self):
        with self.assertRaises(AssemblerException) as context:
            self._build(
"""
    #LAYOUT ROM[0,2], AT[0]
    #SECTION "TEST", ROM {
        db 1, 2, 3, 4
    }
""")
        self.assertIn("Failed to allocate", context.exception.message)

    def test_ram(self):
        self.assertEqual(self._build(
"""
    #LAYOUT ROM[0,4], AT[0]
    #LAYOUT RAM[4,8]
    #SECTION "TEST", ROM {
        db 1, 2, 3, 4
    }
    #SECTION "RAM", RAM {
        ds 2
    }
"""), b'\x01\x02\x03\x04')
