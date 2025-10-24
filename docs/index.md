# Welcome

GB.HLA is a free Game Boy and Game Boy Color assembler.

## Introduction

GB.HLA aims to provide a complete toolchain for Gameboy development. This targets the Game Boy (DMG) and Game Boy Color (GBC). The Game Boy Advance is a completely different device and not covered by this toolchain.

## Why?

The primary toolchain generally recommended for Game Boy assembly is [RGBDS](https://rgbds.gbdev.io/). So why another toolchain?

GB.HLA offers a different approach compared to RGBDS. Key differences are:

* Single pass. RGBDS depends on different tools doing different parts, and combining it all in a linking step. GB.HLA does everything in a single pass. Which does away with complex build systems and intermediate files.
* Extremely powerful macro matching mechanism. This mechanism is powerful enough that ALL assembly instructions are implemented as macros. But the macro system is even more powerful with scoping and linking.
* Slower, as RGBDS is written in C++ and is multiple times faster then GB.HLA. This makes GB.HLA usually 5x slower then RGBDS. In practice this means your build times goes from 1 to 5 seconds.
* Easier to extend. Missing a feature? It is likely that you can easily add it in your own version of GB.HLA with ease.

## Glossary

* DMG: The classic Game Boy with the 4 shades of green screen, released in 1989.
* GBC/CGB: The Game Boy Color is an enhanced version of the DMG, with the addition of color and more features. Released in 1998.
* GBA: Game Boy Advanced, not covered by this toolchain. See [gbadev](https://gbadev.net/) for details on the GBA.
* Pandocs: The [pandocs](https://gbdev.io/pandocs/) are the number 1 reference for details on how the DMG and GBC hardware functions.