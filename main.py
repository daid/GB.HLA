from tokenizer import Token, Tokenizer
from expression import AstNode, parse_expression
from typing import List, Optional, Dict, Tuple


class Macro:
    def __init__(self, name: str, params: List[List[Token]], contents: List[Token]):
        self.name = name
        self.params = params
        self.contents = contents

    def match_params(self, params: List[List[Token]]) -> Optional[Dict[str, List[Token]]]:
        if len(params) != len(self.params):
            return None
        res = {}
        for n in range(len(params)):
            if not Macro.match_node_list(params[n], self.params[n], res):
                return None
        return res

    @staticmethod
    def match_node_list(a: List[Token], b: List[Token], res: Dict[str, List[Token]]) -> bool:
        a_idx = 0
        for b_idx, token in enumerate(b):
            if token.kind == 'ID' and token.value.startswith("_"):
                to_add = (len(a) - a_idx) - (len(b) - b_idx) + 1
                if to_add < 1:
                    return False
                replacement = a[a_idx:a_idx+to_add]
                a_idx += to_add
                res[token.value] = replacement
            else:
                if a_idx >= len(a):
                    return False
                if a[a_idx].kind != token.kind:
                    return False
                if a[a_idx].value != token.value:
                    return False
                a_idx += 1
        return True

    def __repr__(self):
        return f"<Macro:{self.name}:{self.params}>"


class MacroDB:
    def __init__(self):
        self.__macros: List[Macro] = []

    def add(self, name: str, params: List[List[Token]], contents: List[Token]):
        self.__macros.append(Macro(name, params, contents))

    def get(self, name: str, params: List[List[Token]]) -> Optional[Tuple[Macro, Dict[str, List[Token]]]]:
        for macro in self.__macros:
            if macro.name != name:
                continue
            res = macro.match_params(params)
            if res is not None:
                return macro, res
        return None


class Assembler:
    def __init__(self):
        self.__macro_db = MacroDB()

    def process_code(self, code, *, filename="[string]"):
        tok = Tokenizer()
        tok.add_code(code, filename=filename)
        while start := tok.pop():
            if start.isA('NEWLINE'):
                continue
            if start.isA('DIRECTIVE', '#MACRO'):
                self._add_macro(tok)
            elif start.isA('ID', 'DB'):
                print("OUT", self._fetch_parameters(tok))
            elif start.isA('ID'):
                self._process_statement(start, tok)
            else:
                raise AssertionError(start, f"Syntax error")

    def _process_statement(self, start: Token, tok: Tokenizer):
        params = self._fetch_parameters(tok)
        macro = self.__macro_db.get(start.value, params)
        if not macro:
            raise AssertionError(start, f"Syntax error: {start}:{params}")
        macro, macro_args = macro
        prepend = []
        for token in macro.contents:
            if token.kind == 'ID' and token.value in macro_args:
                prepend += macro_args[token.value]
            else:
                prepend.append(token)
        print(prepend)
        tok.prepend(prepend)

    def _add_macro(self, tok: Tokenizer) -> None:
        name = tok.expect('ID').value
        params = self._fetch_parameters(tok)
        content = []
        while token := tok.pop_raw():
            if token.isA('DIRECTIVE', '#END'):
                break
            content.append(token)
        self.__macro_db.add(name, params, content)

    def _fetch_parameters(self, tok: Tokenizer) -> List[List[Token]]:
        params = []
        if tok.match('NEWLINE'):
            return params
        param = []
        params.append(param)
        while not tok.match('NEWLINE'):
            t = tok.pop()
            if t.isA(','):
                param = []
                params.append(param)
            else:
                param.append(t)
        return params

    def _read_expression(self, tok: Tokenizer) -> AstNode:
        return parse_expression(tok)


Assembler().process_code("""
#MACRO ld a, a
    db $7F
#END
#MACRO ld a, [hl]
    db $7E
#END
#MACRO ld a, _value
    db $3E, _value
#END
    ld a, a
    ld a, [hl]
    ld a, (1 + 2) * 3
""")
