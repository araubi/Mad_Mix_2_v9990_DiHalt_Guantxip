"""Compile editable large letters and V9990 GPU-copy streams for credits/menu."""
import json,struct
from PIL import Image
from palette64 import local_image

def compile_ui(A,B,config):
 im=local_image(A/'font-large.png',config['hud_bank'],A)
 assert im.size==(256,64) and set(im.tobytes())<={1,2}
 # The font has no '<': mirror '>' into its cell for the graphics-set row.
 lt,gt=ord('<')-32,ord('>')-32
 cell=lambda n:((n%16)*16,(n//16)*16,(n%16)*16+16,(n//16)*16+16)
 if set(im.crop(cell(lt)).tobytes())<={1}:im.paste(im.crop(cell(gt)).transpose(Image.Transpose.FLIP_LEFT_RIGHT),cell(lt)[:2])
 styles=json.loads((A/'font-large-styles.json').read_text())
 raw=bytearray(16384)
 for style,name in enumerate(('selected','unselected')):
  colors=styles[name];assert len(colors)==16
  for y in range(64):
   for x in range(0,256,2):
    pair=[(colors[y%16]&15) if im.getpixel((xx,y))==2 else (colors[y%16]>>4) for xx in (x,x+1)]
    raw[(style*64+y)*128+x//2]=(pair[0]<<4)|pair[1]
 def packet(sx,sy,dx,dy,w,h):return struct.pack('<BHBBBB',sx,sy,dx,dy,w,h)
 def output(name,data):
  (B/f'ui-{name}.inc').write_text('    db '+','.join(str(v) for v in data+b'\xff')+'\n')
 credits=bytearray()
 for text,y,color in [('PROGRAMA',8,0x38),('RAFAYO GOMEZ',9,0x78),('GRAFICOS',11,0x20),('ACE',12,0x60),('MUSICA',14,0x18),('TPM',15,0x58),('V9990 VERSION',17,0x38),('DIHALT STUDIO 2026',18,0x78),('GRAFICOS V9990',20,0x20),('GUANTXIP',21,0x60)]:
  x=(32-len(text))//2
  for i,c in enumerate(text):
   n=2+((color&0x38)>>3)*96+ord(c)-32
   credits+=packet((n%32)*8,(n//32)*8,(x+i)*8,y*8,8,8)
 output('credits',credits)
 # Menu: four rows (difficulty, graphics set, cursor-up direction, CPU). port_ui
 # draws them at run time from these strings: y, x, length, characters.
 menu=json.loads((A/'menu.json').read_text());assert menu['default']==0 and len(menu['options'])==2
 rows=[(56,menu['options']),(88,['GUANTXIP','DIHALT']),(120,['ARRIBA IZQDA','ARRIBA DCHA']),(152,['Z80','R800'])]
 lines=['ui_menu_texts:']+['    dw ui_mt%d'%i for i in range(8)]
 for r,(y,texts) in enumerate(rows):
  for v,text in enumerate(texts):
   assert len(text)<=12 and all(32<=ord(c)<96 for c in text)
   lines.append('ui_mt%d: db %d,%d,%d,"%s"'%(r*2+v,y,(256-len(text)*16)//2,len(text),text))
 (B/'ui-menu.inc').write_text('\n'.join(lines)+'\n')
 return [(0x29000,raw),(0x2D000,bytes([0x11])*12288)]
