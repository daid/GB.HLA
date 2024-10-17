from typing import List, Optional, Dict, Tuple
import binascii
import os
from tokenizer import Token, Tokenizer
from expression import AstNode, parse_expression
from exception import AssemblerException
from macrodb import MacroDB


def tokens_to_string(tokens: List[Token]) -> str:
    result = ""
    for t in tokens:
        result += str(t.value)
    return result

def params_to_string(params: List[List[Token]]) -> str:
    return ", ".join(tokens_to_string(p) for p in params)


class Layout:
    def __init__(self, name: str, start_addr: int, end_addr: int):
        self.name = name
        self.start_addr = start_addr
        self.end_addr = end_addr
        self.rom_location = None


class Section:
    def __init__(self, layout: Layout, name: str, base_address: Optional[int] = None, bank: Optional[int] = None) -> None:
        self.layout = layout
        self.name = name
        self.base_address = base_address if base_address is not None else -1
        self.bank = bank
        self.data = bytearray()
        self.link: Dict[int, Tuple[int, AstNode]] = {}
        self.asserts: List[Tuple[int, AstNode, str]] = []

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
        self.__constants = {}
        self.__labels = {}
        self.__sections = []
        self.__current_scope = None
        self.__include_paths = [os.path.dirname(__file__)]
        self.__layouts = {}
    
    def process_file(self, filename):
        print(f"Processing file: {filename}")
        self.process_code(open(filename, "rt").read(), filename=filename)

    def _include_file(self, filename: Token):
        for path in self.__include_paths:
            full_path = os.path.join(path, filename.value)
            if os.path.exists(full_path):
                return self.process_file(full_path)
        raise AssemblerException(filename, "Include not found")

    def process_code(self, code, *, filename="[string]"):
        self.__section_stack = []
        self.__current_scope = None
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
            elif start.isA('DIRECTIVE', '#INCLUDE'):
                params = self._fetch_parameters(tok)
                if len(params) != 1 or len(params[0]) != 1 or params[0][0].kind != 'STRING':
                    raise AssemblerException(start, "Syntax error")
                self._include_file(params[0][0])
            elif start.isA('DIRECTIVE', '#LAYOUT'):
                self._define_layout(start, tok)
            elif start.isA('DIRECTIVE', '#SECTION'):
                self._start_section(start, tok)
            elif start.isA('DIRECTIVE', '#ASSERT'):
                message = ""
                conditions = []
                for condition in self._fetch_parameters(tok):
                    condition = self._process_expression(condition)
                    if condition.kind == 'value' and condition.token.kind == 'STRING':
                        message = condition.token.value
                    else:
                        condition = self._resolve_expr(None, condition)
                        if condition.kind == 'value' and condition.token.kind == 'NUMBER':
                            if condition.token.value == 0:
                                raise AssemblerException(condition.token, "Assertion failure")
                        else:
                            conditions.append(condition)
                for condition in conditions:
                    self.__section_stack[-1].asserts.append((len(self.__section_stack[-1].data), condition, message))
            elif start.isA('ID', 'DS'):
                for param in self._fetch_parameters(tok):
                    param = self._process_expression(param)
                    if param.kind != 'value':
                        raise AssemblerException(param.token, "DS needs a constant number")
                    if param.token.kind != 'NUMBER':
                        raise AssemblerException(param.token, "DS needs a constant number")
                    self.__section_stack[-1].data += bytes(param.token.value)
            elif start.isA('ID', 'DB'):
                for param in self._fetch_parameters(tok):
                    self.__section_stack[-1].add8(self._process_expression(param))
            elif start.isA('ID', 'DW'):
                for param in self._fetch_parameters(tok):
                    self.__section_stack[-1].add16(self._process_expression(param))
            elif start.isA('ID') and tok.peek().isA('='):
                tok.pop()
                params = self._fetch_parameters(tok)
                if len(params) != 1:
                    raise AssemblerException(start, "Syntax error")
                expr = self._resolve_expr(None, self._process_expression(params[0]))
                if not expr.is_number():
                    raise AssemblerException(expr.token, "Assignment requires constant expression")
                self.__constants[start.value] = expr.token.value
            elif start.isA('ID') and tok.peek().isA('LABEL'):
                tok.pop()
                label = start.value
                if start.value.startswith("."):
                    label = f"{self.__current_scope}{label}"
                else:
                    self.__current_scope = label
                if label in self.__labels:
                    raise AssemblerException(start, "Duplicate label")
                self.__labels[label] = (self.__section_stack[-1], len(self.__section_stack[-1].data))
            elif start.isA('ID'):
                self._process_statement(start, tok)
            elif start.isA('}'):
                self.__section_stack.pop()
            else:
                raise AssemblerException(start, f"Syntax error")
        if self.__section_stack:
            raise AssemblerException(tok.pop(), f"EOF reached with section open")

    def link(self):
        for section in self.__sections:
            for offset, expr, message in section.asserts:
                expr = self._resolve_expr(section.base_address + offset, expr)
                if expr.kind != 'value' or expr.token.kind != 'NUMBER':
                    print(expr)
                    raise AssemblerException(expr.token, f"Assertion failure (symbol not found?)")
                if expr.token.value == 0:
                    raise AssemblerException(expr.token, f"Assertion failure: {message}")
            for offset, (link_size, expr) in section.link.items():
                expr = self._resolve_expr(section.base_address + offset, expr)
                if expr.kind != 'value':
                    raise AssemblerException(expr.token, f"Failed to parse linking {expr}, symbol not found?")
                if not expr.token.isA('NUMBER'):
                    raise AssemblerException(expr.token, f"Expected a number.")
                if link_size == 1:
                    if expr.token.value < -128 or expr.token.value > 255:
                        raise AssemblerException(expr.token, f"Value out of range")
                    section.data[offset] = expr.token.value & 0xFF
                elif link_size == 2:
                    if expr.token.value < 0 or expr.token.value > 0xFFFF:
                        raise AssemblerException(expr.token, f"Value out of range")
                    section.data[offset] = expr.token.value & 0xFF
                    section.data[offset+1] = expr.token.value >> 8
        return self.__sections

    def _define_layout(self, start: Token, tok: Tokenizer):
        params = self._fetch_parameters(tok)
        if len(params) < 1:
            raise AssemblerException(start, "Expected name of section layout")
        name, (start_addr, end_addr) = self._bracket_param(params[0], 2)
        if name.value in self.__layouts:
            raise AssemblerException(start, "Duplicate layout name")
        layout = Layout(name.value, start_addr.token.value, end_addr.token.value)
        for param in params[1:]:
            pkey, pvalue = self._bracket_param(param)
            if pkey.value == 'AT':
                if len(pvalue) == 0:
                    raise AssemblerException(pkey, "AT requires an argument")
                layout.rom_location = pvalue[0].token.value
        self.__layouts[name.value] = layout

    def _start_section(self, start: Token, tok: Tokenizer):
        params = self._fetch_parameters(tok, params_end='{')
        if len(params) < 2:
            raise AssemblerException(start, "Expected name and type of section")
        name = self._process_expression(params[0])
        if name.kind != "value" or name.token.kind != "STRING":
            raise AssemblerException(name.token, "Expected name of section")
        if not params[1][0].isA('ID'):
            raise AssemblerException(name.token, "Expected type of section")
        section_type, section_type_param = self._bracket_param(params[1])
        address = -1
        if section_type_param:
            address = section_type_param[0].token.value
        if section_type.value not in self.__layouts:
            raise AssemblerException(section_type, "Section type not found")
        layout = self.__layouts[section_type.value]
        if address > -1 and not (layout.start_addr <= address < layout.end_addr):
            raise AssemblerException(section_type, "Address out of range for section")
        self.__section_stack.append(Section(layout, name.token.value, address))
        self.__sections.append(self.__section_stack[-1])

    def _process_statement(self, start: Token, tok: Tokenizer):
        params = self._fetch_parameters(tok)
        macro = self.__macro_db.get(start.value.upper(), params)
        if not macro:
            raise AssemblerException(start, f"Syntax error: {start.value} {params_to_string(params)}")
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
        params = self._fetch_parameters(tok, params_end='{')
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
        params = self._fetch_parameters(tok, params_end='{')
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

    def _fetch_parameters(self, tok: Tokenizer, *, params_end='NEWLINE') -> List[List[Token]]:
        params = []
        if tok.match(params_end):
            return params
        param = []
        params.append(param)
        brackets = 0
        while not tok.match(params_end):
            t = tok.pop()
            if t.kind == 'EOF':
                if params_end != 'NEWLINE':
                    raise AssemblerException(t, "Unexpected end of file")
                break
            if t.kind == '(' or t.kind == '[' or t.kind == '{':
                brackets += 1
            elif t.kind == ')' or t.kind == ']' or t.kind == '}':
                brackets -= 1
                if brackets < 0:
                    raise AssemblerException(t, "Syntax error")
            if t.kind == ',' and brackets == 0:
                param = []
                params.append(param)
            else:
                if t.kind == 'ID' and t.value.startswith("."):
                    t.value = f"{self.__current_scope}{t.value}"
                param.append(t)
        return params

    def _bracket_param(self, tokens: List[Token], arg_count: Optional[int] = None):
        if tokens[0].kind != 'ID':
            raise AssemblerException(tokens[0], "Syntax error")
        if len(tokens) < 2:
            if arg_count is None:
                return tokens[0], ()
            raise SyntaxError(tokens[0], "Expected '['")
        if tokens[1].kind != '[':
            raise SyntaxError(tokens[1], "Expected '['")
        if tokens[-1].kind != ']':
            raise SyntaxError(tokens[-1], "Expected ']'")
        t = Tokenizer()
        t.prepend(tokens[2:-1])
        params = self._fetch_parameters(t)
        if arg_count is None:
            if len(params) != 1:
                raise SyntaxError(tokens[0], "Wrong number of parameters")
        else:
            if len(params) != arg_count:
                raise SyntaxError(tokens[0], "Wrong number of parameters")
        params = tuple(self._process_expression(param) for param in params)
        return tokens[0], params

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
            if start.kind == 'ID' and start.value in self.__constants:
                start.kind = 'NUMBER'
                start.value = self.__constants[start.value]
        return parse_expression(tokens)

    def _resolve_expr(self, offset: Optional[int], expr: AstNode) -> AstNode:
        if expr is None:
            return None
        if expr.kind == 'value' and expr.token.isA('ID'):
            if expr.token.value not in self.__labels:
                return expr
            section, section_offset = self.__labels[expr.token.value]
            expr.token = Token('NUMBER', section.base_address + section_offset, expr.token.line_nr, expr.token.filename)
        elif expr.kind == 'value' and expr.token.isA('CURADDR'):
            if offset is None:
                return expr
            expr.token = Token('NUMBER', offset, expr.token.line_nr, expr.token.filename)
        else:
            expr.left = self._resolve_expr(offset, expr.left)
            expr.right = self._resolve_expr(offset, expr.right)
            if expr.left and expr.left.is_number() and (expr.right is None or expr.right.is_number()):
                if expr.kind == '+':
                    if expr.right:
                        expr.token = Token('NUMBER', expr.left.token.value + expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
                    else:
                        expr.token = Token('NUMBER', expr.left.token.value, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '-':
                    if expr.right:
                        expr.token = Token('NUMBER', expr.left.token.value - expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
                    else:
                        expr.token = Token('NUMBER', -expr.left.token.value, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '&':
                    expr.token = Token('NUMBER', expr.left.token.value & expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '|':
                    expr.token = Token('NUMBER', expr.left.token.value | expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '>>':
                    expr.token = Token('NUMBER', expr.left.token.value >> expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '<<':
                    expr.token = Token('NUMBER', expr.left.token.value << expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '>':
                    expr.token = Token('NUMBER', 1 if expr.left.token.value > expr.right.token.value else 0, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '<':
                    expr.token = Token('NUMBER', 1 if expr.left.token.value < expr.right.token.value else 0, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '>=':
                    expr.token = Token('NUMBER', 1 if expr.left.token.value >= expr.right.token.value else 0, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '<=':
                    expr.token = Token('NUMBER', 1 if expr.left.token.value <= expr.right.token.value else 0, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '==':
                    expr.token = Token('NUMBER', 1 if expr.left.token.value == expr.right.token.value else 0, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '!=':
                    expr.token = Token('NUMBER', 1 if expr.left.token.value != expr.right.token.value else 0, expr.left.token.line_nr, expr.left.token.filename)
                else:
                    return expr
                expr.kind = 'value'
                expr.left = None
                expr.right = None
        return expr


if __name__ == "__main__":
    a = Assembler()
    a.process_file("gbz80/layout.asm")
    a.process_file("gbz80/instr.asm")
    a.process_file("gbz80/regs.asm")
    # import os
    # for f in sorted(os.listdir("../FFL3-Disassembly/src")):
    #     if f.endswith(".asm"):
    #         a.process_file("../FFL3-Disassembly/src/" + f)
    a.process_code(
    """
    #SECTION "Name", ROM0[$0000] {
    db $12, $34
    }""")

    rom = bytearray()
    for section in a.link():
        print(section)
