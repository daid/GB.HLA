
class AssemblerException(Exception):
    def __init__(self, token, message):
        self.token = token
        self.message = message

    @staticmethod
    def from_expression(expr, message):
        tokens = []
        def r(e):
            if e:
                tokens.append(e.token)
                r(e.left)
                r(e.right)
        r(expr)
        per_file = {}
        for token in tokens:
            per_file[token.filename] = per_file.get(token.filename, 0) + 1
        per_file = sorted(per_file.items(), key=lambda n: n[1])
        for token in tokens:
            if token.filename == per_file[0][0]:
                return AssemblerException(token, message)
        return AssemblerException(expr.token, message)
