import PIL.Image
from typing import Optional, List


def read(filename: str, *, tileheight: Optional[int]=None, colormap: List[int]=None) -> bytes:
    if isinstance(filename, str):
        img = PIL.Image.open(filename)
    else:
        img = filename
    if img.mode != "P":
        img = img.convert("P", palette=PIL.Image.ADAPTIVE, colors=4)
    remap = [0, 1, 2, 3]
    if colormap:
        pal3 = img.getpalette()[0:12]
        pal = [(pal3[n*3] << 16) | (pal3[n*3+1] << 8) | (pal3[n*3+2]) for n in range(4)]
        for m in range(4):
            for n in range(4):
                if pal[n] == colormap[m]:
                    remap[n] = m
                    break
    assert (img.size[0] % 8) == 0
    if tileheight is None:
        tileheight = 8 if img.size[1] == 8 else 16
    assert (img.size[1] % tileheight) == 0

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
                    c = remap[img.getpixel((tx * 8 + x, ty * tileheight + y)) & 3]
                    if c & 1:
                        a |= 0x80 >> x
                    if c & 2:
                        b |= 0x80 >> x
                result[index] = a
                result[index+1] = b
                index += 2
    return result