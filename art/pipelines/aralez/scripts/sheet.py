import json,sys,urllib.request,os
from PIL import Image,ImageDraw
db={}
for f in sys.argv[3].split(','): db.update(json.load(open(f)))
uids=sys.argv[4].split(','); out=sys.argv[1]; td=sys.argv[2]
ims=[]
for u in uids:
    m=db.get(u)
    if not m:
      try:
        d=json.load(urllib.request.urlopen('https://api.sketchfab.com/v3/models/'+u,timeout=30))
        m=dict(name=d['name'],user=d['user']['username'],anims=d.get('animationCount'),faces=d['faceCount'],thumb=max((t for t in d['thumbnails']['images']),key=lambda t:t['width'] if t['width']<=400 else 0)['url'])
      except Exception as e: print('nometa',u,e); m=dict(name='?',user='?',anims='?',faces='?',thumb='')
    p=os.path.join(td,u+'.jpg')
    if not os.path.exists(p):
        try: b=urllib.request.urlopen(m['thumb'],timeout=30).read(); open(p,'wb').write(b)
        except Exception:
            try:
                d=json.load(urllib.request.urlopen('https://api.sketchfab.com/v3/models/'+u,timeout=30))
                b=urllib.request.urlopen(max((t for t in d['thumbnails']['images']),key=lambda t:t['width'] if t['width']<=400 else 0)['url'],timeout=30).read(); open(p,'wb').write(b)
            except Exception as e: print('no thumb',u,e)
    try: im=Image.open(p).convert('RGB')
    except Exception: im=Image.new('RGB',(360,240),(90,0,0))
    im=im; im.thumbnail((360,240)); c=Image.new('RGB',(360,270),(20,20,20)); c.paste(im,(0,0))
    ImageDraw.Draw(c).text((4,244),'%s %s a%s f%s\n%s'%(u[:6],m['user'][:14],m['anims'],m['faces'],m['name'][:44]),fill=(255,255,0))
    ims.append(c)
cols=5; rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(360*cols,270*rows))
for i,c in enumerate(ims): S.paste(c,((i%cols)*360,(i//cols)*270))
S.save(out,quality=88); print(out)
