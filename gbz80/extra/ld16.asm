; 16 bit load helpers.

; Store a 16 bit value to memory
#MACRO ld16 [_target], _reg {
    ld a, LOW(_reg)
    ld [_target], a
    ld a, HIGH(_reg)
    ld [_target+1], a
}

; Load a 16 bit value from memory
#MACRO ld16 _reg, [_target] {
    ld a, [_target]
    ld LOW(_reg), a
    ld a, [_target+1]
    ld HIGH(_reg), a
}

; Copy a 16 bit register into a other: ld16 hl, de
#MACRO ld16 _target, _source {
    ld LOW(_target), LOW(_source)
    ld HIGH(_target), HIGH(_source)
}