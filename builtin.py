from typing import List, Optional
from tokenizer import Token
from exception import AssemblerException
from expression import AstNode


_buildin_functions = {}


def builtin(function_type="macro"):
    def wrapper(f):
        f.function_type = function_type
        _buildin_functions[f.__name__.upper()] = f
        return f
    return wrapper


def get(fname: str):
    return _buildin_functions.get(fname)


@builtin()
def strlen(assembler, args: List[List[Token]]) -> List[Token]:
    if len(args) != 1:
        raise AssemblerException(args[0][0], "strlen requires 1 argument")
    if len(args[0]) != 1 or args[0][0].kind != "STRING":
        raise AssemblerException(args[0][0], "Expected a string")
    st = args[0][0]
    return [Token("NUMBER", len(st.value), st.line_nr, st.filename)]


@builtin(function_type="function")
def bit_length(assembler, param: AstNode) -> AstNode:
    if not param.is_number():
        raise AssemblerException(param.token, "BIT_LENGTH parameter is not a number")
    return AstNode('value', Token('NUMBER', param.token.value.bit_length(), param.token.line_nr, param.token.filename), None, None)


@builtin(function_type="link")
def bank(assembler, param: AstNode) -> AstNode:
    if param.right:
        raise AssemblerException(param.token, "bank requires 1 argument")
    label_token = param.left.token
    if label_token.kind == "CURADDR":
        section = assembler.linking_section
    elif label_token.kind != "ID":
        raise AssemblerException(param.token, "Expected a label to BANK()")
    else:
        section, _ = assembler.get_label(label_token.value)
    if not section:
        raise AssemblerException(param.token, f"Could not find label {label_token.value} for BANK()")
    if section.base_address < 0:
        raise AssemblerException(param.token, f"Could not find label {label_token.value} for BANK()")
    bank = section.bank if section.bank is not None else 0
    return AstNode('value', Token('NUMBER', bank, label_token.line_nr, label_token.filename), None, None)


@builtin()
def defined(assembler, args: List[List[Token]]) -> List[Token]:
    if len(args) != 1:
        raise AssemblerException(args[0][0], "strlen requires 1 argument")
    if len(args[0]) != 1 or args[0][0].kind != "ID":
        raise AssemblerException(args[0][0], "Expected an identifier")
    st = args[0][0]
    constant = assembler.get_constant(st.value)
    return [Token("NUMBER", 0 if constant is None else 1, st.line_nr, st.filename)]


@builtin(function_type="link")
def bank_max(assembler, param: AstNode) -> AstNode:
    if param.right:
        raise AssemblerException(param.token, "bank_max requires 1 argument")
    label_token = param.left.token
    if label_token.kind != "ID":
        raise AssemblerException(param.token, "Expected a layout type to BANK_MAX()")

    count = 0
    for section in assembler.get_sections(label_token.value):
        count = max(count, section.bank if section.bank is not None else 0)
    return AstNode('value', Token('NUMBER', count, label_token.line_nr, label_token.filename), None, None)


@builtin(function_type="postbuild")
def checksum(assembler, param: AstNode) -> AstNode:
    start, end = 0, len(assembler.get_rom())
    if param:
        if not param.left.is_number():
            raise AssemblerException(param.token, "Expected a number to checksum")
        if not param.right.left.is_number():
            raise AssemblerException(param.token, "Expected a number to checksum")
        start, end = param.left.token.value, param.right.left.token.value
    return AstNode('value', Token('NUMBER', sum(assembler.get_rom()[start:end]), 0, ""), None, None)

