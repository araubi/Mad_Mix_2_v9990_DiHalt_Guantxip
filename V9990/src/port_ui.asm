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
ui_dirs: db 0                  ; E830, read_controls: 0 = up goes up-left, 1 = up-right
TURBO_R_ID: db 0               ; E831, port_menu copies BIOS $002D saved by port_boot (3 = turbo R)
    assert TURBO_R_ID==$E831
cpu_switch:
    include "port_cpu_switch.inc"
    assert cpu_switch==$E832
    assert ui_dirs==$E830
; E869, draw_pose: HL=2*pose index (0..628), BC=pose_offsets -> HL=&offset word.
; Guantxip set: while the big-ball power lasts (word $3FA5, original timer) Pac's
; bodies use his red sprites; under 30 ticks they blink like the original colour.
ui_power:
    push hl
    add hl,bc
    ex (sp),hl                 ; stack = normal pointer, HL = 2*index
    ld a,(ui_power_on)
    or a
    jr z,pw_normal
    ld de,($3FA5)
    ld a,d
    or e
    jr z,pw_normal
    ld a,d
    or a
    jr nz,pw_red
    ld a,e
    cp 30
    jr nc,pw_red
    and 1                      ; original TIEMPOS_PROTA blinks on bit 0
    jr nz,pw_normal
pw_red:
    ld de,210
    ld c,0                     ; variant*8
pw_variant:
    or a
    sbc hl,de
    jr c,pw_pose
    ld a,c
    add a,8
    ld c,a
    jr pw_variant
pw_pose:
    add hl,de
    ld a,l
    rrca                       ; pose 0..104
    ld hl,ui_power_poses
    ld b,8
pw_scan:
    cp (hl)
    jr z,pw_hit
    inc hl
    inc c
    djnz pw_scan
pw_normal:
    pop hl
    ret
pw_hit:
    pop hl
    ld a,c
    add a,a
    ld l,a
    ld h,0
    ld de,ui_power_offsets
    add hl,de
    ret
ui_power_poses: db 0,1,2,3,4,5,25,26
ui_power_on: db 0              ; written by each set package (1 = Guantxip)
ui_power_offsets: ds 48        ; 3 variants x 8 poses, offsets into pose_data
    assert ui_power==$E869
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
    ld (ui_row),a
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
    ld hl,ui_row               ; up/down: choose the row
    bit 3,a
    jr z,ui_not_up
    ld a,(hl)
    or a
    jr z,ui_menu_loop
    dec (hl)
    jr ui_menu_changed
ui_not_up:
    bit 2,a
    jr z,ui_not_down
    ld a,(hl)
    cp 3
    jr z,ui_menu_loop
    inc (hl)
    jr ui_menu_changed
ui_not_down:
    ld a,(hl)                  ; left/right: change the row's value
    cp 3
    jr nz,ui_toggle
    ld a,(TURBO_R_ID)          ; CPU row: fixed at Z80 without a turbo R
    cp 3
    jr c,ui_menu_loop
    ld a,3
ui_toggle:
    call ui_row_var
    ld a,(hl)
    xor 1
    ld (hl),a
ui_menu_changed:
    call ui_redraw
    jr ui_menu_loop
ui_confirm:
    call display_off            ; accepted fire: blank before waiting for release
ui_confirm_release:
    call ui_input
    and $10
    jr nz,ui_confirm_release
    ret
; Rows: 0 difficulty ($105F), 1 graphics set, 2 cursor-up direction. The
; cursor row is drawn in the selected style between < >, the others plain.
ui_redraw:
    call ui_clear
    xor a
ui_redraw_row:
    ld (ui_draw_row),a
    call ui_row_var            ; HL = row variable (0/1)
    ld a,(ui_draw_row)
    add a,a
    add a,(hl)
    add a,a
    ld e,a
    ld d,0
    ld hl,ui_menu_texts
    add hl,de
    ld e,(hl)
    inc hl
    ld d,(hl)
    ex de,hl                   ; HL = y, x, length, characters
    ld a,(hl)
    ld (ui_pkt+4),a
    inc hl
    ld b,(hl)
    inc hl
    ld c,(hl)
    inc hl
    ld a,(ui_row)
    ld e,a
    ld a,(ui_draw_row)
    cp e
    ld a,64
    jr nz,ui_row_style
    push bc                    ; cursor row: '<' and '>' around the value
    ld a,b
    sub 32
    ld b,a
    ld a,'<'
    call ui_char
    pop bc
    push bc
    ld a,c
    add a,a
    add a,a
    add a,a
    add a,a
    add a,b
    add a,16
    ld b,a
    ld a,'>'
    call ui_char
    pop bc
    xor a
ui_row_style:
    ld (ui_style),a
ui_row_chars:
    ld a,(hl)
    cp ' '
    call nz,ui_char
    inc hl
    ld a,b
    add a,16
    ld b,a
    dec c
    jr nz,ui_row_chars
    ld a,64                    ; arrows use the unselected style
    ld (ui_style),a
    ld a,(ui_draw_row)
    inc a
    cp 4
    jr c,ui_redraw_row
    ret
; A = row -> HL = its variable
ui_row_var:
    ld hl,$105F
    or a
    ret z
    ld hl,gfx_set
    dec a
    ret z
    ld hl,ui_dirs
    dec a
    ret z
    ld hl,ui_cpu
    ret
; A = character, B = x. Style in ui_style (0 selected, 64 unselected).
ui_char:
    push hl
    push bc
    sub 32
    ld e,a
    and 15
    add a,a
    add a,a
    add a,a
    add a,a
    ld (ui_pkt),a
    ld a,e
    and $30
    ld hl,ui_style
    add a,(hl)
    ld l,a
    ld h,0
    ld de,1312
    add hl,de
    ld (ui_pkt+1),hl
    ld a,b
    ld (ui_pkt+3),a
    ld ix,ui_pkt
    call ui_draw
    pop bc
    pop hl
    ret

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
    ld a,(TURBO_R_ID)          ; turbo R: S1990 register 6 = $60 Z80, $40 R800
    cp 3                       ; (ROM mode, as BIOS CHGCPU), LED on port $A7
    jr c,ui_apply_cpu_done
    ld a,(ui_cpu)
    or a
    ld bc,$6000
    jr z,ui_apply_cpu
    ld bc,$4080
ui_apply_cpu:
    push bc
    ld a,b
    call cpu_switch
    pop bc
    ld a,c
    out ($A7),a                ; R800 LED
ui_apply_cpu_done:
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
ui_cpu: db 0                   ; 0 = Z80, 1 = R800 (turbo R only)
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
ui_row: db 0
ui_draw_row: db 0
ui_style: db 64
ui_pkt: db 0
    dw 0
    db 0,0,16,16,$FF
ui_clear_packets:
    db 0
    dw 1440
    db 0,0,0,96,0
    dw 1440
    db 0,96,0,96,$FF
    include "../build/ui-menu.inc"
    include "port_shared_music.inc"
    assert $<=$F000
