import struct
import os

from tokenizer import Token
from expression import AstNode


class _ElfSection:
    def __init__(self, f):
        self._name, self._type, self._flags, self._addr, self._offset, self._size, self._link, self._info, self._addralign, self._entsize = struct.unpack("<IIIIIIIIII", f.read(0x28))
        self.symbols = []
        self.reloc = []
    
    def init(self, f):
        f.seek(self._offset, os.SEEK_SET)
        self.data = f.read(self._size)

    def get_string(self, offset):
        end_offset = self.data.find(b'\x00', offset)
        return self.data[offset:end_offset].decode('ascii')

class Patch:
    def __init__(self, offset, target, target_offset, info):
        self.offset = offset
        self.target = target
        self.target_offset = target_offset
        self.info = info

    def get_link_type(self):
        match self.info:
            case 4:  # R_Z80_ADDR16_LO
                return 1
            case 16: # R_Z80_IMM16
                return 2
        raise RuntimeError(f"Unknown clang link info: {self.info}")
    
    def get_ast(self) -> AstNode:
        token_filename, line_no = "", -1
        if self.target.startswith("b_"):
            node = AstNode("value", Token("ID", self.target[1:], line_no, token_filename), None, None)
            node = AstNode("call", Token("ID", "BANK", 1, token_filename), None, AstNode('param', node.token, node, None))
        elif self.target.startswith("___bank_"):
            node = AstNode("value", Token("ID", self.target[8:], line_no, token_filename), None, None)
            node = AstNode("call", Token("ID", "BANK", 1, token_filename), None, AstNode('param', node.token, node, None))
        else:
            node = AstNode("value", Token("ID", self.target, line_no, token_filename), None, None)
        if self.target_offset:
            node = AstNode("+", Token("OP", "+", line_no, token_filename), node, AstNode("value", Token("NUMBER", self.target_offset, line_no, token_filename), None, None))
        if self.info == 4:
            node = AstNode("&", Token("OP", "&", line_no, token_filename), node, AstNode("value", Token("NUMBER", 0xFF, line_no, token_filename), None, None))
        return node


class ObjectFile:
    def __init__(self, filename):
        f = open(filename, "rb")
        elf_magic, elf_class, elf_data, elf_version, elf_osabi, elf_abiversion = struct.unpack("<IBBBBB", f.read(9))
        assert elf_magic == 0x464c457f, "ELF magic mismatch"
        assert elf_class == 1, "ELF class header mismatch"
        assert elf_data == 1, "ELF data header mismatch"
        assert elf_version == 1, "ELF version header mismatch"
        assert elf_osabi == 0, "ELF OSABI header mismatch"
        assert elf_abiversion == 0, "ELF OSABI version header mismatch"
        f.read(7) # padding
        elf_type, elf_machine = struct.unpack("<HH", f.read(4))
        assert elf_type == 1, "ELF object file not a relocatable file"
        assert elf_machine == 8080, "ELF machine not 8080, not targeting sm83?"

        elf_version, elf_entry, elf_phoff, elf_shoff, elf_flags = struct.unpack("<IIIII", f.read(20))
        assert elf_version == 1
        elf_ehsize, elf_phentsize, elf_phnum, elf_shentsize, elf_shnum, elf_shstrndx = struct.unpack("<HHHHHH", f.read(12))
        assert elf_ehsize == 52
        f.seek(elf_shoff, os.SEEK_SET)
        
        sections = [_ElfSection(f) for n in range(elf_shnum)]
        self.section_by_name = {}
        for section in sections:
            section.init(f)
        self.stringtable = sections[elf_shstrndx]
        symbol_table = []
        for section in sections:
            section.name = self.stringtable.get_string(section._name)
            self.section_by_name[section.name] = section
        
        for off in range(0, len(self.section_by_name[".symtab"].data), 16):
            name, value, size, info, other, shndx = struct.unpack("<IIIBBH", self.section_by_name[".symtab"].data[off:off+16])
            name = self.stringtable.get_string(name)
            symbol_table.append(name)
            if 0 < shndx < 0xFFF0:
                sections[shndx].symbols.append((name, value))
                # print(f"{sections[shndx].name=} {name=} {value=} {size=} {info=} {other=} {shndx=:x}")
        
        for section in sections:
            if section._type == 4:  # rel table
                target = self.section_by_name[section.name[section.name.find('.', 1):]]
                for off in range(0, len(section.data), 12):
                    offset, info, addend = struct.unpack("<IIi", section.data[off:off+12])
                    sym = info >> 8
                    info &= 0xFF # https://github.com/llvm-z80/llvm-z80/blob/main/llvm/include/llvm/BinaryFormat/ELFRelocs/Z80.def#L12
                    target.reloc.append(Patch(offset, symbol_table[sym], addend, info))
                    print(f"{section.name=} {offset=} {info=} {symbol_table[sym]=} {addend=}")



if __name__ == "__main__":
    import sys
    for file in [ObjectFile(f) for f in sys.argv[1:]]:
        print(file.section_by_name[".text"].symbols)
        print(file.section_by_name[".text"].reloc)
