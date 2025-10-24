; Macros to create gbz80 loops

; `loop c, 8 {}` create a loop that uses register c and executes the inner code 8 times.
__loop_nr = 0
#MACRO loop _reg, _n {
    __loop_nr = __loop_nr + 1
    #PUSH _loop_stack, __loop_nr
    ld _reg, _n
__loop_label_ ## __loop_nr:
} end {
    dec _reg
    #POP _loop_stack, _loop_current_label_nr
    jr  nz, __loop_label_ ## _loop_current_label_nr
}

; `loop c {}` create a loop that uses register c and executes the inner code c times, unless c is 0 then it loops 256 times
__loop_nr = 0
#MACRO loop _reg {
    __loop_nr = __loop_nr + 1
    #PUSH _loop_stack, __loop_nr
__loop_label_ ## __loop_nr:
} end {
    dec _reg
    #POP _loop_stack, _loop_current_label_nr
    jr  nz, __loop_label_ ## _loop_current_label_nr
}

; `loop {}` create a loop that loops endlessly.
#MACRO loop {
    __loop_nr = __loop_nr + 1
    #PUSH _loop_stack, __loop_nr
__loop_label_ ## __loop_nr:
} end {
    #POP _loop_stack, _loop_current_label_nr
    jr  __loop_label_ ## _loop_current_label_nr
}
