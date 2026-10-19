import json,sys,urllib.request,os
from PIL import Image,ImageDraw
P=sys.argv[1]; ids=sys.argv[3].split(','); out=sys.argv[2]
c=json.load(open(P+'/dl/cands.json'))
ims=[]
for k in ids:
    f=P+'/dl/thumbs/%s.jpg'%k[:8]
    if not os.path.exists(f):
        try: urllib.request.urlretrieve(c[k]['thumb'],f)
        except Exception as e: print('err',k,e); continue
    im=Image.open(f).convert('RGB'); im.thumbnail((360,240)); 
    can=Image.new('RGB',(360,262),(20,20,20)); can.paste(im,(0,0)); d=ImageDraw.Draw(can)
    d.text((3,242),'%s %s %dk a%d'%(k[:6],c[k]['name'][:28],c[k]['faces']//1000,c[k]['anims']),fill=(255,255,0))
    ims.append(can)
cols=5; rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(cols*360,rows*262))
for i,im in enumerate(ims): S.paste(im,((i%cols)*360,(i//cols)*262))
S.save(out,quality=85); print(len(ims))
