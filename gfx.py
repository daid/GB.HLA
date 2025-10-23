import PIL.Image

from exception import AssemblerException
from tokenizer import Token
from typing import List, Dict, Any


def _bool_option(options: Dict[str, List[Any]], key: str) -> bool:
    if key not in options:
        return False
    if len(options.pop(key)) != 0:
        raise AssemblerException(file_token, f"Syntax error in {key}, expected no values after it")
    return True


def read(file_token: Token, options: Dict[str, List[Any]]) -> bytes:
    tileheight = 8
    colormap = None
    unique = _bool_option(options, "UNIQUE")
    return_tilemap = _bool_option(options, "TILEMAP")
    export_range = None
    debug = _bool_option(options, "DEBUG")
    if "TILEHEIGHT" in options:
        if len(options["TILEHEIGHT"]) != 1 or options["TILEHEIGHT"][0].kind != "value":
            raise AssemblerException(file_token, "Syntax error in TILEHEIGHT[n]")
        tileheight = options.pop("TILEHEIGHT")[0].token.value
    if "COLORMAP" in options:
        if len(options["COLORMAP"]) != 4:
            raise AssemblerException(file_token, "Syntax error in COLORMAP[n, n, n, n]")
        colormap = []
        for n in range(4):
            if options["COLORMAP"][n].kind != "value":
                raise AssemblerException(file_token, "Syntax error in COLORMAP[n, n, n, n]")
            colormap.append(options["COLORMAP"][n].token.value)
        options.pop("COLORMAP")
    if "RANGE" in options:
        if len(options["RANGE"]) != 2:
            raise AssemblerException(file_token, "Syntax error in RANGE[start, end]")
        export_range = options["RANGE"][0].token.value, options["RANGE"][1].token.value
        options.pop("RANGE")
    if options:
        raise AssemblerException(file_token, f"Unknown option: {next(iter(options.keys()))}")

    img = PIL.Image.open(file_token.value)
    if img.mode != "P":
        img = img.convert("P", palette=PIL.Image.ADAPTIVE)
    if (img.size[0] % 8) != 0:
        raise AssemblerException(file_token, "Graphics file width not dividable by 8")
    if (img.size[1] % tileheight) != 0:
        raise AssemblerException(file_token, f"Graphics file height not dividable by {tileheight}")

    palette = img.getpalette()
    palette = [(palette[n*3] << 16) | (palette[n*3+1] << 8) | (palette[n*3+2]) for n in range(len(palette) // 3)]
    if colormap:
        remap = []
        for pal in palette:
            dist = [abs((pal & 0xFF) - (col & 0xFF)) + abs(((pal >> 8) & 0xFF) - ((col >> 8) & 0xFF)) + abs(((pal >> 16) & 0xFF) - ((col >> 16) & 0xFF)) for col in colormap]
            remap.append(dist.index(min(dist)))
    else:
        remap = [0 for n in range(len(palette))]
        # Per default order the colors from light to dark
        brightness_index = [((palette[index] >> 16) + ((palette[index] >> 8) & 0xFF) + (palette[index] & 0xFF), index) for count, index in img.getcolors()]
        brightness_index.sort(reverse=True)
        for target, (_, idx) in enumerate(brightness_index):
            remap[idx] = target * 4 // len(brightness_index)

    if debug:
        print(f"Image: {file_token.value}: {img.size[0]}x{img.size[1]} has colors:")
        for count, index in img.getcolors():
            print(f"  ${palette[index]:06X}: mapped: {remap[index]} (x{count})")

    cols = img.size[0] // 8
    rows = img.size[1] // tileheight
    result = bytearray(rows * cols * tileheight * 2)
    index = 0
    for ty in range(rows):
        for tx in range(cols):
            for y in range(tileheight):
                a = 0
                b = 0
                for x in range(8):
                    c = remap[img.getpixel((tx * 8 + x, ty * tileheight + y))]
                    if c & 1:
                        a |= 0x80 >> x
                    if c & 2:
                        b |= 0x80 >> x
                result[index] = a
                result[index+1] = b
                index += 2
    if unique or return_tilemap:
        unique_tiles = b''
        tile_lookup = {}
        tilemap = bytearray()
        for n in range(0, len(result), tileheight * 2):
            tile = bytes(result[n:n+tileheight*2])
            if tile not in tile_lookup:
                nr = len(unique_tiles) // (tileheight*2)
                if nr > 255:
                    raise AssemblerException(file_token, "Too many unique tiles in graphics for tilemap")
                tile_lookup[tile] = nr
                unique_tiles += tile
            tilemap.append(tile_lookup[tile])
        if return_tilemap:
            if export_range:
                return tilemap[export_range[0]:export_range[1]]
            return tilemap
        result = unique_tiles
    if export_range:
        return result[export_range[0]*tileheight*2:export_range[1]*tileheight*2]
    return result
