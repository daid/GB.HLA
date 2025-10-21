import PIL.Image

from exception import AssemblerException
from tokenizer import Token
from typing import List, Dict, Any


def read(file_token: Token, options: Dict[str, List[Any]]) -> bytes:
    tileheight = 8
    colormap = None
    if "tileheight" in options:
        if len(options["tileheight"]) != 1 or options["tileheight"][0].kind != "value":
            raise AssemblerException(file_token, "Syntax error in tileheight[n]")
        tileheight = options.pop("tileheight")[0].token.value
    if "colormap" in options:
        if len(options["colormap"]) != 4:
            raise AssemblerException(file_token, "Syntax error in colormap[n, n, n, n]")
        colormap = []
        for n in range(4):
            if options["colormap"][n].kind != "value":
                raise AssemblerException(file_token, "Syntax error in colormap[n, n, n, n]")
            colormap.append(options["colormap"][n].token.value)
        options.pop("colormap")
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
        # Per default order the colors from light to dark
        remap = [n * 4 // len(palette) for n in range(len(palette))]
        remap.sort(key=lambda n: (palette[n] >> 16) + ((palette[n] >> 8) & 0xFF) + (palette[n] & 0xFF), reverse=True)

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
    return result
