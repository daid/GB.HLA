

class Layout:
    def __init__(self, name: str, start_addr: int, end_addr: int):
        self.name = name
        self.start_addr = start_addr
        self.end_addr = end_addr
        self.rom_location = None
        self.banked = False
