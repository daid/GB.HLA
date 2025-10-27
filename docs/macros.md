# Macros

TODO: This is a more complex subject then you would expect

```asm
#MACRO macro_name fix_param _variable_param {
    db _variable_param
} end {
    db "After scope"
}
#MACRO macro_name fix_param specific_overload {
    db "overload"
}

macro_name 1 2 ; error, the 1 does not match fix_param
macro_name fix_param 2 ; outputs $02, "After scope"
macro_name fix_param specific_overload ; outputs "overload"
macro_name fix_param 10 {   ; outputs $0A, $04, "After scope"
    db $04
}
```