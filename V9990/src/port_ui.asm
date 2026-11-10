; Shared V9990-only UI, copied from the stage overlay to surviving page-3 RAM.
    include "../build/port-art-config.inc"
    include "../build/port-music.inc"
    include "../build/smooth-config.inc"
    include "../build/gfx-sets.inc"
    org $E800
    jp ui_init
    jp ui_clear
    jp ui_draw
    jp ui_choose
    jp ui_irq
    jp ui_vblank
    jp ui_input
    jp ui_reg
    jp shared_music_start
    jp shared_music_stop
    jp shared_music_tick
    jp shared_load_helpers
    jp ui_show
    jp display_off             ; E827, survives menu/game overlays
    jp ui_apply_set            ; E82A, game start: selected graphics set + palette
    jp ui_family               ; E82D, A=terrain family cache (0/56), at VBlank
ui_init:
    call display_off
    ld a,$C8
    out ($64),a
    in a,($63)
    or $40                     ; configure UI sprite disable while hidden
    out ($63),a
    ei
    ld b,13
    ld a,ART_PLANE_PALETTES
    call ui_reg
    ld b,27
    xor a
    call ui_reg
    xor a
    out ($64),a
    out ($63),a
    ld a,$C0
    out ($63),a
    ld a,7
    out ($63),a
    ld hl,6144
    ld c,24
ui_name_row:
    ld b,32
ui_canvas_names:
    ld a,l
    out ($60),a
    ld a,h
    out ($60),a
    inc hl
    djnz ui_canvas_names
    ld b,32
    call ui_black_names
    dec c
    jr nz,ui_name_row
    ld c,8
ui_bottom_names:
    ld b,64
    call ui_black_names
    dec c
    jr nz,ui_bottom_names
    call ui_clear
    ei
    ret
ui_show:
    call ui_wait
    jp display_on
ui_black_names:
    ld a,1
    out ($60),a
    xor a
    out ($60),a
    djnz ui_black_names
    ret
ui_clear:
    ld ix,ui_clear_packets
    jp ui_draw
; Seven-byte copy descriptors: SX, SY(word), DX, DY offset, NX(0=256), NY.
ui_draw:
    ld a,(ix+0)
    cp $FF
    jr z,ui_wait
    call ui_wait
    ld a,(ix+0)
    ld (ui_command),a
    ld a,(ix+1)
    ld (ui_command+2),a
    ld a,(ix+2)
    ld (ui_command+3),a
    ld a,(ix+3)
    ld (ui_command+4),a
    ld a,(ix+4)
    ld (ui_command+6),a
    ld a,(ix+5)
    ld (ui_command+8),a
    or a
    ld a,0
    jr nz,ui_width
    inc a
ui_width:
    ld (ui_command+9),a
    ld a,(ix+6)
    ld (ui_command+10),a
    ld a,32
    out ($64),a
    ld hl,ui_command
    ld bc,$1563
    otir
    ld de,7
    add ix,de
    jr ui_draw
ui_wait:
    in a,($65)
    and 1
    jr nz,ui_wait
    ret
ui_choose:
    call display_off
    di
    ld a,MENU_PALETTE_BANK     ; menu font uses DiHalt's HUD bank colours
    call ui_stream
    ei
    xor a
    ld ($105F),a
    ld (ui_last),a
    call ui_redraw
ui_release:
    call ui_input
    and $10
    jr nz,ui_release
    call ui_show             ; complete menu, released fire, inputs ready
ui_menu_visible:
ui_menu_loop:
    call ui_vblank
    call ui_input
    bit 4,e
    jr nz,ui_confirm
    and 15
    ld b,a
    ld a,(ui_last)
    cpl
    and b
    ld c,a
    ld a,b
    ld (ui_last),a
    ld a,c
    or a
    jr z,ui_menu_loop
    bit 1,a                    ; left/right: GUANTXIP <-> DIHALT
    jr nz,ui_toggle_set
    bit 0,a
    jr nz,ui_toggle_set
    and $08                    ; up: STANDARD, down: HARD
    ld a,0
    jr nz,ui_select
    inc a
ui_select:
    ld b,a
    ld a,($105F)
    cp b
    jr z,ui_menu_loop
    ld a,b
    ld ($105F),a
    call ui_redraw
    jr ui_menu_loop
ui_toggle_set:
    ld a,(gfx_set)
    xor 1
    ld (gfx_set),a
    call ui_redraw
    jr ui_menu_loop
ui_confirm:
    call display_off            ; accepted fire: blank before waiting for release
ui_confirm_release:
    call ui_input
    and $10
    jr nz,ui_confirm_release
    ret
ui_redraw:
    call ui_clear
    ld a,($105F)
    or a
    ld ix,ui_normal
    jr z,ui_menu_draw
    ld ix,ui_hard
ui_menu_draw:
    call ui_draw
    ld a,(gfx_set)
    or a
    ld ix,ui_set_guantxip
    jr z,ui_set_draw
    ld ix,ui_set_dihalt
ui_set_draw:
    jp ui_draw

