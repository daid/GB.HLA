#MACRO GB_LOGO {
    db $CE, $ED, $66, $66, $CC, $0D, $00, $0B, $03, $73, $00, $83, $00, $0C, $00, $0D
    db $00, $08, $11, $1F, $88, $89, $00, $0E, $DC, $CC, $6E, $E6, $DD, $DD, $D9, $99
    db $BB, $BB, $67, $63, $6E, $0E, $EC, $CC, $DD, $DC, $99, $9F, $BB, $B9, $33, $3E
}
#MACRO GB_HEADER_IMPL _title, _mbc, _gbc, _sgb, _entry {
    #SECTION "Header", ROM0[$100] {
        nop
        jp _entry
        GB_LOGO
        db _title
        ds 15 - STRLEN(_title)
        db _gbc ; GBC flag
        db $00, $00 ; New licensee code
        db _sgb ; SGB flag
        db _mbc ; cart type
        db BIT_LENGTH(BANK_MAX(ROMX)) - 1 ; ROM size
        db ((BANK_MAX(SRAM) > -1) * 2) + (BANK_MAX(SRAM) > 0) + ((BANK_MAX(SRAM) > 3) * 2) + ((BANK_MAX(SRAM) > 7) * -1); SRAM size
        db $01 ; JP only or worldwide
        db $33 ; Licensee
        db $00 ; Version
        db LOW(-CHECKSUM($134, $14D)-($14D - $134))
        dw ((CHECKSUM() & $FF00) >> 8) | ((CHECKSUM() & $00FF) << 8)
    }
}
#MACRO GB_HEADER _title, _mbc, _entry {
    GB_HEADER_IMPL _title, _mbc, $00, $00, _entry
}
#MACRO SGB_HEADER _title, _mbc, _entry {
    GB_HEADER_IMPL _title, _mbc, $00, $03, _entry
}
#MACRO GBC_HEADER _title, _mbc, _entry {
    GB_HEADER_IMPL _title, _mbc, $80, $00, _entry
}
#MACRO GBC_SGB_HEADER _title, _mbc, _entry {
    GB_HEADER_IMPL _title, _mbc, $80, $03, _entry
}


GB_MCB_ROM_ONLY             = $00
GB_MBC1                     = $01
GB_MBC1_RAM                 = $02
GB_MBC1_RAM_BATTERY         = $03
GB_MBC2                     = $05
GB_MBC2_BATTERY             = $06
GB_MBC_ROM_RAM              = $08
GB_MBC_ROM_RAM_BATTERY      = $09
GB_MMM01                    = $0B
GB_MMM01_RAM                = $0C
GB_MMM01_RAM_BATTERY        = $0D
GB_MBC3_TIMER_BATTERY       = $0F
GB_MBC3_TIMER_RAM_BATTERY   = $10
GB_MBC3                     = $11
GB_MBC3_RAM                 = $12
GB_MBC3_RAM_BATTERY         = $13
GB_MBC5                     = $19
GB_MBC5_RAM                 = $1A
GB_MBC5_RAM_BATTERY         = $1B
GB_MBC5_RUMBLE              = $1C
GB_MBC5_RUMBLE_RAM          = $1D
GB_MBC5_RUMBLE_RAM_BATTERY  = $1E
GB_MBC6                     = $20
GB_MBC7                     = $22
GB_MBC_POCKET_CAMERA        = $FC
GB_MBC_BANDAI_TAMA5         = $FD
GB_MBC_HuC3                 = $FE
GB_MBC_HuC1_RAM_BATTERY     = $FF
