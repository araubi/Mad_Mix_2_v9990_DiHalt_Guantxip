#!/usr/bin/env python3
"""Guantxip's stage drawings -> his corrected maps for the Guantxip set.

Guantxip drew the nine stages (assets-guantxip/original/faseN.png) fixing some
wall tiles of Topo's maps, sometimes with tiles that the original does not
have. This renders each original map (assets/maps) with the Guantxip tiles,
finds where his drawing is placed, and for every 32x16 cell that differs looks
for the tile that matches his drawing exactly. The change is kept only if the
tile keeps the original collision class (TABLA_CLASES of the game, 3AECh), so
the game plays the same with either set. Writes assets-guantxip/maps/stageN.tmx
(editable in Tiled, used only by the Guantxip set) and prints what was left
out. Run after import_guantxip.py.
"""
import json,re,sys
from pathlib import Path
import numpy as np
from PIL import Image
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[1]
CLASSES=[1,2]+[0]*30+[3,4,5,5,5,5,6,6,6,7,9,1,8,1,1,0,0,0,0,0,0,10]   # 54 tiles
def cls(t):return CLASSES[t] if t<len(CLASSES) else None
# Family 0 has no free wall slot left, so tile 30 (same Guantxip picture as 27,
# used twice) becomes 27 and slot 30 carries his tile 14 variant without the
# block corner (baldosas-mapa.json), used where 14 lies under the big wall
# 16,17: drawn so in his fase2.png (11-11-2026) and applied the same in fase 3.
REMAP={0:{30:27}}
CONTEXT={0:[(14,(16,17),30)]}   # tile, (tile above, tile above-right), variant
def main():
    out=R/'assets-guantxip/maps';out.mkdir(exist_ok=True);report=[]
    for i in range(1,10):
        text=(R/f'assets/maps/stage{i}.tmx').read_text()
        m=ET.fromstring(text);w=int(m.get('width'));h=int(m.get('height'))
        fam=0 if 'family0' in m.find('tileset').get('source') else 1
        cells=[int(v)-1 for v in m.find('layer/data').text.replace('\n','').split(',') if v.strip()]
        ts=np.asarray(Image.open(R/f'assets-guantxip/tiles/family{fam}.png').convert('RGB')).astype(int)
        tiles=[ts[(t//8)*16:(t//8)*16+16,(t%8)*32:(t%8)*32+32] for t in range(56)]
        world=np.zeros((h*16,w*32,3),int)
        for k,t in enumerate(cells):world[(k//w)*16:(k//w)*16+16,(k%w)*32:(k%w)*32+32]=tiles[t]
        ref=np.asarray(Image.open(R/f'assets-guantxip/original/fase{i}.png').convert('RGB')).astype(int)
        best=max((((np.abs(world[oy:oy+ref.shape[0],ox:ox+ref.shape[1]]-ref).sum(axis=2)<30).mean(),ox,oy)
                  for oy in range(0,h*16-ref.shape[0]+1,16) for ox in range(0,w*32-ref.shape[1]+1,32)))
        _,ox,oy=best;new=[REMAP.get(fam,{}).get(t,t) for t in cells]
        for k,(t,n) in enumerate(zip(cells,new)):
            if t!=n:report.append(f'fase {i} ({k%w},{k//w}): {t}->{n} (misma imagen)')
        for cy in range(ref.shape[0]//16):
            for cx in range(ref.shape[1]//32):
                mx=ox//32+cx;my=oy//16+cy;t=new[my*w+mx]
                r=ref[cy*16:cy*16+16,cx*32:cx*32+32]
                diff=lambda k:int((np.abs(tiles[k]-r).sum(axis=2)>30).sum())
                if diff(t)<=16:continue          # dots and small marks drawn on his pictures
                d,k=min((diff(k),k) for k in range(56))
                if d>4 or k==t:continue           # sprites or objects drawn on the picture
                if cls(k)!=cls(t):report.append(f'fase {i} ({mx},{my}): {t}->{k} omitido (cambia la clase {cls(t)}->{cls(k)})');continue
                new[my*w+mx]=k;report.append(f'fase {i} ({mx},{my}): {t}->{k}')
        for t,(up,upr),v in CONTEXT.get(fam,[]):
            for k in range(w,len(new)):
                if new[k]==t and k%w+1<w and new[k-w]==up and new[k-w+1]==upr:
                    assert cls(v)==cls(t);new[k]=v;report.append(f'fase {i} ({k%w},{k//w}): {t}->{v} (bajo el muro grande)')
        rows=[','.join(str(v+1) for v in new[y*w:(y+1)*w]) for y in range(h)]
        csv='\n'+',\n'.join(rows)+'\n'
        text=re.sub(r'(<data encoding="csv">).*?(</data>)',lambda g:g.group(1)+csv+'    '+g.group(2),text,flags=re.S)
        text=text.replace('source="../tiles/','source="../../assets/tiles/')
        (out/f'stage{i}.tmx').write_text(text)
    (R/'assets-guantxip/maps/cambios.txt').write_text('Cambios de los mapas de Guantxip respecto a los de Topo (tools/compara_fases.py)\n'+'\n'.join(report)+'\n')
    print('\n'.join(report))
if __name__=='__main__':main()
