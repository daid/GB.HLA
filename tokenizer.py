import re
from typing import Optional, List, Dict, Any
from exception import AssemblerException
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    value: Any
    line_nr: int
    filename: str

    def isA(self, kind: str, value=None) -> bool:
        if self.kind != kind:
            return False
        if value is not None and self.value.upper() != value.upper():
            return False
        return True

    def match(self, other: "Token") -> bool:
        if self.kind != other.kind:
            return False
        if self.kind == 'ID':
            if self.value.upper() != other.value.upper():
                return False
        else:
            if self.value != other.value:
                return False
        return True

    def __repr__(self) -> str:
        return f"<{self.kind}:{self.value}@{self.filename}:{self.line_nr}>"


class Tokenizer:
    TOKEN_REGEX = re.compile('|'.join('(?P<%s>%s)' % pair for pair in [
        ('NUMBER', r'\d+(\.\d*)?'),
        ('HEX', r'\$[0-9A-Fa-f]+'),
        ('BIN', r'%[0-1]+'),
        ('GFX', r'`[0-3]+'),
        ('COMMENT', r';[^\n]*'),
        ('LABEL', r':'),
        ('DIRECTIVE', r'#[A-Za-z_]+'),
        ('STRING', '"[^"]*"'),
        ('FUNC', r'\.?[A-Za-z_][A-Za-z0-9_\.]*\('),
        ('ID', r'\.?[A-Za-z_][A-Za-z0-9_\.]*'),
        ('CURADDR', r'@'),
        ('OP', r'(?:<=)|(?:>=)|(?:==)|(?:!=)|(?:<<)|(?:>>)|[+\-*/,\(\)<>&|\[\]{}=]'),
        ('TOKENCONCAT', r'##'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]))

    def __init__(self, constants: Optional[Dict[str, int]] = None):
        self.__tokens = []
        self.__eof = Token('EOF', '', 0, '')
        self.__constants = constants if constants is not None else {}

    def add_code(self, code, *, filename="[string]") -> None:
        line_nr = 1
        for m in self.TOKEN_REGEX.finditer(code):
            kind = m.lastgroup
            value = m.group()
            if kind == 'SKIP' or kind == 'COMMENT':
                continue
            if kind == 'NUMBER':
                value = int(value)
            elif kind == 'HEX':
                value = int(str(value)[1:], 16)
                kind = 'NUMBER'
            elif kind == 'BIN':
                value = int(str(value)[1:], 2)
                kind = 'NUMBER'
            elif kind == 'GFX':
                value = int(str(value)[1:], 4)
                kind = 'NUMBER'
            elif kind == 'FUNC':
                value = value[:-1]
            elif kind == 'NEWLINE':
                value = ""
            elif kind == 'OP':
                kind = value
            elif kind == 'STRING':
                value = value[1:-1]
            elif kind == 'MISMATCH':
                raise AssemblerException(Token(kind, value, line_nr, filename), "Syntax error")
            self.__tokens.append(Token(kind, value, line_nr, filename))
            if kind == 'NEWLINE':
                line_nr += 1
        self.__eof = Token('EOF', '', line_nr, filename)

    def prepend(self, tokens: List[Token]):
        self.__tokens = tokens + self.__tokens

    def pop_raw(self) -> Token:
        if not self.__tokens:
            return self.__eof
        return self.__tokens.pop(0)

    def peek(self) -> Token:
        if not self.__tokens:
            return self.__eof
        token = self.__tokens[0]
        while len(self.__tokens) > 1 and self.__tokens[1].isA('TOKENCONCAT'):
            self.__tokens.pop(1)
            left_side = str(token.value)
            left_side = str(self.__constants.get(left_side, left_side))
            right_side = str(self.__tokens.pop(1).value)
            right_side = str(self.__constants.get(right_side, right_side))
            token = Token(token.kind, left_side + right_side, token.line_nr, token.filename)
            self.__tokens[0] = token
        return token

    def pop(self) -> Token:
        if not self.__tokens:
            return self.__eof
        token = self.peek()
        self.__tokens.pop(0)
        return token

    def expect(self, kind):
        token = self.pop()
        if not token.isA(kind):
            raise AssemblerException(token, f"Expected {kind} got {token.kind}")
        return token

    def match(self, kind) -> Optional[Token]:
        if self.peek().isA(kind):
            return self.pop()
        return None

    def match_any(self, kinds) -> Optional[Token]:
        for kind in kinds:
            if self.peek().isA(kind):
                return self.pop()
        return None

    def __bool__(self):
        return len(self.__tokens) > 0
