#!/usr/bin/env python3
"""Guantxip's V9990 graphics set -> editable assets in the port's own layout.

Reads the artist's sheets in V9990/assets-guantxip/original/ (as delivered:
two tile sheets with their own 16-colour palettes, two sprite sheets with
palettes 3 and 4, and the HUD window) plus two hand-checked maps:
  baldosas-mapa.json  port tile id (original Topo order) -> sheet cell
  figuras-mapa.json   port pose id (0..104) -> sheet + position
and writes, next to them:
  tiles/family0.png, tiles/family1.png   56 tiles of 32x16, port order
  sprites/sprites.png + sprites.json     105 poses, 64-colour table
  hud.png, life.png                      HUD bank (bank 2)
  palettes.json                          four banks + family-1 terrain bank
  font-styles.json                       DiHalt's score/text styles remapped

V9990 P1 always treats pixel 0 as transparent. Guantxip's terrain uses all
sixteen colours, so terrain black becomes pixel 0: plane B is the back layer
and the backdrop (R#15 = palette entry 0) is black, so it looks the same.
Guantxip's light-blue entry 0 moves to entry 15. Sprite black is moved to
entry 1 of the sprite bank, which is also the 1-pixel "detail" colour.
"""
from pathlib import Path
import json,sys
from PIL import Image
R=Path(__file__).resolve().parents[2]
G=R/'V9990/assets-guantxip';O=G/'original';D=R/'V9990/assets'
def rgb5(c):return [round(v*31/255) for v in c]
def pal16(im):p=im.getpalette();return [tuple(p[i*3:i*3+3]) for i in range(16)]

