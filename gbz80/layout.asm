#LAYOUT ROM0[$0000, $4000], AT[0]
#LAYOUT ROMX[$4000, $8000], AT[$4000], BANKED[$001, $200]
#LAYOUT VRAM[$8000, $A000]
#LAYOUT SRAM[$A000, $C000], BANKED[0, 16]
#LAYOUT WRAM0[$C000, $E000]
;#LAYOUT WRAM0[$C000, $D000]
;#LAYOUT WRAMX[$D000, $E000], BANKED[1, 8]
#LAYOUT OAM[$FE00, $FEA0]
#LAYOUT HRAM[$FF80, $FFFF]

; We make sure rom bank 1 exists to get a 32kb rom at minimum
#SECTION "EnsureOneRomBank", ROMX, BANK[1] {
}
