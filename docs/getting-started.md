# Getting Started

## Installation

To install GB.HLA you will need the following parts:

* Python3: Install from [Python website](https://www.python.org/)
* GB.HLA: Download and extract from [Github zip](https://github.com/daid/GB.HLA/archive/refs/heads/main.zip)
* An Emulator with debugging support: [BGB](https://bgb.bircd.org/) or [Emulicious](https://emulicious.net/) are recommended.
* A plain text editor: [Visual Studio Code](https://code.visualstudio.com/) 
    * GB.HLA contains a `gb-hla-language` directory. Copying this to `C:\Users\[username]\.vscode\extensions` will enable basic syntax highlighting for `.asm` files

(TODO: This install guide needs work)

## Your first ROM

> NOTE: This is not a tutorial on how to create a Game Boy game. It only explains how to get a basic setup working with GB.HLA.

Create a project directory and in there create a new file named `main.asm`. In this file put the following contents:

```asm
; Comments start with a semicolon.
#INCLUDE "gbz80/all.asm"    ; include all Game Boy instructions and registers.

; Setup the ROM header. This line can be anywhere but needs to be present for a valid ROM.
; This defines the name, the MBC to use and where the code starts.
; Use GBC_HEADER for a rom with GBC support.
GB_HEADER "FirstRom", GB_MCB_ROM_ONLY, entry

; The entry code, this code is ran at the start of the rom.
#SECTION "Entry", ROM0 {
entry:
    ld sp, $E000    ; Change the stack pointer, the boot ROM leaves it in HRAM, but HRAM is too valuable for that.
loop:
    halt            ; Do nothing.
    jr loop
}
```

To build the rom run the command `python3 [path-to-GB.HLA]/main.py main.asm --output rom.gb --symbols rom.sym` this will create your rom and the respective `.sym` file for debugging. It will also output how much space is free in the rom.

You can now load this rom in any Emulator and run it. Nothing will happen, but there will also be no error. And if you enter the debugger, you will see the `entry` label.

## Core concepts

Unlike other assemblers, GB.HLA makes extensive use of scoping with `{}` characters, and allows indenting of everything. This allows you to build a more C like structure of your code. It allows nesting of sections and macros. This might sound confusing now, but it's extremely powerful to build a better structure of your code.

Example:
```asm
#SECTION "Main code", ROM0 {
    call clearGraphics
    #SECTION "Graphics", ROMX {
        graphicsData:
            #INCGFX "graphics.png"
    }
    ld   hl, graphicsData ; This code directly follows the call to clearGraphics
    ld   a,  BANK(graphicsData)
    call loadGraphics
    loop {  ; endless loop from "gbz80/extra/loop.asm"
        ldh  a, [hInputButtons]
        and  a
        if   nz { ; if macro "gbz80/extra/if.asm"
            call handleInput
        } else {
            call handleIdle
        }
    }
}
```