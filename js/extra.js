console.log("Registering ASM");
hljs.registerLanguage("asm", () => {
    return {
        case_insensitive: true, // language is case-insensitive
        keywords: 'adc add and bit call ccf cp cpl daa dec di ei halt inc jp jr ld ldh nop or pop push res ret reti lr rla rlc rlca rr rra rrc rrca rst sbc scf set sla sra srl stop sub swap xor',
        contains: [
            hljs.QUOTE_STRING_MODE,
            hljs.COMMENT(';', '$'),
            {
                scope: 'number',
                begin: '[0-9][0-9_]+',
                relevance: 0
            },
            {
                scope: 'number',
                begin: '\\$[0-9a-fA-F][0-9a-fA-F_]+',
                relevance: 0
            },
            {
                scope: 'variable',
                begin: '\\w+:',
                relevance: 0
            },
            {
                scope: 'built_in',
                begin: '#\\w+',
                relevance: 0
            }
        ]
    }
});
