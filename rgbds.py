import struct
from typing import List

from tokenizer import Token
from expression import AstNode


class Node:
    def __init__(self, obj_file):
        self.obj_file = obj_file
        self.parent = None
        self.parent_id = -1
        self.parent_line_nr = 0
        self.type = 0
        self.depth = -1
        self.iter_depth = -1
        self.name = ""


class Symbol:
    def __init__(self, obj_file):
        self.obj_file = obj_file
        self.label = ""
        self.type = -1
        self.node = None
        self.line_no = 0
        self.section_id = -1
        self.value = -1

    def get_label_token(self) -> Token:
        return Token('ID', self.label, self.line_no, self.node.name)


class Section:
    def __init__(self, obj_file):
        self.obj_file = obj_file
        self.name = ""
        self.line_no = -1
        self.size = 0
        self.type = -1
        self.address = -1
        self.bank = -1
        self.alignment = 0
        self.align_offset = 0
        self.node = None
        self.data = None
        self.patches = []

    def get_layout_name(self) -> str:
        match self.type:
            case 0: return "WRAM0"
            case 1: return "VRAM"
            case 2: return "ROMX"
            case 3: return "ROM0"
            case 4: return "HRAM"
            case 5: return "WRAMX"
            case 6: return "SRAM"
            case 7: return "OAM"
        raise NotImplementedError("Section type: {self.type:02x}")

    def get_name_token(self) -> Token:
        return Token('STRING', self.name, self.line_no, self.node.name)


class Patch:
    def __init__(self, obj_file):
        self.obj_file = obj_file
        self.node = None
        self.line_no = -1
        self.offset = -1
        self.pc_section = -1
        self.pc_offset = -1
        self.patch_type = -1
        self.rpn = b''

    def get_link_type(self) -> int:
        match self.patch_type:
            case 0: return 1
            case 1: return 2
            case 3: return 1  # JR patch
        raise NotImplementedError("Patch type: {self.patch_type:02x}")

    def get_ast(self) -> AstNode:
        stack: List[AstNode] = []
        idx = 0
        while idx < len(self.rpn):
            match self.rpn[idx]:
                case 0x00:  # +
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("+", Token("OP", "+", self.line_no, self.node.name), left, right))
                case 0x01:  # -
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("-", Token("OP", "-", self.line_no, self.node.name), left, right))
                case 0x02:  # *
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("*", Token("OP", "*", self.line_no, self.node.name), left, right))
                case 0x03:  # /
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("/", Token("OP", "/", self.line_no, self.node.name), left, right))
                case 0x10:  # |
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("|", Token("OP", "|", self.line_no, self.node.name), left, right))
                case 0x11:  # &
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("&", Token("OP", "&", self.line_no, self.node.name), left, right))
                case 0x12:  # ^
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("^", Token("OP", "^", self.line_no, self.node.name), left, right))
                case 0x12:  # ~
                    left = stack.pop()
                    stack.append(AstNode("~", Token("OP", "~", self.line_no, self.node.name), left, None))
                case 0x30:  # ==
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("==", Token("OP", "==", self.line_no, self.node.name), left, right))
                case 0x31:  # ==
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("!=", Token("OP", "!=", self.line_no, self.node.name), left, right))
                case 0x32:  # <
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode("<", Token("OP", "<", self.line_no, self.node.name), left, right))
                case 0x33:  # >
                    right = stack.pop()
                    left = stack.pop()
                    stack.append(AstNode(">", Token("OP", ">", self.line_no, self.node.name), left, right))
                case 0x50:  # Bank
                    symbol = self.obj_file.symbols[struct.unpack("<I", self.rpn[idx + 1:idx + 5])[0]]
                    symbol_node = AstNode("value", Token("ID", symbol.label, self.line_no, self.node.name), None, None)
                    call_node = AstNode("call", Token("ID", "BANK", self.line_no, self.node.name), None, AstNode('param', symbol_node.token, symbol_node, None))
                    stack.append(call_node)
                    idx += 4
                case 0x70:  # HIGH
                    left = stack.pop()
                    stack.append(AstNode(">>", Token("OP", ">>", self.line_no, self.node.name), left, AstNode("value", Token("NUMBER", 8, self.line_no, self.node.name), None, None)))
                case 0x71:  # LOW
                    left = stack.pop()
                    stack.append(AstNode("&", Token("OP", "&", self.line_no, self.node.name), left, AstNode("value", Token("NUMBER", 0xFF, self.line_no, self.node.name), None, None)))
                case 0x80:  # Value
                    value = struct.unpack("<I", self.rpn[idx+1:idx+5])[0]
                    stack.append(AstNode("value", Token("NUMBER", value, self.line_no, self.node.name), None, None))
                    idx += 4
                case 0x81:  # Symbol
                    symbol = self.obj_file.symbols[struct.unpack("<I", self.rpn[idx+1:idx+5])[0]]
                    if symbol.section_id == -1 and symbol.type != 1:  # just a constant
                        stack.append(AstNode("value", Token("NUMBER", symbol.value, self.line_no, self.node.name), None, None))
                    else:
                        stack.append(AstNode("value", Token("ID", symbol.label, self.line_no, self.node.name), None, None))
                    idx += 4
                case _:
                    raise NotImplementedError(f"RPN: {self.rpn[idx]:02x} {stack}")
            idx += 1
        assert len(stack) == 1
        if self.patch_type == 3:  # jr patch
            stack[0] = AstNode("-", Token("OP", "-", self.line_no, self.node.name), stack[0], AstNode("value", Token("CURADDR", "@", self.line_no, self.node.name), None, None))
            stack[0] = AstNode("-", Token("OP", "-", self.line_no, self.node.name), stack[0], AstNode("value", Token("NUMBER", 1, self.line_no, self.node.name), None, None))
        return stack[0]


