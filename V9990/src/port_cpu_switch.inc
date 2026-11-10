; turbo R CPU switch, same protocol as BIOS CHGCPU. A = S1990 register 6
; ($60 Z80, $40 R800 ROM mode). The CPU being stopped parks right after its
; OUT; the other one resumes where IT last parked: inside BIOS CHGCPU the
; first time (boot only, BIOS in page 0), here afterwards. Both paths reload
; SP from $FFFD and pop the same registers, so the call returns on the new
; CPU. Position independent: port_boot copies these bytes to the address the
; UI later holds them at ($E832), so a parked CPU always finds them there.
    di
    push hl
    push de
    push bc
    push af
    push ix
    push iy
    exx
    ex af,af'
    push hl
    push de
    push bc
    push af
    ld a,i
    push af
    ld ($FFFD),sp
    ex af,af'
    ld e,a
    ex af,af'
    ld a,6
    out ($E4),a
    ld a,e
    out ($E5),a
    di
    ld sp,($FFFD)
    pop af
    ld i,a
    pop af
    pop bc
    pop de
    pop hl
    exx
    ex af,af'
    pop iy
    pop ix
    pop af
    pop bc
    pop de
    pop hl
    ret
