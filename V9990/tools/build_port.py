#!/usr/bin/env python3
"""Build native P1 game from checked original images and editable art/maps."""
from pathlib import Path
import json, struct, subprocess, hashlib, os, re, xml.etree.ElementTree as ET
from PIL import Image
from palette64 import local_image
from compile_branding import fanfare_stream
from compile_opening import compile_opening
from compile_topo import compile_topo
from compile_ui import compile_ui
from compile_effects import compile_effects
from gfx_sets import compile_set, Package, pat8
R=Path(__file__).resolve().parents[2]; B=R/'V9990/build'; A=Path(os.environ.get('MADMIX_ASSET_ROOT',R/'V9990/assets'))
SJ=os.environ.get('SJASM','sjasm')
# Optional: precompiled music/SFX/opening (from release v1.0) when the private
# PSG captures and opening artwork are not available.
PRE=Path(os.environ['MADMIX_PREBUILT']) if os.environ.get('MADMIX_PREBUILT') else None
def asm(name):
    subprocess.run([SJ,str(R/'V9990/src'/f'{name}.asm'),str(B/f'{name}.bin')],cwd=R,check=True)
def main():
    contracts=json.loads((R/'V9990/src/patch-contracts.json').read_text())
    gameplay=json.loads((R/'V9990/src/gameplay-config.json').read_text())
    step_multiplier=gameplay['hard_world_step_multiplier']
    assert type(step_multiplier) is int and step_multiplier==2, "HARD doubles movement; select NORMAL at runtime for the original speed"
    B.mkdir(parents=True,exist_ok=True)
    (B/'gameplay-config.inc').write_text(f'WORLD_STEP_MULTIPLIER equ {step_multiplier}\nACTOR_DELTA_LIMIT equ {32*step_multiplier}\n')
    raw=(R/'MSX/build/game.bin').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==contracts['game_sha256'], 'Original game image changed; review patch contracts'
    loader=(R/'MSX/build/loader.bin').read_bytes()
    for a,expected in contracts['loader'].items():
        off=int(a,16)-0xC350;assert loader[off:off+len(bytes.fromhex(expected))]==bytes.fromhex(expected),a
    mem=bytearray(65536);mem[0x1060:0x1060+len(raw)]=raw
    for st in range(9):
        word=lambda a:int.from_bytes(mem[a:a+2],'little')
        resource=0x66F6+9*(st//3);desc=word(resource)+253*mem[0x43A3+st]
        groups=sum(mem[desc+a-0x3E8F] for a in (0x3E9C,0x3EBD,0x3EDE,0x3EFF,0x3F18,0x3F3B,0x3F46,0x3F67))+10
        assert 0xDCB9+groups*12<0xE000, 'Authored depth queue overlaps contacts helper'
    B.mkdir(parents=True,exist_ok=True)
    config=json.loads((A/'palette-config.json').read_text())
    colors=json.loads((A/'palettes.json').read_text())['banks']
    assert len(colors)==4 and all(len(b)==16 for b in colors)
    assert all(len(rgb)==3 and all(isinstance(v,int) and 0<=v<=31 for v in rgb) for bank in colors for rgb in bank)
    assert all(config[k] in range(4) for k in ('hud_bank','terrain_bank','sprite_bank'))
    assert config['stage_colors'] in ('original','fixed')
    (B/'port-art-config.inc').write_text(f"ART_PLANE_PALETTES equ {config['hud_bank']+4*config['terrain_bank']}\nART_SPRITE_ATTR equ {32+64*config['sprite_bank']}\nART_DETAIL_ATTR equ {32+64*config['sprite_bank']}\nART_STAGE_PALETTE equ {4*(16*config['terrain_bank']+1)}\nART_STAGE_ORIGINAL equ {int(config['stage_colors']=='original')}\n")
    # Both graphics sets compile to the same blobs (gfx_sets.compile_set).
    # DiHalt's is preloaded at boot exactly as before; either one is streamed
    # again at game start by ui_apply_set when the menu choice changes.
    dihalt=compile_set(A,config)
    gx_root=R/'V9990/assets-guantxip'
    guantxip=compile_set(gx_root,config,guantxip=True)
    uploads=[]
    (B/'port-hud-names.bin').write_bytes(dihalt['hud_names'])
    (B/'port-life-names.bin').write_bytes(dihalt['life_names'])
    # Occupancy masks (the original game's tile masks, RAM 67CB/800B) are
    # shared: Guantxip's new tiles at numbers Topo's maps never use get their
    # mask in the image. Family-0 tile 30 is used by both sets with different
    # masks: each set package fills ui_occ_patch and ui_apply_set copies it.
    cpu_tiles=[bytearray(c) for c in guantxip['cpu_tiles']]
    cpu_tiles[0][30*64:31*64]=dihalt['cpu_tiles'][0][30*64:31*64]
    new_tiles=json.loads((gx_root/'baldosas-mapa.json').read_text())['ocupacion']
    # The boot preload is the DiHalt set (no stream when it stays selected).
    (B/'ui-occ-dihalt.inc').write_text('    db '+','.join(str(v) for v in dihalt['cpu_tiles'][0][30*64:31*64])+'\n')
    for fam in range(2):
        for t in range(56):
            if str(t) not in new_tiles[f'family{fam}'] or (fam,t)==(0,30):assert cpu_tiles[fam][t*64:t*64+64]==dihalt['cpu_tiles'][fam][t*64:t*64+64],(fam,t)
    uploads += [(0,dihalt['patterns']),(0x40000,dihalt['tiles']),(0x48000,dihalt['tiles']),(0x72000,dihalt['tiles'])]
    unique=range(dihalt['master_patterns']);descs=dihalt['descs']
    uploads.append((0x10000,dihalt['master']))
    # Shared one-pixel black detail pattern, reserved slot126 in each cache.
    uploads += [(0x33870,b'\x10'),(0x3B870,b'\x10')]
    details=bytearray()
    for i in range(60):
        x,y=mem[0x42E1+2*i:0x42E3+2*i];mask,pixel=mem[0x60A0+2*(x&7):0x60A2+2*(x&7)]
        assert pixel and pixel&(pixel-1)==0
        details+=bytes((x&248,y,mask,(x&248)+7-(pixel.bit_length()-1)))
    (B/'port-detail-points.bin').write_bytes(details)
    (B/'port-pose-data.bin').write_bytes(descs)
    (B/'port-pose-offsets.bin').write_bytes(dihalt['offsets'])
    for k in ('descs','offsets'):assert len(guantxip[k])<=len(dihalt[k]),f'Guantxip {k} larger than the resident DiHalt area'
    # Store full editable maps in VRAM as non-displayed data. Runtime loads the
    # selected 3584-byte bank into original A900 collision/game map RAM.
    uploads.append((0x20000,dihalt['maps']))   # each set package rewrites them
    pal=bytes(c for bank in json.loads((A/'palettes.json').read_text())['banks'] for rgb in bank for c in rgb)
    (B/'port-palette.bin').write_bytes(pal)
    (B/'port-tms-palette.bin').write_bytes(pal[48:96])
    # Independent editable PC title: plane B patterns above terrain, names at7E000.
    title=Image.open(A/'screens/title.png');assert title.mode=='P' and title.size==(256,192)
    assert max(title.tobytes())<16
    tp=[bytes(64)];tn=bytearray(struct.pack("<4096H",*([2048]*4096)))
    for y in range(24):
        for x in range(32):
            t=title.crop((x*8,y*8,x*8+8,y*8+8)).tobytes()
            if t not in tp:tp.append(t)
            struct.pack_into('<H',tn,(y*64+x)*2,2048+tp.index(t))
    uploads.append((0x50000,pat8(tp)))
    (B/'title-names.bin').write_bytes(b''.join(tn[y*128:y*128+64] for y in range(24)))
    loading=Image.open(A/'screens/loading.png');assert loading.mode=='P' and loading.size==(256,192)
    assert set(loading.tobytes())<={0,15}
    lp=[bytes(64)];ln=bytearray(struct.pack('<4096H',*([3072]*4096)))
    for y in range(24):
        for x in range(32):
            t=loading.crop((x*8,y*8,x*8+8,y*8+8)).tobytes()
            if t not in lp:lp.append(t)
            struct.pack_into('<H',ln,(y*64+x)*2,3072+lp.index(t))
    assert len(pat8(lp))<=0x8000
    uploads.extend([(0x58000,pat8(lp)),(0x7E000,ln)])
    (B/'title-palette.bin').write_bytes(bytes(round(v*31/255) for v in title.getpalette()[:48]))
    (B/'title-game-palette.bin').write_bytes(pal[144:192])
    uploads.extend(compile_ui(A,B,config))
    uploads.append((0x47FE0,bytes(32)))  # immutable blank pattern1023
    topo_tiles,topo_stream,topo_frames=compile_topo(A)
    assert 0x60000+len(pat8(topo_tiles))<=0x72000, "Topo atlas overlaps immutable terrain master"
    uploads.append((0x60000,pat8(topo_tiles)))
    # Game plus original loader sequence occupy banks 0..7. Preload assets using
    # a temporary page-3 routine while page 1 still contains the cartridge.
    banks=[];inc=[];upload_banks={}
    for address,blob in uploads:
        for off in range(0,len(blob),16384):
            chunk=blob[off:off+16384];padded=bytes(chunk).ljust(16384,b'\0')
            if padded not in upload_banks:
                upload_banks[padded]=8+len(banks);banks.append(padded)
            bank=upload_banks[padded];addr=address+off
            inc += [f'    ld a,{bank}','    ld ($6000),a',f'    ld a,{addr>>16}',f'    ld de,${addr&65535:04X}','    call set_write','    ld hl,$4000',f'    ld de,{len(chunk)}','    call upload']
    (B/'port-uploads.inc').write_text('\n'.join(inc)+'\n')
    if PRE:
        import shutil
        for n in ('music-events.bin','music-events.json'):shutil.copy(PRE/n,B/n)
    else:subprocess.run(['python3',str(R/'V9990/tools/compile_music.py')],check=True)
    music=(B/'music-events.bin').read_bytes(); music_bank=8+len(banks)
    meta=json.loads((B/'music-events.json').read_text()); loop=meta['loop']
    (B/'port-music.inc').write_text(f'MUSIC_BANK equ {music_bank}\nMUSIC_LOOP_BANK equ {music_bank+loop//16384}\nMUSIC_LOOP_PTR equ {0x4000+loop%16384}\n')
    for off in range(0,len(music),16384):banks.append(music[off:off+16384].ljust(16384,b'\xff'))
    (B/'topo-config.inc').write_text(f'TOPO_BANK equ {8+len(banks)}\nTOPO_FRAMES equ {len(topo_frames)}\n')
    for off in range(0,len(topo_stream),16384):banks.append(topo_stream[off:off+16384].ljust(16384,b'\xff'))
    (B/'topo-build.json').write_text(json.dumps({'frames':len(topo_frames),'patterns':len(topo_tiles),'stream_bytes':len(topo_stream)},indent=2)+'\n')
    # Original Spy2 DiHalt logo, byte-exact RGB332; no new quantization.
    logo=Image.open(A/'branding/dihalt_logo-b1.png').convert('RGB')
    assert logo.size==(256,212)
    logo_raw=bytearray()
    for r,g,b in logo.getdata():
        code=(((g*7+127)//255)<<5)|(((r*7+127)//255)<<2)|((b*3+127)//255)
        assert (r,g,b)==(((code>>2)&7)*255//7,((code>>5)&7)*255//7,(code&3)*255//3)
        logo_raw.append(code)
    inc=[]
    for off in range(0,len(logo_raw),16384):
        chunk=logo_raw[off:off+16384];bank=8+len(banks);banks.append(chunk.ljust(16384,b'\0'))
        inc += [f'    ld a,{bank}','    ld ($6000),a','    xor a',f'    ld de,{off}','    call set_write','    ld hl,$4000',f'    ld de,{len(chunk)}','    call upload']
    fanfare,frames=fanfare_stream(A/'branding/dihalt_fanfare.vgm')
    (B/'branding-fanfare.bin').write_bytes(fanfare)
    (B/'branding-uploads.inc').write_text(f'BRANDING_FRAMES equ {frames+50}\n'+'\n'.join(inc)+'\n')
    (B/'branding.json').write_text(json.dumps({'music_frames':frames,'total_frames':frames+50,'hz':50,'source':'Spy vs Spy2 V9990 opening'},indent=2)+'\n')
    opening=(PRE/'opening-b3.bin').read_bytes() if PRE else compile_opening(A,B)
    inc=[]
    for off in range(0,len(opening),16384):
        chunk=opening[off:off+16384];bank=8+len(banks);banks.append(chunk.ljust(16384,b'\0'))
        inc += [f'    ld a,{bank}','    ld ($6000),a',f'    ld a,{off>>16}',f'    ld de,{off&65535}','    call set_write','    ld hl,$4000',f'    ld de,{len(chunk)}','    call upload']
    (B/'opening-uploads.inc').write_text('\n'.join(inc)+'\n')
    # Graphics-set packages streamed by port_ui (ui_stream). RAM targets are
    # resident labels known only after assembly: lay out with placeholders,
    # then rebuild the same-sized banks with the real addresses.
    def set_package(st,addr,family_banks):
        pk=Package()
        pk.ram(addr['ui_family_banks'],bytes(family_banks));pk.ram(addr['ui_power_on'],st['power'])
        pk.ram(addr['pose_offsets'],st['offsets']);pk.ram(addr['pose_data'],st['descs'])
        pk.ram(addr['hud_names'],st['hud_names']);pk.ram(addr['life_names'],st['life_names'])
        pk.ram(addr['ui_occ_patch'],st['cpu_tiles'][0][30*64:31*64])
        pk.vram(0,st['patterns']);pk.vram(0x10000,st['master'])
        for a in (0x40000,0x48000,0x72000):pk.vram(a,st['tiles'])
        pk.vram(0x20000,st['maps'])
        return pk.blobs()
    def pal_package(entry,data):
        pk=Package();pk.palette(entry,data);return pk.blobs()
    gfx={}
    def place(name,blobs):
        gfx[name]=(8+len(banks),len(blobs));banks.extend(blobs)
    place('GUANTXIP_PALETTE_BANK',pal_package(0,guantxip['palette']))
    place('DIHALT_PALETTE_BANK',pal_package(0,dihalt['palette']))
    place('MENU_PALETTE_BANK',pal_package(32,dihalt['palette'][96:144]))
    place('GUANTXIP_FAMILY0_BANK',pal_package(1,guantxip['family'][0]))
    place('GUANTXIP_FAMILY1_BANK',pal_package(1,guantxip['family'][1]))
    dummy=dict.fromkeys(('ui_family_banks','ui_power_on','ui_occ_patch','pose_offsets','pose_data','hud_names','life_names'),0x1100)
    gx_family=(gfx['GUANTXIP_FAMILY0_BANK'][0],gfx['GUANTXIP_FAMILY1_BANK'][0])
    place('GUANTXIP_SET_BANK',set_package(guantxip,dummy,gx_family))
    place('DIHALT_SET_BANK',set_package(dihalt,dummy,(0,0)))
    (B/'gfx-sets.inc').write_text(''.join(f'{k} equ {v[0]}\n' for k,v in gfx.items()))
    controls=(R/'V9990/src/port_presentation.asm').read_text().split('control:\n',1)[1].split('title_show:',1)[0]
    (B/'opening-control.inc').write_text('control:\n'+controls.replace('control_release:\n','control_release:\n    call opening_secret\n'))
    (B/'smooth-config.inc').write_text(f'SMOOTH_BANK equ {8+len(banks)}\n')
    if PRE:
        (B/'sfx-table.inc').write_text((PRE/'sfx-table.inc').read_text())
        POOLS=((0x9E23+3,0xA201),(0xA310,0xA777))
        sfx_pools=[(p,(PRE/f'sfx-runs-{n}.bin').read_bytes()) for n,p in enumerate(POOLS)]
    else:sfx_pools=compile_effects()
    asm('port_sfx')
    for name in ('port_topo','port_ui','port_menu','port_presentation','port_slots','port_bridge','port_trampoline','port_restore','port_runtime','port_preload','port_boot'):
        asm(name)
        if name=='port_ui':
            listing=(B/'port_ui.lst').read_text()
            (B/'ui-api.inc').write_text(f'UI_BYTES equ {len((B/"port_ui.bin").read_bytes())}\n')
            set_addr={k:int(re.search(r'00:0000([0-9A-F]{4})\s+(?:X\s+)?'+k+r'\s*$',listing,re.M)[1],16) for k in ('ui_family_banks','ui_power_on','ui_occ_patch')}
            audio_api=[]
            for label in ('music_active','music_bank','music_ptr','music_shadow'):
                address=int(re.search(r'00:0000([0-9A-F]{4})\s+(?:X\s+)?shared_'+label+r'\s*$',listing,re.M)[1],16)
                audio_api.append(f'{label} equ ${address:04X}')
            (B/'ui-audio-api.inc').write_text('\n'.join(audio_api)+'\n')
        if name=='port_runtime':
            listing=(B/'port_runtime.lst').read_text();api=[]
            for label in ('pose_offsets','pose_data','hud_names','life_names'):
                set_addr[label]=int(re.search(r'00:0000([0-9A-F]{4})\s+(?:X\s+)?'+label+r'\s*$',listing,re.M)[1],16)
            for name,st,fam in (('GUANTXIP_SET_BANK',guantxip,gx_family),('DIHALT_SET_BANK',dihalt,(0,0))):
                first,count=gfx[name];blobs=set_package(st,set_addr,fam);assert len(blobs)==count
                banks[first-8:first-8+count]=blobs
            for label in ('reg_write','set_write','sprite_page','scroll_x','scroll_y','piece_count','audio_clock','vblank','command','pattern_slot','wait_command','clear_ui','display_off','display_on'):
                addr=int(re.search(r'00:0000([0-9A-F]{4})\s+(?:X\s+)?'+label+r'\s*$',listing,re.M)[1],16)
                api.append(f'{label} equ ${addr:04X}')
            (B/'smooth-api.inc').write_text('\n'.join(api)+'\n')
            asm('port_smooth')
            helper_listing=(B/'port_smooth.lst').read_text()
            gen=int(re.search(r'00:0000([0-9A-F]{4})\s+(?:X\s+)?generation\s*$',helper_listing,re.M)[1],16)
            contact_api='    include "../build/smooth-api.inc"\n'+f'GENERATION equ ${gen:04X}\n'
            for label in ('offset_x','offset_y','phase','hardware_count','front_count'):
                addr=int(re.search(r'00:0000([0-9A-F]{4})\s+(?:X\s+)?'+label+r'\s*$',helper_listing,re.M)[1],16)
                contact_api+=(f'SCROLL_PHASE equ ${addr:04X}\n' if label=='phase' else (f'GPU_{label.upper()} equ ${addr:04X}\n' if label.endswith('_count') else f'SCROLL_HALF_{label[-1].upper()} equ ${addr:04X}\n'))
            mid=int(re.search(r'00:0000([0-9A-F]{4})\s+(?:X\s+)?compose_sat\s*$',helper_listing,re.M)[1],16)
            contact_api+=f'STAGE_MID_SAT equ ${mid:04X}\n'
            (B/'contacts-api.inc').write_text(contact_api)
            asm('port_contacts')
            banks.append(((B/'port_smooth.bin').read_bytes()+(B/'port_contacts.bin').read_bytes()+(B/'port_sfx.bin').read_bytes()).ljust(16384,b'\xff'))
    # Fixed jump table makes patch sites reviewable and independent of code size.
    game=bytearray(raw)
    def patch(addr,expected,new):
        assert expected==bytes.fromhex(contracts['game'][f'{addr:04X}']),hex(addr)
        off=addr-0x1060;assert game[off:off+len(expected)]==expected,hex(addr);game[off:off+len(new)]=new
    hooks=[(0x1060,0),(0x5C7D,1),(0x55A1,2),(0x5B7D,3),(0x58DA,4),(0x58E8,5),(0x5B02,6),(0x5B3F,7),(0x416D,8),(0x41D7,9),(0x9DD4,10),(0x9DEF,11),(0xA201,13),(0x6062,14),(0x578C,15)]
    for addr,index in hooks:patch(addr,mem[addr:addr+3],b'\xc3'+struct.pack('<H',0x1100+3*index))
    patch(0x38CD,bytes.fromhex('cd593b'),b'\xcd'+struct.pack('<H',0x1136))
    for addr,expected,target,opcode in (
        (0x6471,'21b83f',0x069B,0xC3),
        (0x64B7,'2ac864',0x069E,0xC3),
        (0x64BC,'712373',0x06A1,0xC3),
        (0x64AF,'edb8e1',0x06A4,0xC3),
        (0x64F5,'c4a155',0x06A7,0xC4),
        (0x3886,'cde438',0x06AA,0xCD),
        (0x43C7,'cd0e58',0x06AD,0xC3),
        (0x384B,'cd2042',0x06B0,0xCD),
        (0x3BCE,'cda155',0x06B3,0xCD),
    ):patch(addr,bytes.fromhex(expected),bytes([opcode])+struct.pack('<H',target))

    for addr,target in ((0x398D,0xE000),(0x3997,0xE003),(0x4D8F,0x06BF),(0x4E08,0x06BF),(0x4BC7,0xE030),(0x4D04,0xE033),(0x5131,0xE039)):
        patch(addr,mem[addr:addr+3],b'\xcd'+struct.pack('<H',target))
    for addr,target in ((0x3A73,0x06C2),(0x4DE5,0xE006),(0x4D69,0xE009),(0x5272,0x06CB),(0x4F44,0xE00C),(0x4E9F,0xE00F),(0x556A,0xE012),(0x412B,0xE021)):
        patch(addr,mem[addr:addr+3],b'\xc3'+struct.pack('<H',target))
    patch(0x3855,bytes.fromhex('cddea8'),bytes(3))  # retired mirror table overlaps terrain alias caches
    patch(0x5335,bytes.fromhex('ed5b933eed4b953e3e00'),bytes.fromhex('cd24e0')+bytes(7))
    patch(0x37E9,bytes.fromhex('cde861'),bytes(3))
    patch(0x43C4,bytes.fromhex('c3c743'),b'\xc3'+struct.pack('<H',0x1133))
    patch(0x3808,bytes.fromhex('dd215067'),b'\xc3'+struct.pack('<H',0x1130)+b'\x00')
    patch(0x557F,bytes.fromhex('cd239e'),b'\xcd'+struct.pack('<H',0x1100+3*12))
    for addr in (0x3838,0x546F):patch(addr,mem[addr:addr+3],bytes(3))
    patch(0xB6DF,bytes.fromhex('cdef9d'),bytes.fromhex('fb0000'))
    patch(0x53CC,bytes.fromhex('c3d253'),bytes.fromhex('c336e0'))
    patch(0x4911,bytes.fromhex('cdd253'),bytes.fromhex('cd36e0'))
    patch(0x9E04,bytes.fromhex('f5d511'),bytes.fromhex('c303ce'))
    patch(0x9E23,bytes.fromhex('f50603'),bytes.fromhex('c300ce'))
    for (start,end),data in sfx_pools:
        off=start-0x1060
        assert game[off:off+len(data)]==raw[off:off+len(data)], 'SFX storage overlaps another patch'
        assert len(data)==end-start
        game[off:off+len(data)]=data
    for addr in (0x6711,0xA8DE):patch(addr,mem[addr:addr+1],b'\xc9')
    for addr,data in zip((0x67CB,0x800B),cpu_tiles):game[addr-0x1060:addr-0x1060+len(data)]=data
    runtime=(B/'port_runtime.bin').read_bytes();assert len(runtime)<=0x3765-0x1100
    game[0x1100-0x1060:0x1100-0x1060+len(runtime)]=runtime
    rom=bytearray((B/'port_boot.bin').read_bytes());assert len(rom)==16384
    for name in ('opening','intro','stage'):
        blob=bytearray((R/f'MSX/build/{name}.bin').read_bytes())
        expected_hash={'opening':'609c540e82fe09bae034e481e94ae4519b782cb1164e32daaaa8e98db051750d','intro':'467b04f89c3adbe13cc9cbca3e72d2b35a76d518599ec1147469265cab3e092a','stage':'8bc0336ef8f7a72b655089abcd06555af5cbd2e2ea083abc885fd9c111315f36'}[name]
        assert hashlib.sha256(blob).hexdigest()==expected_hash, name+' presentation patch source changed'
        base=0x1000 if name=='stage' else 0x88B8
        def edit(addr,old,new):
            off=addr-base;assert blob[off:off+len(old)]==old,(name,hex(addr))
            assert len(old)==len(new);blob[off:off+len(old)]=new
        if name=='intro':blob=bytearray((B/'port_topo.bin').read_bytes()).ljust(len(blob),b'\0')
        if name=='opening':
            edit(0xA581,bytes.fromhex('f32100'),bytes.fromhex('c38006'))
            edit(0xA596,bytes.fromhex('c3b8a3'),bytes.fromhex('c38006'))
        if name=='stage':
            menu=(B/'port_menu.bin').read_bytes();assert len(menu)<=0x2F1D-0x2B6A
            ui=(B/'port_ui.bin').read_bytes();assert len(ui)<=2048
            blob[0x2B6A-0x1000:0x2F1D-0x1000]=menu.ljust(0x2F1D-0x2B6A,b'\0')
            blob[0x1800-0x1000:0x1800-0x1000+len(ui)]=ui
            edit(0x1060,bytes.fromhex('c3c216'),bytes.fromhex('c36a2b'))
            edit(0x1692,bytes.fromhex('f3f5db'),bytes.fromhex('c30ce8'))
        rom+=blob.ljust(16384,b'\xff')
    rom+=game[:20000].ljust(32768,b'\xff')+game[20000:].ljust(32768,b'\xff')+b''.join(banks)
    size=1
    while size<len(rom):size*=2
    rom=bytearray(rom.ljust(size,b'\xff'))
    # openMSX/BlueMSX guess the mapper from LD (nn),A bytes. Make ASCII16 win
    # clearly (>=4 over Konami and ASCII8) with filler in the unused last bank.
    def votes(d):
        c=dict(K=0,S=0,A8=0,A16=0)
        for i in range(len(d)-2):
            if d[i]==0x32:
                v=d[i+1]|d[i+2]<<8
                if v in (0x4000,0x8000,0xA000):c['K']+=1
                elif v in (0x5000,0x9000,0xB000):c['S']+=1
                elif v==0x6000:c['K']+=1;c['A8']+=1;c['A16']+=1
                elif v in (0x6800,0x7800):c['A8']+=1
                elif v==0x7000:c['S']+=1;c['A8']+=1;c['A16']+=1
                elif v==0x77FF:c['A16']+=1
        c['A8']-=1;return c
    c=votes(rom);n7000=max(0,c['K']+4-c['A16']);filler=b'\x32\x00\x70'*n7000+b'\x32\xFF\x77'*4
    assert rom[-len(filler)-16:]==b'\xff'*(len(filler)+16),'last bank must be unused for the mapper filler'
    rom[-len(filler)-16:-16]=filler
    c=votes(rom);assert c['A16']>=max(c['K'],c['S'],c['A8'])+4,c
    rom_tmp=B/'madmix2-v99990.rom.tmp'
    rom_tmp.write_bytes(rom)
    rom_tmp.replace(B/'madmix2-v99990.rom')
    (B/'port-build.json').write_text(json.dumps(dict(bytes=len(rom),resident_bytes=len(runtime),master_patterns=len(unique),maps=9,hooks=[hex(a) for a,i in hooks]),indent=2)+'\n')
    print('Native P1 ROM:',len(rom),'bytes; runtime',len(runtime),'bytes')
if __name__=='__main__':main()
