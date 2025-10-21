from typing import List, Optional, Dict, Tuple, Union
import binascii
import os
from tokenizer import Token, Tokenizer
from expression import AstNode, parse_expression
from exception import AssemblerException
from macrodb import MacroDB, Macro
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
    def __init__(self, layout: Layout, name_token: Token, base_address: Optional[int] = None, bank: Optional[int] = None) -> None:
        self.layout = layout
        self.name = name_token.value
        self.token = name_token
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
        self.__constants: Dict[str, int] = {}
        self.__labels: Dict[str, Tuple[Section, int]] = {}
        self.__sections: List[Section] = []
        self.__current_scope: Optional[str] = None
        self.__include_paths = [os.path.dirname(__file__)]
        self.__layouts: Dict[str, Layout] = {}
        self.__rom: Optional[bytearray] = None
        self.__post_build_link: List[Tuple[Section, int, int, AstNode]] = []
        self.__section_stack: List[Section] = []
        self.__block_macro_stack: List[Tuple[Macro, Dict[str, List[Token]]]] = []
        self.__user_stack: Dict[str, List[int]] = {}
        self.__linking_allocation_done = False

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
        tok = Tokenizer(self.__constants)
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
                if len(params[0]) != 1 or params[0][0].kind != 'STRING':
                    raise AssemblerException(start, "Syntax error")
                if not self.__section_stack:
                    raise AssemblerException(start, "Expression outside of section")
                gfx_params = {}
                for param in params[1:]:
                    pkey, pvalue = self._bracket_param(param)
                    gfx_params[pkey.value] = pvalue
                self.__section_stack[-1].data += gfx.read(params[0][0], gfx_params)
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
            elif start.isA('DIRECTIVE', '#PRINT'):
                for expr in self._fetch_parameters(tok):
                    expr = self._process_expression(expr)
                    expr = self._resolve_expr(None, expr)
                    print(expr, end=' ')
                print()
            elif start.isA('DIRECTIVE', '#IF'):
                allow = True
                for condition in self._fetch_parameters(tok, params_end='{'):
                    condition = self._process_expression(condition)
                    condition = self._resolve_expr(None, condition)
                    if condition.kind != 'value':
                        raise AssemblerException(condition.token, "#IF needs a constant expression")
                    if condition.token.kind != 'NUMBER':
                        raise AssemblerException(condition.token, "#IF needs a constant expression")
                    allow = allow and (condition.token.value != 0)
                if allow:
                    self.__block_macro_stack.append((None, None))  # HACKERDY HACK
                else:
                    self._get_raw_macro_block(start, tok)
            elif start.isA('DIRECTIVE', '#PUSH'):
                params = self._fetch_parameters(tok)
                if len(params) != 2:
                    raise AssemblerException(start, "#PUSH requires 2 parameters: [stack name], [value]")
                stack_name = self._process_expression(params[0])
                value = self._process_expression(params[1])
                if stack_name.kind != "value" or stack_name.token.kind != "ID":
                    raise AssemblerException(start, "First parameter of #PUSH should be a stack name to push to")
                if value.kind != "value" or value.token.kind != "NUMBER":
                    raise AssemblerException(start, "Second parameter of #PUSH should be a value to push")
                if stack_name.token.value not in self.__user_stack:
                    self.__user_stack[stack_name.token.value] = []
                self.__user_stack[stack_name.token.value].append(value.token.value)
            elif start.isA('DIRECTIVE', '#POP'):
                params = self._fetch_parameters(tok)
                if len(params) != 2 or len(params[1]) != 1:
                    raise AssemblerException(start, "#PUSH requires 2 parameters: [stack name], [value]")
                stack_name = self._process_expression(params[0])
                value = params[1][0]
                if stack_name.kind != "value" or stack_name.token.kind != "ID":
                    raise AssemblerException(start, "First parameter of #POP should be a stack name to push to")
                if value.kind != "ID":
                    raise AssemblerException(start, "Second parameter of #POP should be a constant name to pop")
                if stack_name.token.value not in self.__user_stack:
                    raise AssemblerException(start, f"Stack {stack_name.token.value} not found")
                if not self.__user_stack[stack_name.token.value]:
                    raise AssemblerException(start, f"Stack {stack_name.token.value} is empty while trying to pop")
                self.__constants[value.value] = self.__user_stack[stack_name.token.value].pop()
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
                elif not start.value.startswith("__"):
                    self.__current_scope = label
                if label in self.__labels:
                    raise AssemblerException(start, "Duplicate label")
                if not self.__section_stack:
                    raise AssemblerException(start, "Trying to place label outside of section")
                self.__labels[label] = (self.__section_stack[-1], len(self.__section_stack[-1].data))
            elif start.isA('ID'):
                self._process_statement(start, tok)
            elif start.isA('}'):
                if self.__block_macro_stack:
                    macro, macro_args = self.__block_macro_stack.pop()
                    if macro is not None:
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
            raise AssemblerException(start, f"End of file reached with section open")

    def link(self, *, print_free_space=False):
        sa = SpaceAllocator(self.__layouts)
        for section in self.__sections:
            if section.base_address > -1:
                if not sa.allocate_fixed(section.layout.name, section.base_address, len(section.data), bank=section.bank):
                    raise AssemblerException(section.token, f"Failed to allocate fixed region: {section.base_address:04x}-{section.base_address+len(section.data):04x}")
        for section in self.__sections:
            if section.base_address < 0:
                bank_addr = sa.allocate(section.layout.name, len(section.data), bank=section.bank)
                if bank_addr is None:
                    raise AssemblerException(section.token, f"Failed to allocate region of size: {len(section.data):04x}")
                bank, addr = bank_addr
                section.bank = bank
                section.base_address = addr
        self.__linking_allocation_done = True
        for section in self.__sections:
            for offset, expr, message in section.asserts:
                try:
                    expr = self._resolve_expr(section.base_address + offset, expr)
                except PostRomBuild:
                    pass
                if expr.kind != 'value' or expr.token.kind != 'NUMBER':
                    raise AssemblerException.from_expression(expr, f"Assertion failure (symbol not found?) {expr}")
                if expr.token.value == 0:
                    raise AssemblerException.from_expression(expr, f"Assertion failure: {message}")
            for offset, (link_size, expr) in section.link.items():
                try:
                    expr = self._resolve_expr(section.base_address + offset, expr)
                except PostRomBuild:
                    self.__post_build_link.append((section, offset, link_size, expr))
                else:
                    if expr.kind != 'value':
                        raise AssemblerException.from_expression(expr, f"Failed to parse linking '{expr}', symbol not found?")
                    if not expr.token.isA('NUMBER'):
                        raise AssemblerException.from_expression(expr, f"Failed to link '{expr}', symbol not found?")
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

    def dump(self):
        print("\nOutput dump:")
        for section in self.__sections:
            bank = section.bank or 0
            print(f"Section: {section.layout.name}[{bank:02x}]:{section.name}:{section.base_address:04x}")
            offset_to_label = {}
            for label, (label_section, label_offset) in self.__labels.items():
                if section == label_section:
                    offset_to_label[label_offset] = label
            byte_idx = 0
            for offset, c in enumerate(section.data):
                if offset in offset_to_label:
                    if byte_idx > 0:
                        byte_idx = 0
                        print("")
                    print(f"{offset_to_label[offset]}:")
                if byte_idx == 0:
                    print(" ", end="")
                print(f" {c:02X}", end="")
                byte_idx += 1
                if byte_idx == 16:
                    print("")
                    byte_idx = 0
            if byte_idx > 0:
                byte_idx = 0
                print("")
            if len(section.data) in offset_to_label:
                print(f"{offset_to_label[len(section.data)]}:")
    
    def get_label(self, label: str) -> Tuple[Section, int]:
        if label in self.__labels:
            return self.__labels[label]
        return None, None
    
    def get_sections(self, layout_name: str) -> List[Section]:
        return [section for section in self.__sections if section.layout.name == layout_name]
    
    def get_rom(self):
        return self.__rom

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
        section = Section(layout, name.token, address)
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
        if macro.linked:
            prepend.append(macro.linked[0])
            for linked_param in macro.linked[1]:
                for token in linked_param:
                    if token.kind == 'ID' and token.value in macro_args:
                        prepend += macro_args[token.value]
                    else:
                        prepend.append(token)
                if linked_param != macro.linked[1][-1]:
                    prepend.append(Token(",", ",", 0, ""))
            prepend.append(end_token)
        elif end_token.isA('{'):
            self.__block_macro_stack.append((macro, macro_args))
        elif macro.post_contents:
            for token in macro.post_contents:
                if token.kind == 'ID' and token.value in macro_args:
                    prepend += macro_args[token.value]
                else:
                    prepend.append(token)
        tok.prepend(prepend)

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
        if tok.match('>'):
            if macro.post_contents or macro.chains:
                raise AssemblerException(name, "Macros with chains/post actions cannot be linked to other macros")
            linked_macro = tok.expect('ID')
            linked_params = self._fetch_parameters(tok)
            macro.linked = (linked_macro, linked_params)

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

    def _fetch_parameters(self, tok: Tokenizer, *, params_end: Union[str, Tuple[str, str]]='NEWLINE') -> Union[List[List[Token]], Tuple[List[List[Token]], Token]]:
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
                        raise AssemblerException(t, f"Function not found: [{t.value}] with params: {', '.join(tokens_to_string(p) for p in fparams)}")
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
                    t = Token('ID', f"{self.__current_scope}{t.value}", t.line_nr, t.filename)
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
        t = Tokenizer(self.__constants)
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
                        if func.function_type == "macro":
                            contents = func(self, args)
                            tokens = tokens[:start_idx] + contents + tokens[end_idx + 1:]
                        else:
                            return parse_expression(tokens)
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
            func = builtin.get(expr.token.value)
            if func.function_type == "link":
                if not self.__linking_allocation_done:
                    raise PostRomBuild()
                res = func(self, expr.right)
            elif func.function_type == "postbuild":
                if not self.__rom:
                    raise PostRomBuild()
                res = func(self, expr.right)
            elif func.function_type == "function":
                expr = self._resolve_expr(offset, expr.right.left)
                res = func(self, expr)
            else:
                raise RuntimeError(f"Not implemented: {func.function_type}")
            return res
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
    parser.add_argument("input")
    parser.add_argument("--output")
    parser.add_argument("--symbols")
    parser.add_argument("--dump", action="store_true")

    args = parser.parse_args()

    try:
        a = Assembler()
        a.process_file(args.input)
        a.link(print_free_space=True)
    except AssemblerException as e:
        print(f"Error: {e.message}")
        if e.token:
            print(f" at: {e.token.filename}:{e.token.line_nr}")
            if os.path.isfile(e.token.filename):
                lines = open(e.token.filename).readlines()
                print("-----")
                for n in range(max(0, e.token.line_nr - 3), min(len(lines), e.token.line_nr + 2)):
                    print(f"{'>' if n == e.token.line_nr - 1 else ' '}  {lines[n].rstrip()}")
                print("-----")
        exit(1)
    else:
        if args.output:
            open(args.output, "wb").write(a.build_rom())
        if args.symbols:
            a.save_symbols(args.symbols)
        if args.dump:
            a.dump()


if __name__ == "__main__":
    main()