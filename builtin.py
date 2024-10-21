from typing import List, Optional
from tokenizer import Token
from exception import AssemblerException


_buildin_functions = {}


def builtin(f):
    _buildin_functions[f.__name__.upper()] = f
    return f


@builtin
def strlen(assembler, args: List[List[Token]]) -> List[Token]:
    if len(args) != 1:
        raise AssemblerException(args[0][0], "strlen requires 1 argument")
    if len(args[0]) != 1 or args[0][0].kind != "STRING":
        raise AssemblerException(args[0][0], "Expected a string")
    st = args[0][0]
    return [Token("NUMBER", len(st.value), st.line_nr, st.filename)]


@builtin
def bank(assembler, args: List[List[Token]]) -> Optional[List[Token]]:
    if len(args) != 1:
        raise AssemblerException(args[0][0], "bank requires 1 argument")
    if len(args[0]) != 1 or args[0][0].kind != "ID":
        raise AssemblerException(args[0][0], "Expected a label")
    return None


@builtin
def checksum(assembler, args: List[List[Token]]) -> Optional[List[Token]]:
    return None


def get(fname: str):
    return _buildin_functions.get(fname)
