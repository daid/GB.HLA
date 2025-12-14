import os
import binascii
import re
from typing import Optional

from tokenizer import Token
from expression import AstNode


class Patch:
    def __init__(self, area, offset, target, target_offset, size, shift=0):
        self.area = area
        self.offset = offset
        self.target = target
        self.target_offset = target_offset
        self.size = size
        self.shift = shift

    def get_link_type(self):
        return self.size
    
    def get_ast(self) -> AstNode:
        token_filename, line_no = self.area.get_filename_line_for(self.offset)
        if isinstance(self.target, Area):
            node = AstNode("value", Token("ID", f"__area_start_{self.target.name}", line_no, token_filename), None, None)
        elif self.target.name.startswith("b_"):
            node = AstNode("value", Token("ID", self.target.name[1:], line_no, token_filename), None, None)
            node = AstNode("call", Token("ID", "BANK", 1, token_filename), None, AstNode('param', node.token, node, None))
        elif self.target.name.startswith("___bank_"):
            node = AstNode("value", Token("ID", self.target.name[8:], line_no, token_filename), None, None)
            node = AstNode("call", Token("ID", "BANK", 1, token_filename), None, AstNode('param', node.token, node, None))
        else:
            node = AstNode("value", Token("ID", self.target.name, line_no, token_filename), None, None)
        if self.target_offset:
            node = AstNode("+", Token("OP", "+", line_no, token_filename), node, AstNode("value", Token("NUMBER", self.target_offset, line_no, token_filename), None, None))
        if self.shift:
            node = AstNode(">>", Token("OP", ">>", line_no, token_filename), node, AstNode("value", Token("NUMBER", self.shift, line_no, token_filename), None, None))
        if self.size == 1:
            node = AstNode("&", Token("OP", "&", line_no, token_filename), node, AstNode("value", Token("NUMBER", 0xFF, line_no, token_filename), None, None))
        return node

class Area:
    def __init__(self, object_file, type_name: str, name: str, size: int, flags: int, address: int):
        self.object_file = object_file
        self.type_name = type_name
        self.name = name
        self.size = size
        self.flags = flags
        self.address = address if (flags & 0x08) else -1
        self.symbols = []
        self.data = bytearray(size)
        self.patches = []
    
    def get_filename_line_for(self, offset: int):
        previous_sym = None
        for sym in self.symbols:
            if sym.offset <= offset and (previous_sym is None or previous_sym.offset < sym.offset):
                previous_sym = sym
        if not previous_sym:
            return f"{self.object_file.module_name}.c#?", 0
        filename, line_no = self.object_file.get_filename_line_for(previous_sym.name, offset)
        if filename is None:
            return f"{self.object_file.module_name}.c#{previous_sym.name}", offset - previous_sym.offset
        return filename, line_no

    def add_data(self, new_offset, new_data, patches):
        patches.sort()
        index = 0
        patch_index, patch_mode, patch_target = patches.pop(0) if patches else (len(new_data), 0, None)
        while index < len(new_data):
            if index < patch_index:
                self.data[new_offset] = new_data[index]
                new_offset += 1
                index += 1
            else:
                match patch_mode:
                    case 0x00 | 0x02:
                        patch_offset = new_data[index] | (new_data[index + 1] << 8)
                        self.patches.append(Patch(self, new_offset, patch_target, patch_offset, 2))
                        new_offset += 2
                        index += 2
                    case 0x09 | 0x0B:
                        patch_offset = new_data[index] | (new_data[index + 1] << 8) | (new_data[index + 2] << 16) | (new_data[index + 3] << 24)
                        self.patches.append(Patch(self, new_offset, patch_target, patch_offset, 1))
                        new_offset += 1
                        index += 4
                    case 0x89 | 0x8B:
                        patch_offset = new_data[index] | (new_data[index + 1] << 8) | (new_data[index + 2] << 16) | (new_data[index + 3] << 24)
                        self.patches.append(Patch(self, new_offset, patch_target, patch_offset, 1, 8))
                        new_offset += 1
                        index += 4
                    case _:
                        print(patch_index, patch_mode, patch_target, index, binascii.hexlify(new_data[index:]), patches)
                        raise NotImplementedError(f"SDCC patch mode: {patch_mode:02x} not implemented (start praying)")
                patch_index, patch_mode, patch_target = patches.pop(0) if patches else (len(new_data), 0, None)
    
    def get_layout_name(self) -> str:
        if self.type_name == "_CODE":
            return "ROM0"
        if self.type_name.startswith("_CODE_"):
            return "ROMX"
        if self.type_name == "_DATA":
            return "WRAM0"
        raise NotImplementedError(f"Area type: {self.type_name}")
    
    def get_bank(self) -> int:
        if self.type_name.startswith("_CODE_"):
            return int(self.type_name[6:])
        raise NotImplementedError(f"Area type: {self.type_name}")

    def get_name_token(self) -> Token:
        return Token('STRING', self.name, 1, self.name)

    def __repr__(self):
        return f"<Area: {self.name}>"


