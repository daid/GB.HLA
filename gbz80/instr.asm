#FMACRO HIGH bc { b }
#FMACRO HIGH de { d }
#FMACRO HIGH hl { h }
#FMACRO HIGH _value { (((_value) >> 8) & $FF) }
#FMACRO LOW bc { c }
#FMACRO LOW de { e }
#FMACRO LOW hl { l }
#FMACRO LOW _value { ((_value) & $FF) }
#FMACRO JR_OFFSET _target { _target - @ }
#MACRO adc _value { adc a, _value }
#MACRO adc a, [hl] { db $8e }
#MACRO adc a, _value { db $ce, _value }
#MACRO adc a, a { db $8f }
#MACRO adc a, b { db $88 }
#MACRO adc a, c { db $89 }
#MACRO adc a, d { db $8a }
#MACRO adc a, e { db $8b }
#MACRO adc a, h { db $8c }
#MACRO adc a, l { db $8d }
#MACRO add _value { add a, _value }
#MACRO add a, [hl] { db $86 }
#MACRO add a, _value { db $c6, _value }
#MACRO add a, a { db $87 }
#MACRO add a, b { db $80 }
#MACRO add a, c { db $81 }
#MACRO add a, d { db $82 }
#MACRO add a, e { db $83 }
#MACRO add a, h { db $84 }
#MACRO add a, l { db $85 }
#MACRO add hl, bc { db $09 }
#MACRO add hl, de { db $19 }
#MACRO add hl, hl { db $29 }
#MACRO add hl, sp { db $39 }
#MACRO add sp, _offset { db $e8, _offset }
#MACRO and _value { and a, _value }
#MACRO and a, [hl] { db $a6 }
#MACRO and a, _value { db $e6, _value }
#MACRO and a, a { db $a7 }
#MACRO and a, b { db $a0 }
#MACRO and a, c { db $a1 }
#MACRO and a, d { db $a2 }
#MACRO and a, e { db $a3 }
#MACRO and a, h { db $a4 }
#MACRO and a, l { db $a5 }
#MACRO bit _id, [hl] { db $cb, $46 | ((_idx) << 3) }
#MACRO bit _idx, a { db $cb, $47 | ((_idx) << 3) }
#MACRO bit _idx, b { db $cb, $40 | ((_idx) << 3) }
#MACRO bit _idx, c { db $cb, $41 | ((_idx) << 3) }
#MACRO bit _idx, d { db $cb, $42 | ((_idx) << 3) }
#MACRO bit _idx, e { db $cb, $43 | ((_idx) << 3) }
#MACRO bit _idx, h { db $cb, $44 | ((_idx) << 3) }
#MACRO bit _idx, l { db $cb, $45 | ((_idx) << 3) }
#MACRO call _target { db $cd
    dw _target }
#MACRO call c, _target { db $dc
    dw _target }
#MACRO call nc, _target { db $d4
    dw _target }
#MACRO call nz, _target { db $c4
    dw _target }
#MACRO call z, _target { db $cc
    dw _target }
#MACRO ccf { db $3f }
#MACRO cp a, [hl] { db $be }
#MACRO cp _value { cp a, _value }
#MACRO cp a, _value { db $fe, _value }
#MACRO cp a, a { db $bf }
#MACRO cp a, b { db $b8 }
#MACRO cp a, c { db $b9 }
#MACRO cp a, d { db $ba }
#MACRO cp a, e { db $bb }
#MACRO cp a, h { db $bc }
#MACRO cp a, l { db $bd }
#MACRO cpl { db $2f }
#MACRO daa { db $27 }
#MACRO dec [hl] { db $35 }
#MACRO dec a { db $3d }
#MACRO dec b { db $05 }
#MACRO dec bc { db $0b }
#MACRO dec c { db $0d }
#MACRO dec d { db $15 }
#MACRO dec de { db $1b }
#MACRO dec e { db $1d }
#MACRO dec h { db $25 }
#MACRO dec hl { db $2b }
#MACRO dec l { db $2d }
#MACRO dec sp { db $3b }
#MACRO di { db $f3 }
#MACRO ei { db $fb }
#MACRO halt { db $76 }
#MACRO inc [hl] { db $34 }
#MACRO inc a { db $3c }
#MACRO inc b { db $04 }
#MACRO inc bc { db $03 }
#MACRO inc c { db $0c }
#MACRO inc d { db $14 }
#MACRO inc de { db $13 }
#MACRO inc e { db $1c }
#MACRO inc h { db $24 }
#MACRO inc hl { db $23 }
#MACRO inc l { db $2c }
#MACRO inc sp { db $33 }
#MACRO jp _target { db $c3
    dw _target }
