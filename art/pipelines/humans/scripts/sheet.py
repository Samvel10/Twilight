import json,sys,urllib.request,io,os
from PIL import Image,ImageDraw,ImageFont
P=sys.argv[1]; out=sys.argv[2]; uids=sys.argv[3].split(',')
rows={}
for f in ('dl/sf.json','dl/andy.json'):
  for r in json.load(open(os.path.join(P,f))): rows.setdefault(r['uid'],r)
os.makedirs(P+'/dl/thumbs',exist_ok=True)
sel=[]
for u in uids:
  m=[r for k,r in rows.items() if k.startswith(u)]
  if m: sel.append(m[0])
W,H=360,240; cols=6; sh=Image.new('RGB',(cols*W,((len(sel)+cols-1)//cols)*(H+30)),'white'); d=ImageDraw.Draw(sh)
try: fnt=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
except Exception: fnt=None
for i,r in enumerate(sel):
  fn=P+'/dl/thumbs/'+r['uid']+'.jpg'
  th=r['thumb'][0] if isinstance(r['thumb'],list) else r['thumb']
  if not os.path.exists(fn) and th:
    try: open(fn,'wb').write(urllib.request.urlopen(th,timeout=30).read())
    except Exception as e: print('thumb err',r['uid'],e)
  x,y=(i%cols)*W,(i//cols)*(H+30)
  if os.path.exists(fn):
    im=Image.open(fn).convert('RGB'); im.thumbnail((W,H)); sh.paste(im,(x,y))
  d.text((x+2,y+H+1),'%d %s %s'%(i,r['uid'][:6],r['name'][:40]),fill='black',font=fnt)
  d.text((x+2,y+H+15),'%s f%s %s'%(r.get('user','Andywoodhead')[:18],r['faces'],r['lic'][:10]),fill='blue',font=fnt)
sh.save(out,quality=85); print('saved',out,len(sel))