class Symbol:
    def __init__(self, area: Optional[Area], name: str, offset: int, is_label: bool):
        self.name = name
        self.offset = offset
        self.is_label = is_label
        self.area = area
    
    def __repr__(self):
        return f"<Symbol: {self.name}>"


class ObjectFile:
    def __init__(self, filename: str):
        self.module_name = None
        self.__symbols = []
        self.areas = []
        self.__file_lookup = {}

        list_filename = f"{os.path.splitext(filename)[0]}.lst"
        if os.path.exists(list_filename):
            latest_symbol_info = None
            current_file = None
            current_line = None
            f = open(list_filename, "rt")
            for line in f:
                offset = line[4:12].strip()
                if offset != "" and current_file is not None:
                    offset = int(offset, 16)
                    latest_symbol_info.append((offset, current_file, int(current_line)))
                    current_file = None
                    current_line = None
                data = line[40:].rstrip()
                if data.endswith("::"):
                    latest_symbol_info = []
                    self.__file_lookup[data[:-2]] = latest_symbol_info
                elif m := re.match(r";([a-z0-9\.]+):([0-9]+)", data):
                    current_file, current_line = m.groups()

        f = open(filename, "rt")
        header = f.readline().strip()
        assert header.startswith("XL"), "Header line is wrong. Wrong sdcc version used?"
        asize = int(header[2:])
        assert asize == 4, "asize is wrong, wrong sdcc version used?"
        new_offset = None
        new_data = None
        for line in f:
            line = line.strip().split()
            match line[0]:
                case "H":  # Header [areas] areas [symbols] global symbols
                    pass
                case "O":  # Options
                    assert "-msm83" in line, "No sm83 in rel options, wrong sdcc version used?"
                case "M":  # module name
                    assert len(line) == 2
                    self.module_name = line[1]
                case "S":  # Symbol name [Ref|Def]xxxx
                    assert len(line) == 3
                    if line[2].startswith("Def"):
                        if self.areas:
                            symbol = Symbol(self.areas[-1], line[1], int(line[2][3:], 16), True)
                            self.areas[-1].symbols.append(symbol)
                        else:
                            symbol = Symbol(None, line[1], int(line[2][3:], 16), True)
                    else:
                        symbol = Symbol(None, line[1], int(line[2][3:], 16), False)
                    self.__symbols.append(symbol)
                case "A":  # Area [name] size [size] flags [flags] addr [addr]
                    assert len(line) == 8
                    assert line[2] == "size"
                    assert line[4] == "flags"
                    assert line[6] == "addr"
                    self.areas.append(Area(self, line[1], self.module_name + line[1], int(line[3], 16), int(line[5], 16), int(line[7], 16)))
                case "T":  # Data
                    assert len(line) >= 5
                    data = bytes(int(s, 16) for s in line[1:])
                    new_offset = data[0] | data[1] << 8 | data[2] << 16 | data[3] << 24
                    new_data = data[4:]
                case "R":  # Relocation
                    assert len(line) >= 5
                    data = bytes(int(s, 16) for s in line[1:])
                    assert data[0] == 0 and data[1] == 0
                    area_index = data[2] | data[3] << 8
                    data = data[4:]
                    patches = []
                    while data:
                        mode = data[0]
                        if (mode & 0xF0) == 0xF0:
                            mode = ((mode << 8) & 0xF00) | data[1]
                            data = data[1:]
                        offset = data[1]
                        ref = data[2] | (data[3] << 8)
                        target = self.__symbols[ref] if (mode & 0x02) else self.areas[ref]
                        patches.append((offset - 4, mode, target))
                        data = data[4:]
                    assert new_data is not None
                    if new_data:
                        self.areas[area_index].add_data(new_offset, new_data, patches)
                    else:
                        assert not patches
                    new_offset = None
                    new_data = None
                case _:
                    print(f"Unknown line in sdcc object: {' '.join(line)}")

    def get_filename_line_for(self, symbol: str, offset: int):
        if symbol not in self.__file_lookup:
            return None, None
        prev_file, prev_line = None, None
        for o, file, line in self.__file_lookup[symbol]:
            if o > offset:
                return prev_file, prev_line
            prev_file, prev_line = file, line
        return prev_file, prev_line