; ---- Graphics sets (Guantxip / DiHalt) ----------------------------------
; Packages in ROM, one record after another from $4000 of their first bank:
;   01 lo mid hi lenL lenH data  VRAM write   02 dstL dstH lenL lenH data  RAM
;   03 r14 lenL lenH data        palette      FF  continue at next bank $4000
;   00                           end
; Records never cross a bank. Called with DI. With ui_stream_irq set, a pending
; audio IRQ is served between records (it maps the ROM itself, so re-map).
ui_apply_set:
    ld a,i
    push af
    di
    ld a,(gfx_set)
    ld hl,loaded_set
    cp (hl)
    jr z,ui_apply_palette
    ld (hl),a
    or a
    ld a,GUANTXIP_SET_BANK
    jr z,ui_apply_load
    ld a,DIHALT_SET_BANK
ui_apply_load:
    ld hl,ui_stream_irq
    inc (hl)
    call ui_stream
    ld hl,ui_stream_irq
    dec (hl)
ui_apply_palette:
    ld a,(gfx_set)
    or a
    ld a,GUANTXIP_PALETTE_BANK
    jr z,ui_apply_pal
    ld a,DIHALT_PALETTE_BANK
ui_apply_pal:
    call ui_stream
    ld a,$FF
    ld (ui_last_family),a
    pop af
    ret po
    ei
    ret
; A=0 (family 0) or 56 (family 1). Only on a change: rewrite terrain bank 0.
ui_family:
    ld hl,ui_last_family
    cp (hl)
    ret z
    ld (hl),a
    or a
    ld a,(ui_family_banks)
    jr z,ui_family_go
    ld a,(ui_family_banks+1)
ui_family_go:
    or a
    ret z
    di
    call ui_stream
    ei
    ret
ui_stream:
    ld (ui_stream_bank),a
    ld hl,$4000
ui_stream_record:
    push hl
    call shared_select_rom
    pop hl
    ld a,(ui_stream_bank)
    ld ($6000),a
    ld a,(hl)
    inc hl
    or a
    jr z,ui_stream_end
    inc a
    jr z,ui_stream_bank_next
    dec a
    dec a
    jr z,ui_stream_vram
    dec a
    jr z,ui_stream_ram
    ld b,14                    ; palette: R#14 = entry*4
    ld a,(hl)
    inc hl
    call ui_reg
    ld c,$61
    jr ui_stream_data
ui_stream_vram:
    xor a
    out ($64),a                ; R#0.. auto-increment: write address
    ld bc,$0363
    otir
    ld c,$60
ui_stream_data:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld b,e
    ld a,e
    or a
    jr z,ui_stream_out
    inc d
ui_stream_out:
    otir
    dec d
    jr nz,ui_stream_out
    jr ui_stream_next
ui_stream_ram:
    ld e,(hl)
    inc hl
    ld d,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld b,(hl)
    inc hl
    ldir
ui_stream_next:
    ld a,(ui_stream_irq)
    or a
    jr z,ui_stream_record
    push hl
    call shared_select_ram
    ei
    nop
    di
    pop hl
    jr ui_stream_record
ui_stream_bank_next:
    ld hl,ui_stream_bank
    inc (hl)
    ld hl,$4000
    jr ui_stream_record
ui_stream_end:
    jp shared_select_ram
gfx_set: db 0                  ; 0 = GUANTXIP (default), 1 = DIHALT
loaded_set: db 1               ; the cartridge preloads DiHalt's set
ui_family_banks: db 0,0        ; written by each set package
ui_last_family: db $FF
ui_stream_bank: db 0
ui_stream_irq: db 0
; Only V9990 vertical flags tick music. Original MSX IRQ: acknowledge and return.
ui_irq:
    push af
    in a,($66)
    and 1
    jr nz,ui_audio_irq
    in a,($99)
    pop af
    ei
    ret
ui_audio_irq:
    out ($66),a
    push hl
    ld hl,ui_ticks
    inc (hl)
    pop hl
    in a,($99)
    push bc
    push de
    push hl
    push ix
    push iy
    exx
    ex af,af'
    push af
    push bc
    push de
    push hl
    call shared_music_tick
    call shared_psg
    pop hl
    pop de
    pop bc
    pop af
    ex af,af'
    exx
    pop iy
    pop ix
    pop hl
    pop de
    pop bc
    pop af
    ei
    ret
ui_vblank:
    ld a,(ui_ticks)
    ld b,a
ui_frame_wait:
    ld a,(ui_ticks)
    cp b
    jr z,ui_frame_wait
    ret
    include "port_display.inc"
ui_reg:
    push af
    ld a,b
    or $80
    out ($64),a
    pop af
    out ($63),a
    ret
    include "port_ui_input.inc"
ui_command: dw 0,0,0,1536,8,8
    db 0,$0C,$FF,0,0,0,0,0,$40 ; P1 UI canvas is lower bank A only
ui_ticks equ $105E
ui_last: db 0
ui_clear_packets:
    db 0
    dw 1440
    db 0,0,0,96,0
    dw 1440
    db 0,96,0,96,$FF
ui_normal:
    include "../build/ui-normal.inc"
ui_hard:
    include "../build/ui-hard.inc"
ui_set_guantxip:
    include "../build/ui-set0.inc"
ui_set_dihalt:
    include "../build/ui-set1.inc"
    include "port_shared_music.inc"
    assert $<=$F000
