from typing import List, Optional, Dict, Tuple
import binascii
from tokenizer import Token, Tokenizer
from expression import AstNode, parse_expression
from exception import AssemblerException
from macrodb import MacroDB


def tokens_to_string(tokens: List[Token]) -> str:
    result = ""
    for t in tokens:
        result += t.value
    return result

def params_to_string(params: List[List[Token]]) -> str:
    return ", ".join(tokens_to_string(p) for p in params)


class Section:
    def __init__(self, base_address: Optional[int] = None, bank: Optional[int] = None) -> None:
        self.base_address = base_address if base_address is not None else -1
        self.bank = bank
        self.data = bytearray()
        self.link: Dict[int, Tuple[int, AstNode]] = {}

    def add16(self, node: AstNode) -> None:
        if node.kind == 'value' and node.token.kind == 'NUMBER':
            self.data.append(node.token.value & 0xFF)
            self.data.append((node.token.value >> 8) & 0xFF)
        else:
            self.link[len(self.data)] = (2, node)
            self.data.append(0)
            self.data.append(0)

    def add8(self, node: AstNode) -> None:
        if node.kind == 'value' and node.token.kind == 'NUMBER':
            self.data.append(node.token.value)
        elif node.kind == 'value' and node.token.kind == 'STRING':
            self.data += node.token.value[1:-1].encode("ASCII")
        else:
            self.link[len(self.data)] = (1, node)
            self.data.append(0)

    def __repr__(self) -> str:
        if self.bank is not None:
            return f"Section@{self.bank:02x}:{self.base_address:04x} {binascii.hexlify(self.data).decode('ascii')}"
        if self.base_address > -1:
            return f"Section@{self.base_address:04x} {binascii.hexlify(self.data).decode('ascii')}"
        return f"Section {binascii.hexlify(self.data).decode('ascii')}"