#MACRO jp c, _target { db $da
    dw _target }
#MACRO jp hl { db $e9 }
#MACRO jp nc, _target { db $d2
    dw _target }
#MACRO jp nz, _target { db $c2
    dw _target }
#MACRO jp z, _target { db $ca
    dw _target }
#MACRO _jr_offset_byte _target {
    #ASSERT ((_target) - @ - 1) < 128, ((_target) - @ - 1) >= -128, "JR offset out of range"
    db (_target) - @ - 1 }
#MACRO jr _target { db $18
    _jr_offset_byte _target }
#MACRO jr c, _target { db $38
    _jr_offset_byte _target }
#MACRO jr nc, _target { db $30
    _jr_offset_byte _target }
#MACRO jr nz, _target { db $20
    _jr_offset_byte _target }
#MACRO jr z, _target { db $28
    _jr_offset_byte _target }
#MACRO ld [_target], a { db $ea
    dw _target }
#MACRO ld [_target], sp { db $08
    dw _target }
#MACRO ld [bc], a { db $02 }
#MACRO ldh [c], a { db $e2 }
#MACRO ldh [$FF00+c], a { db $e2 }
#MACRO ld [de], a { db $12 }
#MACRO ld [hl], _value { db $36, _value }
#MACRO ld [hl+], a { db $22 }
#MACRO ld [hl-], a { db $32 }
#MACRO ld [hl], a { db $77 }
#MACRO ld [hl], b { db $70 }
#MACRO ld [hl], c { db $71 }
#MACRO ld [hl], d { db $72 }
#MACRO ld [hl], e { db $73 }
#MACRO ld [hl], h { db $74 }
#MACRO ld [hl], l { db $75 }
#MACRO ld a, [_target] { db $fa
    dw _target }
#MACRO ld a, [bc] { db $0a }
#MACRO ldh a, [c] { db $f2 }
#MACRO ldh a, [$FF00+c] { db $f2 }
#MACRO ld a, [de] { db $1a }
#MACRO ld a, [hl+] { db $2a }
#MACRO ld a, [hl-] { db $3a }
#MACRO ld a, [hl] { db $7e }
#MACRO ld a, _value { db $3e, _value }
#MACRO ld a, a { db $7f }
#MACRO ld a, b { db $78 }
#MACRO ld a, c { db $79 }
#MACRO ld a, d { db $7a }
#MACRO ld a, e { db $7b }
#MACRO ld a, h { db $7c }
#MACRO ld a, l { db $7d }
#MACRO ld b, [hl] { db $46 }
#MACRO ld b, _value { db $06, _value }
#MACRO ld b, a { db $47 }
#MACRO ld b, b { db $40 }
#MACRO ld b, c { db $41 }
#MACRO ld b, d { db $42 }
#MACRO ld b, e { db $43 }
#MACRO ld b, h { db $44 }
#MACRO ld b, l { db $45 }
#MACRO ld bc, _value { db $01
    dw _value }
#MACRO ld c, [hl] { db $4e }
#MACRO ld c, _value { db $0e, _value }
#MACRO ld c, a { db $4f }
#MACRO ld c, b { db $48 }
#MACRO ld c, c { db $49 }
#MACRO ld c, d { db $4a }
#MACRO ld c, e { db $4b }
#MACRO ld c, h { db $4c }
#MACRO ld c, l { db $4d }
#MACRO ld d, [hl] { db $56 }
#MACRO ld d, _value { db $16, _value }
#MACRO ld d, a { db $57 }
#MACRO ld d, b { db $50 }
#MACRO ld d, c { db $51 }
#MACRO ld d, d { db $52 }
#MACRO ld d, e { db $53 }
#MACRO ld d, h { db $54 }
#MACRO ld d, l { db $55 }
#MACRO ld de, _value { db $11
    dw _value }
