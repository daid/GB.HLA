import json


opcodes = json.load(open("opcodes.json", "rt"))
macros = []
for prefix, code, data in list((None, k, v) for k, v in opcodes['unprefixed'].items()) + list((0xCB, k, v) for k, v in opcodes["cbprefixed"].items()):
    if prefix:
        code = [f"db ${prefix:02x}, ${int(code, 0):02x}"]
    else:
        code = [f"db ${int(code, 0):02x}"]
    if 'ILLEGAL' in data['mnemonic']:
        continue
    args = []
    for arg in data['operands']:
        label = arg['name']
        if label == 'a16':
            label = "_target"
            code.append("dw _target")
        elif label == 'n8':
            label = "_value"
            code[0] += ", _value"
        elif label == 'e8':
            label = "_offset"
        elif label == 'a8':
            label = "_target"
        if not arg['immediate']:
            label = f"[{label}]"
        args.append(label.lower())
    macro = f"{data['mnemonic'].lower()}"
    if args:
        macro = f"{macro} {', '.join(args)}"
    macros.append((macro, code))
macros.sort()
for macro, code in macros:
    code = '\n    '.join(code)
    print(f"#MACRO {macro} {{ {code} }}")
