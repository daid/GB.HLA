from tokenizer import Token, Tokenizer
from exception import AssemblerException
from typing import Tuple, Dict, Callable, List, Optional


g_anonymous_label_count = 0

PREC_NONE = 0
PREC_ASSIGNMENT = 1  # =
PREC_LOGIC_OR = 2  # or
PREC_LOGIC_AND = 3  # and
PREC_BITWISE_OR = 4  # |
PREC_BITWISE_XOR = 5  # ^
PREC_BITWISE_AND = 6  # &
PREC_EQUALITY = 7  # == !=
PREC_COMPARISON = 8  # < > <= >=
PREC_SHIFT = 9  # << >>
PREC_TERM = 10  # + -
PREC_FACTOR = 11  # * /
PREC_UNARY = 12  # ! -
PREC_CALL = 13  # . () []
PREC_PRIMARY = 14


class AstNode:
    def __init__(self, kind: str, token: Token, left: Optional["AstNode"], right: Optional["AstNode"]):
        self.kind = kind
        self.token = token
        self.left = left
        self.right = right
    
    def is_number(self):
        if self.kind != 'value':
            return False
        if self.token.kind != 'NUMBER':
            return False
        return True

    def is_string(self):
        if self.kind != 'value':
            return False
        if self.token.kind != 'STRING':
            return False
        return True

    def __repr__(self):
        if self.kind == 'call':
            if self.right:
                return f"{self.token.value}({self.right})"
            return f"{self.token.value}()"
        if self.kind == 'param':
            if self.right:
                return f"{self.left}, {self.right}"
            return f"{self.left}"
        if self.kind == 'value':
            return f"{self.token.value}"
        if self.right:
            return f"({self.left} {self.kind} {self.right})"
        return f"({self.kind} {self.left})"


def parse_value(tok: Tokenizer) -> AstNode:
    t = tok.pop()
    return AstNode("value", t, None, None)


def parse_anonymous_label(tok: Tokenizer) -> AstNode:
    t = tok.pop()
    offset = 0
    for c in t.value[1:]:
        if c == '+':
            offset += 1
        elif c == '-':
            offset -= 1
    if t.value[1] == '-':
        offset += 1
    return AstNode("value", Token('ID', f"__anonymous_{g_anonymous_label_count + offset}", t.line_nr, t.filename), None, None)


def parse_grouping(tok: Tokenizer) -> AstNode:
    tok.pop()
    res = parse_precedence(tok, PREC_ASSIGNMENT)
    tok.expect(')')
    return res


def parse_call(tok: Tokenizer) -> AstNode:
    func = AstNode('call', tok.pop(), None, None)
    if tok.match(')'):
        return func
    args = [parse_precedence(tok, PREC_ASSIGNMENT)]
    while tok.match(','):
        args.append(parse_precedence(tok, PREC_ASSIGNMENT))
    tok.expect(')')
    node = func
    for arg in args:
        node.right = AstNode('param', arg.token, arg, None)
        node = node.right
    return func


def parse_ref(tok: Tokenizer) -> AstNode:
    t = tok.pop()
    res = parse_precedence(tok, PREC_ASSIGNMENT)
    tok.expect(']')
    return AstNode('REF', t, res, None)


def parse_unary(tok: Tokenizer) -> AstNode:
    t = tok.pop()
    return AstNode(t.kind, t, parse_precedence(tok, PREC_UNARY), None)


def parse_binary(tok: Tokenizer) -> Tuple[str, AstNode]:
    t = tok.pop()
    rule = EXPRESSION_RULES[t.kind]
    res = parse_precedence(tok, rule[2] + 1)
    return t.kind, res


EXPRESSION_RULES: Dict[str, Tuple[Callable[[Tokenizer], AstNode], Callable[[Tokenizer], Tuple[str, AstNode]], int]] = {
    'ID': (parse_value, None, PREC_NONE),
    'ALABEL': (parse_anonymous_label, None, PREC_NONE),
    'STRING': (parse_value, None, PREC_NONE),
    'CURADDR': (parse_value, None, PREC_NONE),
    '#': (parse_unary, None, PREC_NONE),
    '&': (None, parse_binary, PREC_BITWISE_AND),
    '^': (None, parse_binary, PREC_BITWISE_XOR),
    '|': (None, parse_binary, PREC_BITWISE_OR),
    '+': (parse_unary, parse_binary, PREC_TERM),
    '~': (parse_unary, None, PREC_TERM),
    '!': (parse_unary, None, PREC_TERM),
    '-': (parse_unary, parse_binary, PREC_TERM),
    '/': (None, parse_binary, PREC_FACTOR),
    '*': (None, parse_binary, PREC_FACTOR),
    '%': (None, parse_binary, PREC_FACTOR),
    '>>': (None, parse_binary, PREC_SHIFT),
    '<<': (None, parse_binary, PREC_SHIFT),
    '==': (None, parse_binary, PREC_EQUALITY),
    '!=': (None, parse_binary, PREC_EQUALITY),
    '<': (None, parse_binary, PREC_COMPARISON),
    '>': (None, parse_binary, PREC_COMPARISON),
    '<=': (None, parse_binary, PREC_COMPARISON),
    '>=': (None, parse_binary, PREC_COMPARISON),
    '&&': (None, parse_binary, PREC_LOGIC_AND),
    '||': (None, parse_binary, PREC_LOGIC_OR),
    'NUMBER': (parse_value, None, PREC_NONE),
    'FUNC': (parse_call, None, PREC_CALL),
    '(': (parse_grouping, None, PREC_CALL),
    '[': (parse_ref, None, PREC_CALL),
}


def parse_precedence(tok: Tokenizer, precedence: int) -> AstNode:
    token = tok.peek()
    if token.kind not in EXPRESSION_RULES:
        raise AssemblerException(token, f"Unexpected {token.value}")
    prefix_rule = EXPRESSION_RULES[token.kind][0]
    if prefix_rule is None:
        raise AssemblerException(token, "Expect expression.")
    a = prefix_rule(tok)

    while tok.peek().kind in EXPRESSION_RULES and precedence <= EXPRESSION_RULES[tok.peek().kind][2]:
        t = tok.peek()
        infix_rule = EXPRESSION_RULES[t.kind][1]
        assert infix_rule is not None
        b, c = infix_rule(tok)
        a = AstNode(b, t, a, c)
    return a


def parse_expression(tokens: List[Token], anonymous_label_count) -> AstNode:
    global g_anonymous_label_count
    g_anonymous_label_count = anonymous_label_count
    tok = Tokenizer()
    tok.prepend(tokens)
    result = parse_precedence(tok, PREC_ASSIGNMENT)
    if not tok.match('EOF'):
        raise AssemblerException(tok.pop(), "Syntax error")
    return result
