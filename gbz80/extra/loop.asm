; Macros to create gbz80 loops

; `loop c, 8 {}` create a loop that uses register c and executes the inner code 8 times.
__loop_nr = 0
#MACRO loop _reg, _n {
    __loop_nr = __loop_nr + 1
    ld _reg, _n
__loop_label_ ## __loop_nr:
} end {
    dec _reg
    jr  nz, __loop_label_ ## __loop_nr
}

; `loop c {}` create a loop that uses register c and executes the inner code c times, unless c is 0 then it loops 256 times
__loop_nr = 0
#MACRO loop _reg {
    __loop_nr = __loop_nr + 1
__loop_label_ ## __loop_nr:
} end {
    dec _reg
    jr  nz, __loop_label_ ## __loop_nr
}

; `loop {}` create a loop that loops endlessly.
#MACRO loop {
    __loop_nr = __loop_nr + 1
__loop_label_ ## __loop_nr:
} end {
    jr  __loop_label_ ## __loop_nr
}
