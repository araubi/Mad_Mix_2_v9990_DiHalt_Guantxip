; Combined fixed keyboard and both joystick ports. Original logical E bits retained.
; Q/A/O/P, arrows; SPACE/M and either joystick trigger; H pause remains original.
; 0 (testing): ends the stage.
read_controls:
    push bc
    push de
    push hl
    call $5795                   ; original five key pairs + H
    di
    ld e,a
    in a,($AA)
    and $F0
    or 8
    out ($AA),a
    in a,($A9)
    bit 4,a
    jr nz,no_left
    set 1,e
no_left:
    bit 5,a
    jr nz,no_up
    set 3,e
no_up:
    bit 6,a
    jr nz,no_down
    set 2,e
no_down:
    bit 7,a
    jr nz,no_right
    set 0,e
no_right:
    in a,($AA)
    and $F0
    or 4
    out ($AA),a
    in a,($A9)
    bit 2,a
    jr nz,no_m
    set 4,e
no_m:
    in a,($AA)                   ; test key 0 (row 0 bit 0): finish the stage
    and $F0
    out ($AA),a
    in a,($A9)
    rra
    jr c,no_zero
    ld hl,($3E8D)                ; COCOS_COMIDOS = COCOS_TOTAL, as when the last
    ld ($3E8B),hl                ; dot is eaten
no_zero:
    ld c,e
    ld a,7
    out ($A0),a
    in a,($A2)
    ld d,a
    and $3F
    or $80
    out ($A1),a
    ld a,15
    out ($A0),a
    in a,($A2)
    ld b,a
    and $BF
    out ($A1),a
    ld a,14
    out ($A0),a
    in a,($A2)
    ld l,a
    ld a,15
    out ($A0),a
    ld a,b
    or $40
    out ($A1),a
    ld a,14
    out ($A0),a
    in a,($A2)
    and l
    cpl
    and $3F
    ld l,a
    ld a,15
    out ($A0),a
    ld a,b
    out ($A1),a
    ld a,7
    out ($A0),a
    ld a,d
    out ($A1),a
    ld e,c
    bit 0,l
    jr z,no_joy_up
    set 3,e
no_joy_up:
    bit 1,l
    jr z,no_joy_down
    set 2,e
no_joy_down:
    bit 2,l
    jr z,no_joy_left
    set 1,e
no_joy_left:
    bit 3,l
    jr z,no_joy_right
    set 0,e
no_joy_right:
    ld a,l
    and $30
    jr z,no_joy_fire
    set 4,e
no_joy_fire:
    ld a,($E830)                 ; menu option: up goes up-right (turn 90 degrees)
    or a
    ld a,e
    jr z,controls_done
    and $F0
    bit 3,e                      ; up -> right
    jr z,$+4
    or 1
    bit 0,e                      ; right -> down
    jr z,$+4
    or 4
    bit 2,e                      ; down -> left
    jr z,$+4
    or 2
    bit 1,e                      ; left -> up
    jr z,$+4
    or 8
controls_done:
    pop hl
    pop de
    pop bc
    ld e,a
    ei
    ret