class ObjectFile:
    def __init__(self, filename: str):
        f = open(filename, "rb")
        def readstring() -> str:
            res = b''
            while (c := f.read(1)) != b'\x00':
                res += c
            return res.decode()
        assert f.read(4) == b'RGB9'
        revision, symbol_count, section_count, node_count = struct.unpack("<IIII", f.read(16))
        assert revision == 13
        self.nodes = [None] * node_count
        self.symbols = []
        self.sections = []
        for idx in range(node_count):
            node = Node(self)
            node.parent_id, node.parent_line_nr, node.type = struct.unpack("<iIB", f.read(9))
            if (node.type & 0x7F) == 0:
                node.depth, node.iter_depth = struct.unpack("<II", f.read(8))
            else:
                node.name = readstring()
            self.nodes[node_count - 1 - idx] = node
        for node in self.nodes:
            if node.parent_id != -1:
                node.parent = self.nodes[node.parent_id]

        for idx in range(symbol_count):
            symbol = Symbol(self)
            symbol.label = readstring()
            symbol.type = f.read(1)[0]
            if symbol.type != 1:
                node_id, symbol.line_no, symbol.section_id, symbol.value = struct.unpack("<iiii", f.read(16))
                symbol.node = self.nodes[node_id]
            self.symbols.append(symbol)

        for idx in range(section_count):
            section = Section(self)
            section.name = readstring()
            node_id, section.line_no, section.size, section.type, section.address, section.bank, section.alignment, section.align_offset = struct.unpack("<iiiBiiBi", f.read(26))
            assert section.alignment == 0, "Section alignment not supported"
            section.node = self.nodes[node_id]
            if section.type in {2, 3}:
                section.data = f.read(section.size)
                patch_count = struct.unpack("<I", f.read(4))[0]
                for patch_idx in range(patch_count):
                    patch = Patch(self)
                    node_id, patch.line_no, patch.offset, patch.pc_section, patch.pc_offset, patch.patch_type, rpn_size = struct.unpack("<iiiiiBi", f.read(25))
                    assert patch.pc_section == idx, "LOAD blocks not supported"
                    patch.node = self.nodes[node_id]
                    patch.rpn = f.read(rpn_size)
                    section.patches.append(patch)
            self.sections.append(section)

        assert_count = struct.unpack("<I", f.read(4))[0]
        for idx in range(assert_count):
            node_id, line_no, offset, pc_section, pc_offset, assert_type, rpn_size = struct.unpack("<IIIIIBI", f.read(25))
            rpn = f.read(rpn_size)
