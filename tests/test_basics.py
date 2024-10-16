import unittest
from main import Assembler


class TestAssemblerBasics(unittest.TestCase):
    def _simple(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'#SECTION "TEST", ROM0[0] {{ {code}\n }}')
        s = a.link()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].base_address, 0)
        return s[0].data

    def test_basic(self):
        self.assertEqual(self._simple("db $12, $34"), b'\x12\x34')
        self.assertEqual(self._simple("dw $1234"), b'\x34\x12')
        self.assertEqual(self._simple("dw label\nlabel:"), b'\x02\x00')


if __name__ == '__main__':
    unittest.main()
