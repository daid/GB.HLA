; -- JOYP / P1 ($FF00) --------------------------------------------------------
; Joypad face buttons
rP1   = $FF00
rJOYP = $FF00
JOYP_GET_BUTTONS    = %00_01_0000 ; reading A/B/Select/Start buttons
JOYP_GET_CTRL_PAD   = %00_10_0000 ; reading Control Pad directions
JOYP_GET_NONE       = %00_11_0000 ; reading nothing
JOYP_INPUTS         = %00_00_1111 ; bits equal to 0 indicate pressed (when reading inputs)

; -- SB ($FF01) ---------------------------------------------------------------
; Serial transfer data [r/w]
rSB = $FF01

; -- SC ($FF02) ---------------------------------------------------------------
; Serial transfer control
rSC = $FF02

SC_START    = $80
SC_SLOW     = $00
SC_FAST     = $02
SC_EXTERNAL = $00
SC_INTERNAL = $01

; -- DIV ($FF04) --------------------------------------------------------------
; Divider register [r/w]
rDIV = $FF04

; -- TIMA ($FF05) -------------------------------------------------------------
; Timer counter [r/w]
rTIMA = $FF05

; -- TMA ($FF06) --------------------------------------------------------------
; Timer modulo [r/w]
rTMA = $FF06

; -- TAC ($FF07) --------------------------------------------------------------
; Timer control
rTAC = $FF07

TAC_STOP    = $00
TAC_START   = $04

TAC_4KHZ    = %000000_00 ; every 256 M-cycles = ~4 KHz on DMG
TAC_262KHZ  = %000000_01 ; every 4 M-cycles = ~262 KHz on DMG
TAC_65KHZ   = %000000_10 ; every 16 M-cycles = ~65 KHz on DMG
TAC_16KHZ   = %000000_11 ; every 64 M-cycles = ~16 KHz on DMG

; -- IF ($FF0F) ---------------------------------------------------------------
; Pending interrupts
rIF = $FF0F

IF_JOYPAD = $10
IF_SERIAL = $08
IF_TIMER  = $04
IF_STAT   = $02
IF_VBLANK = $01


rNR10 = $FF10
rNR11 = $FF11
rNR12 = $FF12
rNR13 = $FF13
rNR14 = $FF14
rNR21 = $FF16
rNR22 = $FF17
rNR23 = $FF18
rNR24 = $FF19
rNR30 = $FF1A
rNR31 = $FF1B
rNR32 = $FF1C
rNR33 = $FF1D
rNR34 = $FF1E
rNR41 = $FF20
rNR42 = $FF21
rNR43 = $FF22
rNR44 = $FF23
rNR50 = $FF24
rNR51 = $FF25
rNR52 = $FF26

; -- LCDC ($FF40) -------------------------------------------------------------
; PPU graphics control
rLCDC = $FF40
LCDC_OFF        = $00
LCDC_ON         = $80
LCDC_WIN_9800   = $00
LCDC_WIN_9C00   = $40
LCDC_WIN_OFF    = $00
LCDC_WIN_ON     = $20
LCDC_BLOCK21    = $00
LCDC_BLOCK01    = $10
LCDC_BG_9800    = $00
LCDC_BG_9C00    = $08
LCDC_OBJ_8      = $00
LCDC_OBJ_16     = $04
LCDC_OBJ_OFF    = $00
LCDC_OBJ_ON     = $02
LCDC_BG_OFF     = $00
LCDC_BG_ON      = $01

; -- STAT ($FF41) -------------------------------------------------------------
; Graphics status and interrupt control
rSTAT = $FF41

STAT_LYC    = $40
STAT_MODE_2 = $20
STAT_MODE_1 = $10
STAT_MODE_0 = $08
STAT_LYCF   = $04
STAT_BUSY   = $02

STAT_MODE_MASK  = %000000_11 ; PPU's current status [ro]
STAT_HBLANK     = %000000_00 ; waiting after a line's rendering (HBlank)
STAT_VBLANK     = %000000_01 ; waiting between frames (VBlank)
STAT_OAM        = %000000_10 ; checking which OBJs will be rendered on this line (OAM scan)
STAT_LCD        = %000000_11 ; pushing pixels to the LCD

; -- SCY ($FF42) --------------------------------------------------------------
; Background Y scroll offset (in pixels) [r/w]
rSCY = $FF42