#MACRO ld e, [hl] { db $5e }
#MACRO ld e, _value { db $1e, _value }
#MACRO ld e, a { db $5f }
#MACRO ld e, b { db $58 }
#MACRO ld e, c { db $59 }
#MACRO ld e, d { db $5a }
#MACRO ld e, e { db $5b }
#MACRO ld e, h { db $5c }
#MACRO ld e, l { db $5d }
#MACRO ld h, [hl] { db $66 }
#MACRO ld h, _value { db $26, _value }
#MACRO ld h, a { db $67 }
#MACRO ld h, b { db $60 }
#MACRO ld h, c { db $61 }
#MACRO ld h, d { db $62 }
#MACRO ld h, e { db $63 }
#MACRO ld h, h { db $64 }
#MACRO ld h, l { db $65 }
#MACRO ld hl, sp + _offset { db $f8, _offset }
#MACRO ld hl, _value { db $21
    dw _value }
#MACRO ld l, [hl] { db $6e }
#MACRO ld l, _value { db $2e, _value }
#MACRO ld l, a { db $6f }
#MACRO ld l, b { db $68 }
#MACRO ld l, c { db $69 }
#MACRO ld l, d { db $6a }
#MACRO ld l, e { db $6b }
#MACRO ld l, h { db $6c }
#MACRO ld l, l { db $6d }
#MACRO ld sp, hl { db $f9 }
#MACRO ld sp, _value { db $31 
    dw _value }
#MACRO ldh [_target], a { db $e0
    #ASSERT HIGH(_target) == $ff
    db LOW(_target) }
#MACRO ldh a, [_target] { db $f0
    #ASSERT HIGH(_target) == $ff
    db LOW(_target) }
#MACRO nop { db $00 }
#MACRO or _value { or a, _value }
#MACRO or a, [hl] { db $b6 }
#MACRO or a, _value { db $f6, _value }
#MACRO or a, a { db $b7 }
#MACRO or a, b { db $b0 }
#MACRO or a, c { db $b1 }
#MACRO or a, d { db $b2 }
#MACRO or a, e { db $b3 }
#MACRO or a, h { db $b4 }
#MACRO or a, l { db $b5 }
#MACRO pop af { db $f1 }
#MACRO pop bc { db $c1 }
#MACRO pop de { db $d1 }
#MACRO pop hl { db $e1 }
#MACRO push af { db $f5 }
#MACRO push bc { db $c5 }
#MACRO push de { db $d5 }
#MACRO push hl { db $e5 }
#MACRO res _idx, [hl] { db $cb, $86 | ((_idx) << 3) }
#MACRO res _idx, a { db $cb, $87 | ((_idx) << 3) }
#MACRO res _idx, b { db $cb, $80 | ((_idx) << 3) }
#MACRO res _idx, c { db $cb, $81 | ((_idx) << 3) }
#MACRO res _idx, d { db $cb, $82 | ((_idx) << 3) }
#MACRO res _idx, e { db $cb, $83 | ((_idx) << 3) }
#MACRO res _idx, h { db $cb, $84 | ((_idx) << 3) }
#MACRO res _idx, l { db $cb, $85 | ((_idx) << 3) }
#MACRO ret { db $c9 }
#MACRO ret c { db $d8 }
#MACRO ret nc { db $d0 }
#MACRO ret nz { db $c0 }
#MACRO ret z { db $c8 }
#MACRO reti { db $d9 }
#MACRO rl [hl] { db $cb, $16 }
#MACRO rl a { db $cb, $17 }
#MACRO rl b { db $cb, $10 }
#MACRO rl c { db $cb, $11 }
#MACRO rl d { db $cb, $12 }
#MACRO rl e { db $cb, $13 }
#MACRO rl h { db $cb, $14 }
#MACRO rl l { db $cb, $15 }
#MACRO rla { db $17 }
#MACRO rlc [hl] { db $cb, $06 }
#MACRO rlc a { db $cb, $07 }
#MACRO rlc b { db $cb, $00 }
#MACRO rlc c { db $cb, $01 }
#MACRO rlc d { db $cb, $02 }
#MACRO rlc e { db $cb, $03 }
#MACRO rlc h { db $cb, $04 }
#MACRO rlc l { db $cb, $05 }
#MACRO rlca { db $07 }
#MACRO rr [hl] { db $cb, $1e }
#MACRO rr a { db $cb, $1f }
#MACRO rr b { db $cb, $18 }
#MACRO rr c { db $cb, $19 }
#MACRO rr d { db $cb, $1a }
#MACRO rr e { db $cb, $1b }
#MACRO rr h { db $cb, $1c }
#MACRO rr l { db $cb, $1d }
#MACRO rra { db $1f }
#MACRO rrc [hl] { db $cb, $0e }
#MACRO rrc a { db $cb, $0f }
#MACRO rrc b { db $cb, $08 }
#MACRO rrc c { db $cb, $09 }
#MACRO rrc d { db $cb, $0a }
#MACRO rrc e { db $cb, $0b }
#MACRO rrc h { db $cb, $0c }
#MACRO rrc l { db $cb, $0d }
#MACRO rrca { db $0f }
#MACRO rst _value {
    #ASSERT (_value & $07) == 0, _value < $40, "RST target invalid"
    db $c7 + _value }
