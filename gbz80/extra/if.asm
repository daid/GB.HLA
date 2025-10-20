
#FMACRO invert_condition c { nc }
#FMACRO invert_condition z { nz }
#FMACRO invert_condition nc { c }
#FMACRO invert_condition nz { z }
_if_enter_counter = 0
#MACRO if _cond {
    _if_enter_counter = _if_enter_counter + 1
    jr invert_condition(_cond), _if_label_ ## _if_enter_counter
    #PUSH _if_stack, _if_enter_counter
} end {
    #POP _if_stack, _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} else {
    #POP _if_stack, _if_current_label_nr
    #PUSH _if_stack, _if_current_label_nr
    jr _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    #POP _if_stack, _if_current_label_nr
    _ifelse_label_ ## _if_current_label_nr:
} else.jp {
    #POP _if_stack, _if_current_label_nr
    #PUSH _if_stack, _if_current_label_nr
    jp _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    #POP _if_stack, _if_current_label_nr
    _ifelse_label_ ## _if_current_label_nr:
}

#MACRO if.jp _cond {
    _if_enter_counter = _if_enter_counter + 1
    jp invert_condition(_cond), _if_label_ ## _if_enter_counter
    #PUSH _if_stack, _if_current_label_nr
} end {
    #POP _if_stack, _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} else {
    #POP _if_stack, _if_current_label_nr
    #PUSH _if_stack, _if_current_label_nr
    jr _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    #POP _if_stack, _if_current_label_nr
    _ifelse_label_ ## _if_current_label_nr:
} else.jp {
    #POP _if_stack, _if_current_label_nr
    #PUSH _if_stack, _if_current_label_nr
    jp _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    #POP _if_stack, _if_current_label_nr
    _ifelse_label_ ## _if_current_label_nr:
}
