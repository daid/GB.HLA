#MACRO GB_LOGO {
    db $CE, $ED, $66, $66, $CC, $0D, $00, $0B, $03, $73, $00, $83, $00, $0C, $00, $0D
    db $00, $08, $11, $1F, $88, $89, $00, $0E, $DC, $CC, $6E, $E6, $DD, $DD, $D9, $99
    db $BB, $BB, $67, $63, $6E, $0E, $EC, $CC, $DD, $DC, $99, $9F, $BB, $B9, $33, $3E
}
#MACRO GB_HEADER _title, _mbc, _entry {
    #SECTION "Header", ROM0[$100] {
        nop
        jp _entry
        GB_LOGO
        db _title
        ds 15 - STRLEN(_title)
        db $00 ; GBC flag
        db $00, $00 ; New licensee code
        db $00 ; SGB flag
        db _mbc ; cart type
        db BIT_LENGTH(BANK_MAX(ROMX)) - 1 ; ROM size
        db $00 ; SRAM size
        db $01 ; JP only or worldwide
        db $00 ; Licensee
        db $00 ; Version
        db LOW(-CHECKSUM($134, $14D)-($14D - $134))
        dw ((CHECKSUM() & $FF00) >> 8) | ((CHECKSUM() & $00FF) << 8)
    }
}