; -- SCX ($FF43) --------------------------------------------------------------
; Background X scroll offset (in pixels) [r/w]
rSCX = $FF43

; -- LY ($FF44) ---------------------------------------------------------------
; Y coordinate of the line currently processed by the PPU (0-153) [ro]
rLY = $FF44

; -- LYC ($FF45) --------------------------------------------------------------
; Value that LY is constantly compared to [r/w]
rLYC = $FF45

; -- DMA ($FF46) --------------------------------------------------------------
; OAM DMA start address (high 8 bits) and start [wo]
rDMA = $FF46

; -- BGP ($FF47) --------------------------------------------------------------
; (DMG only) Background color mapping [r/w]
rBGP = $FF47

; -- OBP0 ($FF48) -------------------------------------------------------------
; (DMG only) OBJ color mapping #0 [r/w]
rOBP0 = $FF48

; -- OBP1 ($FF49) -------------------------------------------------------------
; (DMG only) OBJ color mapping #1 [r/w]
rOBP1 = $FF49

; -- WY ($FF4A) ---------------------------------------------------------------
; Y coordinate of the Window's top-left pixel (0-143) [r/w]
rWY = $FF4A

; -- WX ($FF4B) ---------------------------------------------------------------
; X coordinate of the Window's top-left pixel, plus 7 (7-166) [r/w]
rWX = $FF4B

; -- SPD / KEY1 ($FF4D) -------------------------------------------------------
; (CGB only) Double-speed mode control
rKEY1 = $FF4D

KEY1_SINGLE  = $00
KEY1_DOUBLE  = $80
KEY1_PREPARE = $01


; -- VBK ($FF4F) --------------------------------------------------------------
; (CGB only) VRAM bank number (0 or 1)
rVBK = $FF4F

; -- VDMA_SRC_HIGH / HDMA1 ($FF51) --------------------------------------------
; (CGB only) VRAM DMA source address (high 8 bits) [wo]
rHDMA1 = $FF51

; -- VDMA_SRC_LOW / HDMA2 ($FF52) ---------------------------------------------
; (CGB only) VRAM DMA source address (low 8 bits) [wo]
rHDMA2 = $FF52

; -- VDMA_DEST_HIGH / HDMA3 ($FF53) -------------------------------------------
; (CGB only) VRAM DMA destination address (high 8 bits) [wo]
rHDMA3 = $FF53

; -- VDMA_DEST_LOW / HDMA4 ($FF54) --------------------------------------------
; (CGB only) VRAM DMA destination address (low 8 bits) [wo]
rHDMA4 = $FF54

; -- VDMA_LEN / HDMA5 ($FF55) -------------------------------------------------
; (CGB only) VRAM DMA length, mode, and start
rHDMA5 = $FF55

; -- RP ($FF56) ---------------------------------------------------------------
; (CGB only) Infrared communications port
rRP = $FF56

RP_DISABLE = %00_000000
RP_ENABLE  = %11_000000

RP_DATA_IN = $02
RP_LED_ON  = $01

; -- BGPI / BCPS ($FF68) ------------------------------------------------------
; (CGB only) Background palette I/O index
rBCPS = $FF68

; -- BGPD / BCPD ($FF69) ------------------------------------------------------
; (CGB only) Background palette I/O access [r/w]
rBCPD = $FF69

; -- OBPI / OCPS ($FF6A) ------------------------------------------------------
; (CGB only) OBJ palette I/O index
rOCPS = $FF6A

; -- OBPD / OCPD ($FF6B) ------------------------------------------------------
; (CGB only) OBJ palette I/O access [r/w]
rOCPD = $FF6B

; -- OPRI ($FF6C) -------------------------------------------------------------
; (CGB boot ROM only) OBJ draw priority mode
rOPRI = $FF6C

; -- WBK / SVBK ($FF70) -------------------------------------------------------
; (CGB only) WRAM bank number
rSVBK = $FF70

; -- PCM12 ($FF76) ------------------------------------------------------------
; Audio channels 1 and 2 output
rPCM12 = $FF76

; -- PCM34 ($FF77) ------------------------------------------------------------
; Audio channels 3 and 4 output
rPCM34 = $FF77

; -- IE ($FFFF) ---------------------------------------------------------------
; Interrupt enable
rIE = $FFFF
IE_JOYPAD = $10
IE_SERIAL = $08
IE_TIMER  = $04
IE_STAT   = $02
IE_VBLANK = $01
