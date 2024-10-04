from typing import List, Optional, Dict, Tuple
from collections import defaultdict
from tokenizer import Token



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
                if not a[a_idx].match(token):
                    return False
                a_idx += 1
        return True

    def __repr__(self):
        return f"<Macro:{self.name}:{self.params}>"


class MacroDB:
    def __init__(self):
        self.__macros: Dict[str, Tuple[List[Macro], List[Macro]]] = defaultdict(lambda: ([], []))

    def add(self, name: str, params: List[List[Token]], contents: List[Token]):
        if MacroDB.is_constant_params(params):
            self.__macros[name][0].append(Macro(name, params, contents))
        else:
            self.__macros[name][1].append(Macro(name, params, contents))

    def get(self, name: str, params: List[List[Token]]) -> Optional[Tuple[Macro, Dict[str, List[Token]]]]:
        for macro in self.__macros[name][0]:
            if len(macro.params) != len(params):
                continue
            res = macro.match_params(params)
            if res is not None:
                return macro, res
        for macro in self.__macros[name][1]:
            res = macro.match_params(params)
            if res is not None:
                return macro, res
        return None

    @staticmethod
    def is_constant_params(params: List[List[Token]]):
        for param in params:
            for t in param:
                if t.isA('ID') and t.value.startswith('_'):
                    return False
        return True
