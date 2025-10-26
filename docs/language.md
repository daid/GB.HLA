# Language Reference

Statements in GB.HLA in general are on a line. Comments are defined starting with a semicolon: `;` and can be on their own line or after a statement. Whitespace before or after a statement is ignored.
Example:
```asm
statement ; comment
; comment
    statement
```

## #MACRO

TODO: Macros are complex enough that they require their own page

## #FMACRO

TODO

## #INCLUDE

Reads and fully parses the given file. This allows for splitting your project into multiple files and also to include libraries into your project.

### Example:
```asm
#INCLUDE "gbz80/all.asm" ; include default set of gbz80 ASM instructions
#INCLUDE "mylib/rand.asm" ; include a file from your project
```

## #INCGFX

TODO

## #LAYOUT

TODO

## #SECTION

TODO

## #ASSERT

TODO

## #PRINT

TODO

## #IF

## #FOR

## #PUSH

## #POP

# Other

## ds, db, dw

## assignment

# Labels
