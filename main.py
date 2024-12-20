from typing import List, Optional, Dict, Tuple, Union
import binascii
import os
from tokenizer import Token, Tokenizer
from expression import AstNode, parse_expression
from exception import AssemblerException
from macrodb import MacroDB
from layout import Layout
from spaceallocator import SpaceAllocator
import builtin
import gfx


def tokens_to_string(tokens: List[Token]) -> str:
    result = ""
    for t in tokens:
        if t.kind == 'FUNC':
            result += f"{t.value}("
        elif t.kind == 'STRING':
            result += f'"{t.value}"'
        else:
            result += str(t.value)
    return result

def params_to_string(params: List[List[Token]]) -> str:
    return ", ".join(tokens_to_string(p) for p in params)


class PostRomBuild(Exception):
    pass


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
            self.data += node.token.value.encode("ASCII")
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
        self.__layouts: Dict[str, Layout] = {}
        self.__rom = None
        self.__post_build_link = []

    def process_file(self, filename):
        self.__include_paths.append(os.path.dirname(filename))
        self._process_file(filename)
        self.__include_paths.pop()

    def _process_file(self, filename):
        print(f"Processing file: {filename}")
        self.process_code(open(filename, "rt").read(), filename=filename)

    def _include_file(self, filename: Token):
        for path in self.__include_paths:
            full_path = os.path.join(path, filename.value)
            if os.path.exists(full_path):
                return self._process_file(full_path)
        raise AssemblerException(filename, "Include not found")

    def process_code(self, code, *, filename="[string]"):
        self.__section_stack = []
        self.__block_macro_stack = []
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
            elif start.isA('DIRECTIVE', '#FMACRO'):
                self._add_function(tok)
            elif start.isA('DIRECTIVE', '#INCLUDE'):
                params = self._fetch_parameters(tok)
                if len(params) != 1 or len(params[0]) != 1 or params[0][0].kind != 'STRING':
                    raise AssemblerException(start, "Syntax error")
                self._include_file(params[0][0])
            elif start.isA('DIRECTIVE', '#INCGFX'):
                params = self._fetch_parameters(tok)
                if len(params) != 1 or len(params[0]) != 1 or params[0][0].kind != 'STRING':
                    raise AssemblerException(start, "Syntax error")
                if not self.__section_stack:
                    raise AssemblerException(start, "Expression outside of section")
                self.__section_stack[-1].data += gfx.read(params[0][0].value)
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
                        try:
                            condition = self._resolve_expr(None, condition)
                        except PostRomBuild:
                            pass
                        conditions.append(condition)
                for condition in conditions:
                    if condition.kind == 'value' and condition.token.kind == 'NUMBER':
                        if condition.token.value == 0:
                            raise AssemblerException(condition.token, f"Assertion failure: {message}")
                    else:
                        self.__section_stack[-1].asserts.append((len(self.__section_stack[-1].data), condition, message))
            elif start.isA('ID', 'DS'):
                if not self.__section_stack:
                    raise AssemblerException(start, "Expression outside of section")
                for param in self._fetch_parameters(tok):
                    param = self._resolve_expr(None, self._process_expression(param))
                    if param.kind != 'value':
                        raise AssemblerException(param.token, "DS needs a constant number")
                    if param.token.kind != 'NUMBER':
                        raise AssemblerException(param.token, "DS needs a constant number")
                    if param.token.value < 0:
                        raise AssemblerException(param.token, "DS needs a positive number")
                    self.__section_stack[-1].data += bytes(param.token.value)
            elif start.isA('ID', 'DB'):
                if not self.__section_stack:
                    raise AssemblerException(start, "Expression outside of section")
                for param in self._fetch_parameters(tok):
                    self.__section_stack[-1].add8(self._process_expression(param))
            elif start.isA('ID', 'DW'):
                if not self.__section_stack:
                    raise AssemblerException(start, "Expression outside of section")
                for param in self._fetch_parameters(tok):
                    self.__section_stack[-1].add16(self._process_expression(param))
            elif start.isA('ID') and tok.peek().isA('='):
                tok.pop()
                params = self._fetch_parameters(tok)
                if len(params) != 1:
                    raise AssemblerException(start, "Syntax error")
                expr = self._process_expression(params[0])
                try:
                    expr = self._resolve_expr(None, expr)
                except PostRomBuild:
                    pass
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
                if self.__block_macro_stack:
                    macro, macro_args = self.__block_macro_stack.pop()
                    macro_contents = macro.post_contents
                    if tok.peek().isA('ID') and tok.peek().value in macro.chains:
                        macro = macro.chains[tok.peek().value]
                        macro_contents = macro.contents
                        self.__block_macro_stack.append((macro, macro_args))
                        tok.pop()
                        tok.expect('{')
                    prepend = []
                    for token in macro_contents:
                        if token.kind == 'ID' and token.value in macro_args:
                            prepend += macro_args[token.value]
                        else:
                            prepend.append(token)
                    tok.prepend(prepend)
                elif self.__section_stack:
                    self.__section_stack.pop()
                else:
                    raise AssemblerException(start, f"Unexpected }}")
            else:
                raise AssemblerException(start, f"Syntax error")
        if self.__section_stack:
            raise AssemblerException(tok.pop(), f"EOF reached with section open")

    def link(self, *, print_free_space=False):
        sa = SpaceAllocator(self.__layouts)
        for section in self.__sections:
            if section.base_address > -1:
                sa.allocate_fixed(section.layout.name, section.base_address, len(section.data))
        for section in self.__sections:
            if section.base_address < 0:
                bank, addr = sa.allocate(section.layout.name, len(section.data), bank=section.bank)
                section.bank = bank
                section.base_address = addr
        for section in self.__sections:
            for offset, expr, message in section.asserts:
                try:
                    expr = self._resolve_expr(section.base_address + offset, expr)
                except PostRomBuild:
                    pass
                if expr.kind != 'value' or expr.token.kind != 'NUMBER':
                    raise AssemblerException(expr.token, f"Assertion failure (symbol not found?) {expr}")
                if expr.token.value == 0:
                    raise AssemblerException(expr.token, f"Assertion failure: {message}")
            for offset, (link_size, expr) in section.link.items():
                try:
                    expr = self._resolve_expr(section.base_address + offset, expr)
                except PostRomBuild:
                    self.__post_build_link.append((section, offset, link_size, expr))
                else:
                    if expr.kind != 'value':
                        raise AssemblerException(expr.token, f"Failed to parse linking '{expr}', symbol not found?")
                    if not expr.token.isA('NUMBER'):
                        raise AssemblerException(expr.token, f"Failed to link '{expr}', not a number (symbol not found?)")
                    if link_size == 1:
                        if expr.token.value < -128 or expr.token.value > 255:
                            raise AssemblerException(expr.token, f"Value out of range")
                        section.data[offset] = expr.token.value & 0xFF
                    elif link_size == 2:
                        if expr.token.value < 0 or expr.token.value > 0xFFFF:
                            raise AssemblerException(expr.token, f"Value out of range")
                        section.data[offset] = expr.token.value & 0xFF
                        section.data[offset+1] = expr.token.value >> 8
                    else:
                        raise NotImplementedError()
        if print_free_space:
            sa.dump_free_space()
        return self.__sections

    def build_rom(self):
        max_bank = {}
        for section in self.__sections:
            if section.bank is None:
                continue
            max_bank[section.layout.name] = max(section.bank, max_bank.get(section.layout.name, 0))
        rom_size = 0
        for section in self.__sections:
            if section.layout.rom_location is None:
                continue
            layout_size = section.layout.end_addr - section.layout.start_addr
            if section.layout.banked:
                bank_count = (1 << max_bank[section.layout.name].bit_length()) - section.layout.bank_min
                layout_size *= bank_count
            rom_size = max(section.layout.rom_location + layout_size, rom_size)
        self.__rom = bytearray(rom_size)
        for section in self.__sections:
            if section.layout.rom_location is None:
                continue
            offset = section.layout.rom_location + section.base_address - section.layout.start_addr
            if section.layout.banked:
                offset += (section.layout.end_addr - section.layout.start_addr) * (section.bank - section.layout.bank_min)
            self.__rom[offset:offset+len(section.data)] = section.data
        for section, offset, link_size, expr in self.__post_build_link:
            if section.layout.rom_location is None:
                continue
            offset = section.layout.rom_location + section.base_address - section.layout.start_addr + offset
            if section.layout.banked:
                offset += (section.layout.end_addr - section.layout.start_addr) * (section.bank - section.layout.bank_min)
            expr = self._resolve_expr(section.base_address + offset, expr)
            if expr.kind != 'value':
                raise AssemblerException(expr.token, f"Failed to parse linking {expr}, symbol not found?")
            if link_size == 1:
                if expr.token.value < -128 or expr.token.value > 255:
                    raise AssemblerException(expr.token, f"Value out of range")
                self.__rom[offset] = expr.token.value & 0xFF
            elif link_size == 2:
                if expr.token.value < 0 or expr.token.value > 0xFFFF:
                    raise AssemblerException(expr.token, f"Value out of range")
                self.__rom[offset] = expr.token.value & 0xFF
                self.__rom[offset+1] = expr.token.value >> 8
            else:
                raise NotImplementedError()
        return self.__rom

    def save_symbols(self, filename: str) -> None:
        with open(filename, "wt") as f:
            for label, (section, offset) in self.__labels.items():
                address = section.base_address + offset
                bank = section.bank if section.bank is not None else 0
                f.write(f"{bank:02x}:{address:04x} {label}\n")

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
            elif pkey.value == 'BANKED':
                if len(pvalue) > 2:
                    raise AssemblerException(pkey, "BANKED expects at most 2 arguments")
                if len(pvalue) > 1:
                    layout.bank_max = pvalue[1].token.value
                if len(pvalue) > 0:
                    layout.bank_min = pvalue[0].token.value
                layout.banked = True
            else:
                raise AssemblerException(pkey, "Unknown parameter to #LAYOUT")
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
        for section in self.__sections:
            if section.name == name.token.value:
                raise AssemblerException(name.token, "Duplicate section name")
        section_type, section_type_param = self._bracket_param(params[1])
        address = -1
        if section_type_param:
            address = section_type_param[0].token.value
        if section_type.value not in self.__layouts:
            raise AssemblerException(section_type, "Section type not found")
        layout = self.__layouts[section_type.value]
        if address > -1 and not (layout.start_addr <= address < layout.end_addr):
            raise AssemblerException(section_type, "Address out of range for section")
        section = Section(layout, name.token.value, address)
        for param in params[2:]:
            pkey, pvalue = self._bracket_param(param)
            if pkey.value == 'BANK':
                if len(pvalue) != 1:
                    raise AssemblerException(pkey, "BANK requires an argument")
                if not layout.banked:
                    raise AssemblerException(pkey, "Cannot assign a bank to an unbanked section")
                section.bank = pvalue[0].token.value
                if section.bank < layout.bank_min:
                    raise AssemblerException(pkey, f"Bank number need to be at least {layout.bank_min}")
                if layout.bank_max is not None and section.bank >= layout.bank_max:
                    raise AssemblerException(pkey, f"Bank number needs to be lower then {layout.bank_max}")
            else:
                raise AssemblerException(pkey, "Unknown parameter to #SECTION")
        self.__section_stack.append(section)
        self.__sections.append(section)

    def _process_statement(self, start: Token, tok: Tokenizer):
        params, end_token = self._fetch_parameters(tok, params_end=('NEWLINE', '{'))
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
        if end_token.isA('{'):
            self.__block_macro_stack.append((macro, macro_args))

    def _add_macro(self, tok: Tokenizer) -> None:
        name = tok.expect('ID')
        params = self._fetch_parameters(tok, params_end='{')
        content = self._get_raw_macro_block(name, tok)
        macro = self.__macro_db.add(name.value.upper(), params, content)
        if tok.peek().isA('ID', 'end'):
            tok.pop()
            tok.expect('{')
            content = self._get_raw_macro_block(name, tok)
            macro.post_contents = content
        while tok.peek().isA('ID'):
            chain_name = tok.pop()
            tok.expect('{')
            content = self._get_raw_macro_block(chain_name, tok)
            chain = macro.add_chain(chain_name.value, content)
            if tok.peek().isA('ID', 'end'):
                tok.pop()
                tok.expect('{')
                content = self._get_raw_macro_block(name, tok)
                chain.post_contents = content

    def _get_raw_macro_block(self, name: Token, tok: Tokenizer) -> List[Token]:
        content = []
        bracket = 0
        while token := tok.pop_raw():
            if token.kind == '{':
                bracket += 1
            if token.kind == '}':
                if bracket == 0:
                    break
                else:
                    bracket -= 1
            content.append(token)
        if token is None:
            raise AssemblerException(name, "Unterminated macro definition")
        if not content[-1].isA('NEWLINE'):
            content.append(Token('NEWLINE', '', 0, ''))
        return content

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

    def _fetch_parameters(self, tok: Tokenizer, *, params_end: Union[str, Tuple[str, str]]='NEWLINE') -> List[List[Token]]:
        params = []
        tok_match = tok.match
        if not isinstance(params_end, str):
            tok_match = tok.match_any
        if end_token := tok_match(params_end):
            if not isinstance(params_end, str):
                return params, end_token
            return params
        param = []
        params.append(param)
        brackets = 0
        while brackets != 0 or not (end_token := tok_match(params_end)):
            t = tok.pop()
            if t.kind == 'EOF':
                if params_end != 'NEWLINE':
                    raise AssemblerException(t, "Unexpected end of file")
                break
            if t.kind == 'FUNC':
                func = builtin.get(t.value.upper())
                if not func:
                    fparams = self._fetch_parameters(tok, params_end=')')
                    func = self.__func_db.get(t.value.upper(), fparams)
                    if func is None:
                        raise AssemblerException(t, f"Function not found: {t.value}")
                    func, func_args = func
                    for token in func.contents:
                        if token.kind == 'ID' and token.value in func_args:
                            param += func_args[token.value]
                        else:
                            param.append(token)
                    continue
                brackets += 1
            elif t.kind == '(' or t.kind == '[' or t.kind == '{':
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
        if not isinstance(params_end, str):
            return params, end_token
        return params

    def _bracket_param(self, tokens: List[Token], arg_count: Optional[int] = None):
        if tokens[0].kind != 'ID':
            raise AssemblerException(tokens[0], "Syntax error")
        if len(tokens) < 2:
            if arg_count is None:
                return tokens[0], ()
            raise AssemblerException(tokens[0], "Expected '['")
        if tokens[1].kind != '[':
            raise AssemblerException(tokens[1], "Expected '['")
        if tokens[-1].kind != ']':
            raise AssemblerException(tokens[-1], "Expected ']'")
        t = Tokenizer()
        t.prepend(tokens[2:-1])
        params = self._fetch_parameters(t)
        if arg_count is not None:
            if len(params) != arg_count:
                raise AssemblerException(tokens[0], "Wrong number of parameters")
        params = tuple(self._process_expression(param) for param in params)
        return tokens[0], params

    def _process_expression(self, tokens: List[Token]) -> AstNode:
        for start_idx, start in enumerate(tokens):
            if start.kind == 'FUNC':
                args = []
                arg = []
                brackets = 0
                for end_idx in range(start_idx + 1, len(tokens)):
                    t = tokens[end_idx]
                    if t.isA(')') and brackets == 0:
                        if arg:
                            args.append(arg)
                        func = builtin.get(start.value.upper())
                        if func is None:
                            raise RuntimeError("_fetch_parameters allowed a non-builting through?")
                        contents = func(self, args)
                        if contents is None:
                            return parse_expression(tokens)
                        else:
                            tokens = tokens[:start_idx] + contents + tokens[end_idx + 1:]
                        return self._process_expression(tokens)
                    elif t.isA(',') and brackets == 0:
                        args.append(arg)
                        arg = []
                    else:
                        if t.kind == 'FUNC':
                            brackets += 1
                        elif t.kind == ')':
                            brackets -= 1
                        arg.append(tokens[end_idx])
                raise AssemblerException(start, f"Function not closed: {start.value}")
            if start.kind == 'ID' and start.value in self.__constants:
                tokens[start_idx] = Token('NUMBER', self.__constants[start.value], start.line_nr, start.filename)
        return parse_expression(tokens)

    def _resolve_expr(self, offset: Optional[int], expr: AstNode) -> Optional[AstNode]:
        if expr is None:
            return None
        if expr.kind == 'value' and expr.token.isA('ID'):
            if expr.token.value not in self.__labels:
                return expr
            section, section_offset = self.__labels[expr.token.value]
            if section.base_address < 0:
                return expr
            expr.token = Token('NUMBER', section.base_address + section_offset, expr.token.line_nr, expr.token.filename)
        elif expr.kind == 'value' and expr.token.isA('CURADDR'):
            if offset is None:
                return expr
            expr.token = Token('NUMBER', offset, expr.token.line_nr, expr.token.filename)
        elif expr.kind == 'call':
            if expr.token.value == 'BANK':
                label_token = expr.right.left.token
                if label_token.value not in self.__labels:
                    return expr
                section, section_offset = self.__labels[label_token.value]
                if section.base_address < 0:
                    return expr
                bank = section.bank if section.bank is not None else 0
                return AstNode('value', Token('NUMBER', bank, expr.token.line_nr, expr.token.filename), None, None)
            elif expr.token.value == 'BANK_MAX':
                if self.__rom is None:
                    raise PostRomBuild()
                count = 0
                for section in self.__sections:
                    if section.layout.name == expr.right.left.token.value:
                        count = max(count, section.bank if section.bank is not None else 0)
                return AstNode('value', Token('NUMBER', count, expr.token.line_nr, expr.token.filename), None, None)
            elif expr.token.value == 'CHECKSUM':
                if self.__rom is None:
                    raise PostRomBuild()
                start, end = 0, len(self.__rom)
                if expr.right:
                    if not expr.right.left.is_number():
                        return expr
                    if not expr.right.right.left.is_number():
                        return expr
                    start, end = expr.right.left.token.value, expr.right.right.left.token.value
                return AstNode('value', Token('NUMBER', sum(self.__rom[start:end]), expr.token.line_nr, expr.token.filename), None, None)
            elif expr.token.value == 'BIT_LENGTH':
                expr = self._resolve_expr(offset, expr.right.left)
                if not expr.is_number():
                    raise AssemblerException(expr.token, "BIT_LENGTH parameter is not a number")
                return AstNode('value', Token('NUMBER', expr.token.value.bit_length(), expr.token.line_nr, expr.token.filename), None, None)
            else:
                raise NotImplementedError(str(expr))
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
                elif expr.kind == '*':
                    expr.token = Token('NUMBER', expr.left.token.value * expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
                elif expr.kind == '/':
                    expr.token = Token('NUMBER', expr.left.token.value // expr.right.token.value, expr.left.token.line_nr, expr.left.token.filename)
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


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")

    args = parser.parse_args()
    print(args)

    a = Assembler()
    # import os
    # for f in sorted(os.listdir("../FFL3-Disassembly/src")):
    #     if f.endswith(".asm"):
    #         a.process_file("../FFL3-Disassembly/src/" + f)
    a.process_file(args.filename)
    a.link(print_free_space=True)
    # for section in a.link():
    #     print(section)
    open("rom.gb", "wb").write(a.build_rom())
    a.save_symbols("rom.sym")


if __name__ == "__main__":
    main()