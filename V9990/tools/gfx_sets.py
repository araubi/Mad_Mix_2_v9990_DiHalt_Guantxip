"""Compile one graphics set (HUD + font, terrain, sprites, palette) for the P1 port.

The DiHalt set is read with the original strict 64-colour checks
(palette64.local_image / sprite_images). The Guantxip set
(V9990/assets-guantxip, made by import_guantxip.py) keeps a separate 16-colour
palette per terrain family, so it is read as plain indexed PNGs (index & 15).
Both produce exactly the same kinds of blobs, so the cartridge can stream
either one into VRAM/RAM at game start.
"""
import json,struct,xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from palette64 import local_image,sprite_images
import analyze_trace

def pat8(tiles):
    data=bytearray(((len(tiles)+31)//32)*1024)
    for i,t in enumerate(tiles):
        for y in range(8):
            for x in range(0,8,2): data[(i//32)*1024+(i%32)*4+y*128+x//2]=(t[y*8+x]<<4)|t[y*8+x+1]
    return data

def _plain(path,size=None):
    im=Image.open(path);assert im.mode=='P',path
    if size:assert im.size==size,(path,im.size)
    out=Image.frombytes('P',im.size,bytes(v&15 for v in im.tobytes()));return out

def _guantxip_sprites(A):
    meta=json.loads((A/'sprites/sprites.json').read_text());sheet=Image.open(A/'sprites'/meta['image'])
    assert sheet.mode=='P' and sheet.size==(256,448) and [r['id'] for r in meta['poses']]==list(range(105))
    images=[]
    for r in meta['poses']:
        im=sheet.crop((r['x'],r['y'],r['x']+r['width'],r['y']+r['height']));bank=r['palette_bank']
        assert all(v==0 or v//16==bank for v in im.tobytes()),r['id']
        o=Image.frombytes('P',im.size,bytes(v&15 for v in im.tobytes()));o.info['palette_bank']=bank;images.append(o)
    return images

def compile_set(A,config,guantxip=False):
    """Returns a dict of blobs. A = asset root, config = palette-config.json."""
    A=Path(A)
    if guantxip:
        load=lambda path,size,bank:_plain(path,size)
    else:
        def load(path,size,bank):
            im=local_image(path,bank,A)
            if size:assert im.size==size,(path,size)
            return im
    patterns=[bytes(64),bytes([1])*64]
    im=load(A/'font.png' if (A/'font.png').exists() else A.parent/'assets/font.png',(128,48),config['hud_bank'])
    styles=json.loads((A/'font-styles.json').read_text())['styles']
    assert len(styles)==9 and all(len(s)==8 and all(isinstance(v,int) and 0<=v<=255 for v in s) for s in styles)
    assert set(im.tobytes())<={1,2}
    for style in range(9):
        for c in range(96):
            mask=im.crop(((c%16)*8,(c//16)*8,(c%16)*8+8,(c//16)*8+8)).tobytes()
            patterns.append(bytes((styles[style][y] & 15) if mask[y*8+x]==2 else (styles[style][y]>>4) for y in range(8) for x in range(8)))
    index={t:i for i,t in enumerate(patterns)}
    def tile_id(t):
        if t not in index:index[t]=len(patterns);patterns.append(t)
        return index[t]
    if guantxip:
        hud=_plain(A/'hud.png',(256,192))
    else:
        composition=ET.parse(A/'hud.tmx').getroot()
        assert (composition.get('width'),composition.get('height'))==('32','24')
        ref=composition.find('tileset');assert ref.get('firstgid')=='1'
        tsx=A/ref.get('source');ts=ET.parse(tsx).getroot()
        atlas=load(tsx.parent/ts.find('image').get('source'),(256,192),config['hud_bank'])
        gids=[int(v) for v in composition.find('layer/data').text.split(',') if v.strip()]
        assert len(gids)==768 and all(0<=v<=768 for v in gids)
        hud=Image.new('P',(256,192));hud.putpalette(atlas.getpalette())
        for i,gid in enumerate(gids):
            if gid:
                n=gid-1;x=(n%32)*8;y=(n//32)*8
                hud.paste(atlas.crop((x,y,x+8,y+8)),((i%32)*8,(i//32)*8))
    for y in range(192):
        for x in range(256):
            if not (32<=x<224 and 16<=y<160):assert hud.getpixel((x,y))!=0, 'HUD must remain opaque outside playfield'
    names=[]
    for y in range(24):
        for x in range(32):names.append(tile_id(hud.crop((x*8,y*8,x*8+8,y*8+8)).tobytes()))
    life_im=load(A/'life.png',(24,24),config['hud_bank'])
    life=[tile_id(life_im.crop((x*8,y*8,x*8+8,y*8+8)).tobytes()) for y in range(3) for x in range(3)]
    tiles=[];cpu_tiles=[]
    for fam in range(2):
        if guantxip:
            im=_plain(A/f'tiles/family{fam}.png',(256,112));occupancy=(A.parent/f'assets/tiles/family{fam}-occupancy.dat').read_bytes()
        else:
            ts=ET.parse(A/f'tiles/family{fam}.tsx').getroot();im=load(A/'tiles'/ts.find('image').get('source'),(256,112),config['terrain_bank'])
            occupancy=(A/f'tiles/family{fam}-occupancy.dat').read_bytes()
        assert len(occupancy)==3584
        if guantxip:   # Guantxip's new tiles take the mask of the Topo tile they replace
            occupancy=bytearray(occupancy)
            for t,src in json.loads((A/'baldosas-mapa.json').read_text())['ocupacion'][f'family{fam}'].items():
                occupancy[int(t)*64:int(t)*64+64]=occupancy[src*64:src*64+64]
            occupancy=bytes(occupancy)
        cpu_tiles.append(occupancy)
        for t in range(56):
            for sy in range(2):
                for sx in range(4):
                    x=(t%8)*32+sx*8;y=(t//8)*16+sy*8
                    tiles.append(im.crop((x,y,x+8,y+8)).tobytes())
    maps=bytearray(9*4096)      # Guantxip: his corrected maps (tools/compara_fases.py)
    for i in range(9):
        m=ET.parse(A/f'maps/stage{i+1}.tmx').getroot();data=m.find('layer/data');assert data.get('encoding')=='csv'
        cells=[int(v.strip())-1 for v in data.text.split(',') if v.strip()]
        assert len(cells)==64*int(m.get('height')) and len(cells)<=3584 and all(0<=v<56 for v in cells)
        maps[i*4096:i*4096+len(cells)]=bytes(cells)
    analyze_trace.PIECE_CACHE.clear()
    sprites=_guantxip_sprites(A) if guantxip else analyze_trace.load_sprites(A)
    unique=[];lookup={};descs=bytearray();offsets=[];seen={}
    def compile_pose(sid,variant,sprites):
        x=68 if variant==1 else 64
        pieces=analyze_trace.sprite_pieces(dict(a=sid|(128 if variant else 0),d=32,e=x),sprites)
        d=bytearray((len(pieces),))
        for p in pieces:
            pix=bytes(p['pixels'])
            if pix not in lookup:lookup[pix]=len(unique);unique.append(pix)
            n=lookup[pix]
            d += struct.pack('<bbHHB',p['x']-x,p['y']-32,(n%16)*16,512+(n//16)*16,32+64*p['bank'])
        d=bytes(d)
        if d not in seen or not guantxip:seen[d]=len(descs);descs.extend(d)   # Guantxip: identical poses share one descriptor (DiHalt layout kept as v1.0)
        return seen[d]
    for variant in range(3):
        for sid in range(105):offsets.append(compile_pose(sid,variant,sprites))
    # Guantxip: red Pac bodies while the big-ball power lasts (port_ui ui_power).
    power_ids=[0,1,2,3,4,5,25,26];power_offsets=[offsets[v*105+i] for v in range(3) for i in power_ids]
    if guantxip and (A/'sprites/power.png').exists():
        pm=json.loads((A/'sprites/sprites.json').read_text())['power'];assert pm['poses']==power_ids
        strip=Image.open(A/'sprites'/pm['image']);red=list(sprites)
        for k,sid in enumerate(power_ids):
            im=strip.crop((24*k,0,24*k+24,24));assert all(v==0 or v//16==1 for v in im.tobytes()),sid
            o=Image.frombytes('P',im.size,bytes(v&15 for v in im.tobytes()));o.info['palette_bank']=1;red[sid]=o
        analyze_trace.PIECE_CACHE.clear()
        power_offsets=[compile_pose(i,v,red) for v in range(3) for i in power_ids]
    analyze_trace.PIECE_CACHE.clear()
    master=bytearray(((len(unique)+15)//16)*2048)
    for i,t in enumerate(unique):
        for y in range(16):
            for x in range(0,16,2): master[(i//16)*2048+(i%16)*8+y*128+x//2]=(t[y*16+x]<<4)|t[y*16+x+1]
    assert len(master)<0x10000
    pj=json.loads((A/'palettes.json').read_text())
    pal=bytes(c for bank in pj['banks'] for rgb in bank for c in rgb)
    family=None
    if 'terrain_family1' in pj:
        f1=bytes(c for rgb in pj['terrain_family1'] for c in rgb)
        family=(pal[3:48],f1[3:48])      # entries 1..15 of bank 0; entry 0 = backdrop
    assert len(pat8(patterns))<=0x10000
    return dict(patterns=pat8(patterns),hud_names=struct.pack('<768H',*names),life_names=struct.pack('<9H',*life),
                tiles=pat8(tiles),cpu_tiles=cpu_tiles,maps=bytes(maps),master=bytes(master),descs=bytes(descs),
                offsets=b''.join(struct.pack('<H',x) for x in offsets),
                power=bytes((int(guantxip),))+struct.pack('<24H',*power_offsets),palette=pal,family=family,
                master_patterns=len(unique))

class Package:
    """Records for port_ui's ui_stream. Never lets a record cross a 16 KB bank."""
    def __init__(self):self.banks=[bytearray()]
    def _room(self,n):
        if len(self.banks[-1])+n+1>16384:     # +1: room for the FF/00 marker
            self.banks[-1].append(0xFF);self.banks.append(bytearray())
    def vram(self,addr,data,chunk=2048):
        for off in range(0,len(data),chunk):
            part=data[off:off+chunk];a=addr+off;self._room(6+len(part))
            self.banks[-1]+=bytes((1,a&255,(a>>8)&255,a>>16))+struct.pack('<H',len(part))+part
    def ram(self,addr,data,chunk=2048):
        for off in range(0,len(data),chunk):
            part=data[off:off+chunk];self._room(5+len(part))
            self.banks[-1]+=bytes((2,))+struct.pack('<HH',addr+off,len(part))+part
    def palette(self,entry,data):
        self._room(4+len(data));self.banks[-1]+=bytes((3,entry*4))+struct.pack('<H',len(data))+data
    def blobs(self):
        out=[bytes(b) for b in self.banks];out[-1]+=b'\0'
        return [b.ljust(16384,b'\xff') for b in out]
