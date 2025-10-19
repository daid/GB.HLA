
#FMACRO invert_condition c { nc }
#FMACRO invert_condition z { nz }
#FMACRO invert_condition nc { c }
#FMACRO invert_condition nz { z }
_if_enter_counter = 0
_if_exit_counter = 0
#MACRO if _cond {
    _if_enter_counter = _if_enter_counter + 1
    #PRINT "if", _if_enter_counter
    jr invert_condition(_cond), _if_label_ ## _if_enter_counter
} end {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    _if_exit_counter = _if_exit_counter + 1
    _if_label_ ## _if_current_label_nr:
} else {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    jr _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    _if_exit_counter = _if_exit_counter + 1
    _ifelse_label_ ## _if_current_label_nr:
} else.jp {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    jp _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    _if_exit_counter = _if_exit_counter + 1
    _ifelse_label_ ## _if_current_label_nr:
}

#MACRO if.jp _cond {
    _if_enter_counter = _if_enter_counter + 1
    #PRINT "if", _if_enter_counter
    jp invert_condition(_cond), _if_label_ ## _if_enter_counter
} end {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    _if_exit_counter = _if_exit_counter + 1
    _if_label_ ## _if_current_label_nr:
} else {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    jr _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    _if_exit_counter = _if_exit_counter + 1
    _ifelse_label_ ## _if_current_label_nr:
} else.jp {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    jp _ifelse_label_ ## _if_current_label_nr
    _if_label_ ## _if_current_label_nr:
} end {
    _if_current_label_nr = _if_enter_counter - _if_exit_counter
    _if_exit_counter = _if_exit_counter + 1
    _ifelse_label_ ## _if_current_label_nr:
}