#MACRO sbc _value { sbc a, _value }
#MACRO sbc a, [hl] { db $9e }
#MACRO sbc a, _value { db $de, _value }
#MACRO sbc a, a { db $9f }
#MACRO sbc a, b { db $98 }
#MACRO sbc a, c { db $99 }
#MACRO sbc a, d { db $9a }
#MACRO sbc a, e { db $9b }
#MACRO sbc a, h { db $9c }
#MACRO sbc a, l { db $9d }
#MACRO scf { db $37 }
#MACRO set _idx, [hl] { db $cb, $c6 | ((_idx) << 3) }
#MACRO set _idx, a { db $cb, $c7 | ((_idx) << 3) }
#MACRO set _idx, b { db $cb, $c0 | ((_idx) << 3) }
#MACRO set _idx, c { db $cb, $c1 | ((_idx) << 3) }
#MACRO set _idx, d { db $cb, $c2 | ((_idx) << 3) }
#MACRO set _idx, e { db $cb, $c3 | ((_idx) << 3) }
#MACRO set _idx, h { db $cb, $c4 | ((_idx) << 3) }
#MACRO set _idx, l { db $cb, $c5 | ((_idx) << 3) }
#MACRO sla [hl] { db $cb, $26 }
#MACRO sla a { db $cb, $27 }
#MACRO sla b { db $cb, $20 }
#MACRO sla c { db $cb, $21 }
#MACRO sla d { db $cb, $22 }
#MACRO sla e { db $cb, $23 }
#MACRO sla h { db $cb, $24 }
#MACRO sla l { db $cb, $25 }
#MACRO sra [hl] { db $cb, $2e }
#MACRO sra a { db $cb, $2f }
#MACRO sra b { db $cb, $28 }
#MACRO sra c { db $cb, $29 }
#MACRO sra d { db $cb, $2a }
#MACRO sra e { db $cb, $2b }
#MACRO sra h { db $cb, $2c }
#MACRO sra l { db $cb, $2d }
#MACRO srl [hl] { db $cb, $3e }
#MACRO srl a { db $cb, $3f }
#MACRO srl b { db $cb, $38 }
#MACRO srl c { db $cb, $39 }
#MACRO srl d { db $cb, $3a }
#MACRO srl e { db $cb, $3b }
#MACRO srl h { db $cb, $3c }
#MACRO srl l { db $cb, $3d }
#MACRO stop { db $10, $00 }
#MACRO stop _value { db $10, _value }
#MACRO sub _value { sub a, _value }
#MACRO sub a, [hl] { db $96 }
#MACRO sub a, _value { db $d6, _value }
#MACRO sub a, a { db $97 }
#MACRO sub a, b { db $90 }
#MACRO sub a, c { db $91 }
#MACRO sub a, d { db $92 }
#MACRO sub a, e { db $93 }
#MACRO sub a, h { db $94 }
#MACRO sub a, l { db $95 }
#MACRO swap [hl] { db $cb, $36 }
#MACRO swap a { db $cb, $37 }
#MACRO swap b { db $cb, $30 }
#MACRO swap c { db $cb, $31 }
#MACRO swap d { db $cb, $32 }
#MACRO swap e { db $cb, $33 }
#MACRO swap h { db $cb, $34 }
#MACRO swap l { db $cb, $35 }
#MACRO xor a, [hl] { db $ae }
#MACRO xor _value { xor a, _value }
#MACRO xor a, _value { db $ee, _value }
#MACRO xor a, a { db $af }
#MACRO xor a, b { db $a8 }
#MACRO xor a, c { db $a9 }
#MACRO xor a, d { db $aa }
#MACRO xor a, e { db $ab }
#MACRO xor a, h { db $ac }
#MACRO xor a, l { db $ad }