class Assembler:
    def __init__(self):
        self.__macro_db = MacroDB()
        self.__func_db = MacroDB()
        self.__labels = {}
        self.__sections = []
    
    def process_file(self, filename):
        self.process_code(open(filename, "rt").read(), filename=filename)

    def process_code(self, code, *, filename="[string]"):
        section = Section()
        tok = Tokenizer()
        tok.add_code(code, filename=filename)
        while start := tok.pop():
            if start.isA('NEWLINE'):
                continue
            if start.isA('EOF'):
                break
            if start.isA('DIRECTIVE', '#MACRO'):
                self._add_macro(tok)
            elif start.isA('DIRECTIVE', '#FUNC'):
                self._add_function(tok)
            elif start.isA('DIRECTIVE', '#ASSERT'):
                conditions = self._fetch_parameters(tok)
                # TODO: Check if conditions are true
            elif start.isA('ID', 'DB'):
                for param in self._fetch_parameters(tok):
                    section.add8(self._process_expression(param))
            elif start.isA('ID', 'DW'):
                for param in self._fetch_parameters(tok):
                    section.add16(self._process_expression(param))
            elif start.isA('ID') and tok.peek().isA('LABEL'):
                tok.pop()
                if start.value in self.__labels:
                    raise AssemblerException(start, "Duplicate label")
                self.__labels[start.value] = (section, len(section.data))
            elif start.isA('ID'):
                self._process_statement(start, tok)
            else:
                raise AssemblerException(start, f"Syntax error")
        if section.data:
            self.__sections.append(section)
    
    def link(self):
        for section in self.__sections:
            for offset, (link_size, expr) in section.link.items():
                expr = self._resolve_expr(section.base_address + offset, expr)
                print(expr)

    def _process_statement(self, start: Token, tok: Tokenizer):
        params = self._fetch_parameters(tok)
        macro = self.__macro_db.get(start.value.upper(), params)
        if not macro:
            raise AssemblerException(start, f"Syntax error: {params_to_string([[start]] + params)}")
        macro, macro_args = macro
        prepend = []
        for token in macro.contents:
            if token.kind == 'ID' and token.value in macro_args:
                prepend += macro_args[token.value]
            else:
                prepend.append(token)
        tok.prepend(prepend)

    def _add_macro(self, tok: Tokenizer) -> None:
        name = tok.expect('ID')
        params = self._fetch_parameters(tok)
        content = []
        while token := tok.pop_raw():
            if token.isA('}'):
                break
            content.append(token)
        if token is None:
            raise AssemblerException(name, "Unterminated macro definition")
        if not content[-1].isA('NEWLINE'):
            content.append(Token('NEWLINE', '', 0, ''))
        self.__macro_db.add(name.value.upper(), params, content)

    def _add_function(self, tok: Tokenizer) -> None:
        name = tok.expect('ID')
        params = self._fetch_parameters(tok)
        content = []
        while token := tok.pop_raw():
            if token.isA('}'):
                break
            if token.isA('NEWLINE'):
                continue
            content.append(token)
        if token is None:
            raise AssemblerException(name, "Unterminated function definition")
        self.__func_db.add(name.value.upper(), params, content)

    def _fetch_parameters(self, tok: Tokenizer) -> List[List[Token]]:
        params = []
        if tok.match('NEWLINE') or tok.match('{'):
            return params
        param = []
        params.append(param)
        while not tok.match('NEWLINE') and not tok.match('{'):
            t = tok.pop()
            if t.isA(','):
                param = []
                params.append(param)
            else:
                param.append(t)
        return params

    def _process_expression(self, tokens: List[Token]) -> AstNode:
        for start_idx, start in enumerate(tokens):
            if start.kind == 'FUNC':
                args = []
                arg = []
                for end_idx in range(start_idx + 1, len(tokens)):
                    t = tokens[end_idx]
                    if t.isA(')'):
                        if arg:
                            args.append(arg)
                        func = self.__func_db.get(start.value.upper(), args)
                        if func is None:
                            raise AssemblerException(start, f"Function not found: {start.value}")
                        func, func_args = func
                        contents = []
                        for token in func.contents:
                            if token.kind == 'ID' and token.value in func_args:
                                contents += func_args[token.value]
                            else:
                                contents.append(token)
                        tokens = tokens[:start_idx] + contents + tokens[end_idx+1:]
                        return self._process_expression(tokens)
                    elif t.isA(','):
                        args.append(arg)
                        arg = []
                    else:
                        arg.append(tokens[end_idx])
                raise AssemblerException(start, f"Function not closed: {start.value}")
        return parse_expression(tokens)

    def _resolve_expr(self, offset: int, expr: AstNode) -> AstNode:
        if expr is None:
            return None
        expr.left = self._resolve_expr(offset, expr.left)
        expr.right = self._resolve_expr(offset, expr.right)
        if expr.kind == 'value' and expr.token.isA('ID'):
            if expr.token.value not in self.__labels:
                raise AssemblerException(expr.token, f"Label not found: {expr.token.value}")
            section, section_offset = self.__labels[expr.token.value]
            expr.token = Token('NUMBER', section.base_address + section_offset, expr.token.line_nr, expr.token.filename)
        elif expr.kind == 'value' and expr.token.isA('CURADDR'):
            expr.token = Token('NUMBER', offset, expr.token.line_nr, expr.token.filename)
        elif expr.kind == '+':
            expr.kind = 'value'
            if expr.right:
                expr.token = Token('NUMBER', expr.left.token.value + expr.right.token.value, expr.token.line_nr, expr.token.filename)
            else:
                expr.token = Token('NUMBER', expr.left.token.value, expr.token.line_nr, expr.token.filename)
        elif expr.kind == '-':
            expr.kind = 'value'
            if expr.right:
                expr.token = Token('NUMBER', expr.left.token.value - expr.right.token.value, expr.token.line_nr, expr.token.filename)
            else:
                expr.token = Token('NUMBER', -expr.left.token.value, expr.token.line_nr, expr.token.filename)
        return expr

a = Assembler()
a.process_file("gbz80.instr.asm")
a.process_code(
"""
label:
    nop
    dw -label
    jr label
    jp label
""")
a.link()
