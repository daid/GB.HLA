import unittest
from main import Assembler, AssemblerException


class TestAssemblerSections(unittest.TestCase):
    def test_section_load(self):
        a = Assembler()
        a.process_code("""
#LAYOUT ROM0[$0000, $4000], AT[0]
#SECTION "TEST", ROM0[0] {
    db 1
preLoadLabel:   
    #LOAD "LOAD", ROM0[$10] {
inLoadLabel:
        db 2
    }
postLoadLabel:
    db 3
}
""")
        s = a.link()
        self.assertEqual(len(s), 2)
        self.assertEqual(s[0].base_address, 0)
        self.assertEqual(s[1].base_address, 16)
        self.assertEqual(s[0].data, b'\x01\x02\x03')
        self.assertEqual(s[1].data, b'\x02')
        self.assertEqual(a.get_label("preLoadLabel"), (s[0], 1))
        self.assertEqual(a.get_label("inLoadLabel"), (s[1], 0))
        self.assertEqual(a.get_label("postLoadLabel"), (s[0], 2))