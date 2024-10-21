from typing import List, Optional, Dict, Tuple
from collections import defaultdict
from tokenizer import Token



class Macro:
    def __init__(self, name: str, params: List[List[Token]], contents: List[Token]):
        self.name = name
        self.params = params
        self.contents = contents

        sort_key = []
        for param_idx, param in enumerate(params):
            for t_idx, t in enumerate(param):
                if t.isA('ID') and t.value.startswith('_'):
                    sort_key.append(-param_idx * 100 - t_idx)
        self.__sort_key = tuple(sort_key)

    def is_constant_params(self):
        for param in self.params:
            for t in param:
                if t.isA('ID') and t.value.startswith('_'):
                    return False
        return True

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

    @staticmethod
    def sort_key(self):
        return self.__sort_key


class MacroDB:
    def __init__(self):
        self.__macros: Dict[str, Tuple[List[Macro], List[Macro]]] = defaultdict(lambda: ([], []))

    def add(self, name: str, params: List[List[Token]], contents: List[Token]):
        macro = Macro(name, params, contents)
        if macro.is_constant_params():
            self.__macros[name][0].append(macro)
        else:
            self.__macros[name][1].append(macro)
            self.__macros[name][1].sort(key=Macro.sort_key)

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