def tiles():
    m=json.loads((G/'baldosas-mapa.json').read_text())
    banks=[]
    for fam,name in ((0,'baldosas_familia0_paleta1.png'),(1,'baldosas_familia1_paleta2.png')):
        src=Image.open(O/name);assert src.mode=='P' and src.size==(256,212)
        p=pal16(src);assert p[15]==(0,0,0),'Guantxip black expected at entry 15'
        remap=[15 if i==0 else 0 if i==15 else i for i in range(16)]
        colors=[p[remap.index(i)] for i in range(16)]   # new index -> rgb
        out=Image.new('P',(256,112));out.putpalette([v for c in colors for v in c]+[0]*720)
        cells=m[f'family{fam}']
        for t in range(56):
            x,y=cells[str(t)];cell=src.crop((x,y,x+32,y+16))
            cell=Image.frombytes('P',(32,16),bytes(remap[v] for v in cell.tobytes()));cell.putpalette(out.getpalette())
            out.paste(cell,((t%8)*32,(t//8)*16))
        (G/'tiles').mkdir(exist_ok=True);out.save(G/f'tiles/family{fam}.png')
        banks.append(colors)
    return banks

def sprites():
    m=json.loads((G/'figuras-mapa.json').read_text())['poses']
    meta=json.loads((D/'sprites/sprites.json').read_text())
    s3=Image.open(O/'sprites_paleta3.png');s4=Image.open(O/'sprites_paleta4.png')
    p3=pal16(s3);p4=pal16(s4)
    assert p3[15]==(0,0,0)
    order3=[0,15]+[i for i in range(1,15)]               # new index -> old index
    bank1=[p3[i] for i in order3];inv3={old:new for new,old in enumerate(order3)}
    bank3=p4
    sheet=Image.new('P',(256,448));poses=[]
    fallback={5:{1:7,2:15},20:{1:15,2:0},88:{1:14,2:15},90:{1:14,2:15}}  # mono 1/2 -> palette-3 index
    for row in meta['poses']:
        i=row['id'];w,h=row['width'],row['height'];spec=m[str(i)]
        if spec is None:
            mono=Image.open(D/f'sprites/{i:03d}.png');assert mono.size==(w,h)
            mono=mono.tobytes()
            # Topo's 1-pixel white halo (mask) is not part of Guantxip's style.
            halo=lambda k:mono[k]==1 and any(not(0<=xx<w and 0<=yy<h) or mono[yy*w+xx]==0 for xx,yy in ((k%w-1,k//w),(k%w+1,k//w),(k%w,k//w-1),(k%w,k//w+1)))
            px=[inv3[fallback[i][v]] if v and not (i==5 and halo(k)) else 0 for k,v in enumerate(mono)];bank=1
        else:
            n,x,y=spec[:3];maxy=spec[3] if len(spec)>3 else 999
            src=s3 if n==3 else s4
            cell=src.crop((x,y,x+w,y+h)).tobytes()
            px=[0 if (y+k//w)>=maxy else v for k,v in enumerate(cell)]
            if n==3:px=[inv3[v] if v else 0 for v in px];bank=1
            else:bank=3
        im=Image.frombytes('P',(w,h),bytes(bank*16+v if v else 0 for v in px))
        sheet.paste(im,(row['x'],row['y']))
        poses.append(dict(row,palette_bank=bank,source=(f'guantxip paleta {spec[0]} x={spec[1]} y={spec[2]}' if spec else 'original Topo (sin dibujo de Guantxip)')))
    return sheet,bank1,bank3,dict(meta,poses=poses)

def hud(bank1):
    src=Image.open(O/'ventana.png').convert('RGB').crop((0,0,256,192))
    life_src=None
    cols=[];MAG=(255,0,238)
    for c in src.getdata():
        if c!=MAG and c not in cols:cols.append(c)
    # Life icon: Guantxip's pose-0 face, in the HUD bank.
    s3=Image.open(O/'sprites_paleta3.png').convert('RGB');face=s3.crop((0,0,24,24))
    for c in face.getdata():
        if c!=(255,0,255) and c not in cols:cols.append(c)
    # DiHalt score/text styles: keep their colours when there is room.
    dpal=[tuple(round(v*255/31) for v in c) for c in json.loads((D/'palettes.json').read_text())['banks'][2]]
    styles=json.loads((D/'font-styles.json').read_text())
    used=[];[used.append(v) for s in styles['styles'] for b in s for v in (b>>4,b&15) if v not in used]
    def dist(a,b):return sum((x-y)**2 for x,y in zip(a,b))
    extra=sorted(used,key=lambda i:-min(dist(dpal[i],c) for c in cols))
    for i in extra:
        if len(cols)>=15:break
        if min(dist(dpal[i],c) for c in cols)>40*40:cols.append(dpal[i])
    assert len(cols)<=15,len(cols)
    bank2=[(0,0,0)]+cols+[(0,0,0)]*(15-len(cols))
    idx={c:i for i,c in enumerate(bank2) if i}
    def near(c):return min(range(1,16),key=lambda i:dist(bank2[i],c))
    h=Image.frombytes('P',(256,192),bytes(0 if c==MAG else 32+idx[c] for c in src.getdata()))
    for y in range(192):
        for x in range(256):
            if not(32<=x<224 and 16<=y<160):assert h.getpixel((x,y))!=0,'HUD must be opaque outside the window'
    life=Image.frombytes('P',(24,24),bytes(0 if c==(255,0,255) else 32+idx[c] for c in face.getdata()))
    newstyles=[[near(dpal[b>>4])*16+near(dpal[b&15]) for b in s] for s in styles['styles']]
    return h,life,bank2,dict(styles,styles=newstyles,description=styles['description']+' Remapped by import_guantxip.py to the Guantxip HUD bank.')

def main():
    t0,t1=tiles();sheet,b1,b3,meta=sprites();h,life,b2,styles=hud(b1)
    banks=[t0,b1,b2,b3]
    table=[v for b in banks for c in b for v in c]+[0]*576
    for im,path in ((sheet,'sprites/sprites.png'),(h,'hud.png'),(life,'life.png')):
        im.putpalette(table);(G/path).parent.mkdir(exist_ok=True);im.save(G/path,transparency=bytes(0 if i%16==0 else 255 for i in range(256)))
    (G/'sprites/sprites.json').write_text(json.dumps(meta,indent=2)+'\n')
    (G/'font-styles.json').write_text(json.dumps(styles,indent=2)+'\n')
    (G/'palettes.json').write_text(json.dumps({'description':'Guantxip V9990 set. Bank 0 terrain (family 0: stages 1-3 and 7-9), bank 1 sprites (paleta 3), bank 2 HUD, bank 3 sprites (paleta 4). terrain_family1 replaces bank 0 on stages 4-6. RGB5 0..31.',
        'banks':[[rgb5(c) for c in b] for b in banks],'terrain_family1':[rgb5(c) for c in t1]},indent=1)+'\n')
    print('Guantxip assets written to',G)
if __name__=='__main__':main()
