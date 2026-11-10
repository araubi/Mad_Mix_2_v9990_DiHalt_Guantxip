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
 menu=json.loads((A/'menu.json').read_text());assert menu['default']==0 and len(menu['options'])==2
 for selected,name in enumerate(('normal','hard')):
  data=bytearray()
  for row,(text,y) in enumerate(zip(menu['options'],menu['rows'])):
   x=(256-len(text)*16)//2;style=int(row!=selected)
   for i,c in enumerate(text):
    n=ord(c)-32;assert 0<=n<64
    data+=packet((n%16)*16,1312+style*64+(n//16)*16,x+i*16,y,16,16)
  n=ord('>')-32;data+=packet((n%16)*16,1312+(n//16)*16,menu['arrow_x'],menu['rows'][selected],16,16)
  output(name,data)
 # Graphics-set row under the difficulty options: < NAME >, toggled with left/right.
 for n,name in enumerate(('GUANTXIP','DIHALT')):
  data=bytearray();text='< '+name+' >';x=(256-len(text)*16)//2;y=menu.get('set_row',152)
  for i,c in enumerate(text):
   if c==' ':continue
   k=ord(c)-32;style=1 if c in '<>' else 0
   data+=packet((k%16)*16,1312+style*64+(k//16)*16,x+i*16,y,16,16)
  output(f'set{n}',data)
 return [(0x29000,raw),(0x2D000,bytes([0x11])*12288)]
