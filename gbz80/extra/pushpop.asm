#MACRO pushpop _regpair1 {
    push _regpair1
} end {
    pop  _regpair1
}
#MACRO pushpop _regpair1, _regpair2 {
    push _regpair1
    push _regpair2
} end {
    pop  _regpair2
    pop  _regpair1
}
#MACRO pushpop _regpair1, _regpair2, _regpair3 {
    push _regpair1
    push _regpair2
    push _regpair3
} end {
    pop  _regpair3
    pop  _regpair2
    pop  _regpair1
}
#MACRO pushpop _regpair1, _regpair2, _regpair3, _regpair4 {
    push _regpair1
    push _regpair2
    push _regpair3
    push _regpair4
} end {
    pop  _regpair4
    pop  _regpair3
    pop  _regpair2
    pop  _regpair1
}