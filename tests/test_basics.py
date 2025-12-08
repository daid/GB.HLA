import unittest
from main import Assembler, AssemblerException


class TestAssemblerBasics(unittest.TestCase):
    def _simple(self, code: str) -> bytes:
        a = Assembler()
        a.process_code(f'#LAYOUT ROM0[$0000, $4000], AT[0]\n#SECTION "TEST", ROM0[0] {{ {code}\n }}')
        s = a.link()
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0].base_address, 0)
        return s[0].data

    def test_db(self):
        self.assertEqual(self._simple("db $12, $34"), b'\x12\x34')
    def test_dw(self):
        self.assertEqual(self._simple("dw $1234"), b'\x34\x12')
    def test_label(self):
        self.assertEqual(self._simple("dw label\nlabel:"), b'\x02\x00')
    def test_local_label(self):
        self.assertEqual(self._simple("dw label, label.part\nlabel: ds 1\n.part:"), b'\x04\x00\x05\x00\x00')
    def test_non_scope_label(self):
        self.assertEqual(self._simple("dw label, __part, label.part\nlabel: ds 1\n__part: ds 1\n.part:"), b'\x06\x00\x07\x00\x08\x00\x00\x00')
    def test_ds(self):
        self.assertEqual(self._simple("ds 2"), b'\x00\x00')
    def test_var(self):
        self.assertEqual(self._simple("VALUE = $1 + 3\ndb VALUE"), b'\x04')
    def test_var2(self):
        self.assertEqual(self._simple("VALUE = $1 + 3\ndb VALUE\nVALUE = 3 * 3\ndb VALUE"), b'\x04\x09')
    def test_var3(self):
        self.assertEqual(self._simple("VALUE = 2\ndb label | VALUE\nlabel:"), b'\x03')
    def test_assert(self):
        with self.assertRaises(AssemblerException) as context:
            self._simple('#ASSERT 0')
        self.assertIn("Assertion failure", context.exception.message)
    def test_assert_msg(self):
        with self.assertRaises(AssemblerException) as context:
            self._simple('#ASSERT 0, "FAIL"')
        self.assertIn("FAIL", context.exception.message)
    def test_assert_label(self):
        with self.assertRaises(AssemblerException) as context:
            self._simple('#ASSERT label != 0, "FAIL"\nlabel:')
        self.assertIn("FAIL", context.exception.message)
    def test_anonymous_label(self):
        self.assertEqual(self._simple("dw :+\n:\ndw :-"), b'\x02\x00\x02\x00')
        self.assertEqual(self._simple(":\ndw :+\n:\ndw :-"), b'\x02\x00\x02\x00')
        self.assertEqual(self._simple(":\ndw :++\n:\ndw :--\n:"), b'\x04\x00\x00\x00')
    def test_line_continuation(self):
        self.assertEqual(self._simple("db $12, \\\n $34"), b'\x12\x34')
    def test_not(self):
        self.assertEqual(self._simple("#IF !0 { db 1\n }"), b'\x01')
