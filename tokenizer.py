import re
from typing import Optional, List
from exception import AssemblerException


class Token:
    __slots__ = 'kind', 'value', 'line_nr', 'filename'

    def __init__(self, kind, value, line_nr, filename):
        self.kind = kind
        self.value = value
        self.line_nr = line_nr
        self.filename = filename

    def isA(self, kind, value=None):
        if self.kind != kind:
            return False
        if value is not None and self.value.upper() != value.upper():
            return False
        return True

    def __repr__(self) -> str:
        return f"<{self.kind}:{self.value}@{self.filename}:{self.line_nr}>"


class Tokenizer:
    TOKEN_REGEX = re.compile('|'.join('(?P<%s>%s)' % pair for pair in [
        ('NUMBER', r'\d+(\.\d*)?'),
        ('HEX', r'\$[0-9A-Fa-f]+'),
        ('GFX', r'`[0-3]+'),
        ('ASSIGN', r':='),
        ('COMMENT', r';[^\n]*'),
        ('LABEL', r':'),
        ('DIRECTIVE', r'#[A-Za-z_]+'),
        ('STRING', '[a-zA-Z]?"[^"]*"'),
        ('ID', r'\.?[A-Za-z_][A-Za-z0-9_\.]*'),
        ('OP', r'(?:<=)|(?:>=)|(?:==)|(?:<<)|(?:>>)|[+\-*/,\(\)<>&|\[\]]'),
        ('TOKENCONCAT', r'##'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]))

    def __init__(self):
        self.__tokens = []

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
            elif kind == 'NEWLINE':
                value = ""
            elif kind == 'OP':
                kind = value
            self.__tokens.append(Token(kind, value, line_nr, filename))
            if kind == 'NEWLINE':
                line_nr += 1

    def prepend(self, tokens: List[Token]):
        self.__tokens = tokens + self.__tokens

    def pop_raw(self) -> Optional[Token]:
        if not self.__tokens:
            return None
        return self.__tokens.pop(0)

    def peek(self) -> Optional[Token]:
        if not self.__tokens:
            return None
        token = self.__tokens[0]
        while len(self.__tokens) > 1 and self.__tokens[1].isA('TOKENCONCAT'):
            self.__tokens.pop(1)
            token = Token(token.kind, str(token.value) + str(self.__tokens.pop(1).value), token.line_nr, token.filename)
        return token

    def pop(self) -> Optional[Token]:
        if not self.__tokens:
            return None
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

    def __bool__(self):
        return len(self.__tokens) > 0
