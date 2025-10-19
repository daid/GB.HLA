from typing import Dict, Optional, Tuple
from exception import AssemblerException
from layout import Layout


class SpaceAllocationInfo:
    def __init__(self, layout: Layout):
        self.__layout = layout
        self.__available = []
        if layout.banked:
            self.__available.append((layout.bank_min, layout.start_addr, layout.end_addr))
            self.__next_free_bank = layout.bank_min + 1
        else:
            self.__available.append((None, layout.start_addr, layout.end_addr))
            self.__next_free_bank = None
    
    def free_space(self):
        per_bank = {}
        for bank, start, end in self.__available:
            per_bank[bank] = per_bank.get(bank, 0) + (end - start)
        return per_bank
    
    def total_space(self):
        return self.__layout.end_addr - self.__layout.start_addr

    def allocate_fixed(self, start: int, length: int, *, bank: Optional[int]) -> Optional[int]:
        if bank is not None:
            while bank >= self.__next_free_bank:
                self.__new_bank()
        end = start + length
        for idx, (b, s, e) in enumerate(self.__available):
            if b != bank and bank is not None:
                continue
            if s <= start and e >= end:
                self.__available.pop(idx)
                if s < start:
                    self.__available.append((b, s, start))
                if e > end:
                    self.__available.append((b, end, e))
                return b
        raise AssemblerException(None, f"Failed to allocate fixed region: {start:04x}-{end:04x} in bank {bank}")

    def allocate(self, length: int, bank: Optional[int]=None) -> Tuple[Optional[int], int]:
        if bank is not None:
            while bank >= self.__next_free_bank:
                self.__new_bank()
        for idx, (b, s, e) in enumerate(self.__available):
            if bank is not None and b != bank:
                continue
            if e - s >= length:
                if e - s > length:
                    self.__available[idx] = (b, s + length, e)
                else:
                    self.__available.pop(idx)
                return b, s
        if bank is not None or not self.__layout.banked:
            raise AssemblerException(None, f"Failed to allocate region: {length:04x}")
        self.__new_bank()
        return self.allocate(length, bank)

    def __new_bank(self):
        if self.__layout.bank_max is not None and self.__next_free_bank == self.__layout.bank_max:
            raise AssemblerException(None, f"Ran out of available banks for {self.__layout.name}")
        self.__available.append((self.__next_free_bank, self.__layout.start_addr, self.__layout.end_addr))
        self.__next_free_bank += 1


class SpaceAllocator:
    def __init__(self, layouts: Dict[str, Layout]):
        self.__data = {name: SpaceAllocationInfo(layout) for name, layout in layouts.items()}

    def dump_free_space(self) -> None:
        print("\nFree space:")
        for name, sai in self.__data.items():
            spaces = sai.free_space()
            for bank, free in sorted(spaces.items()):
                bank = f" {bank:02x}" if bank is not None else ""
                if free < sai.total_space():
                    print(f"  {name:5}{bank:5} {free:5}/{sai.total_space():<5} ({free/sai.total_space()*100:.1f}%)")

    def allocate_fixed(self, section_type: str, start: int, length: int, *, bank: Optional[int]=None) -> int:
        return self.__data[section_type].allocate_fixed(start, length, bank=bank)

    def allocate(self, section_type: str, length: int, bank=None) -> Tuple[Optional[int], int]:
        return self.__data[section_type].allocate(length, bank=bank)
