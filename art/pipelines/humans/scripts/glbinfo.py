import json,struct,sys,re
for f in sys.argv[1:]:
  b=open(f,'rb').read(); n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n])
  N=j['nodes']; skins=j.get('skins',[])
  print('=====',f.split('/')[-1][:12],'meshes',len(j.get('meshes',[])),'skins',len(skins),'anims',len(j.get('animations',[])),'mats',len(j.get('materials',[])),'imgs',len(j.get('images',[])))
  for s in skins:
    names=[re.sub(r'_\d+$','',N[k].get('name','')) for k in s['joints']]
    ue=[x for x in ('pelvis','spine_01','spine_03','clavicle_l','upperarm_l','hand_r','thigh_l','calf_l','foot_r','ball_r','head','neck_01','index_01_l') if x in names]
    print('  skin joints',len(names),'UE4 names',len(ue),'/13',names[:8])
  tris=0
  for m in j.get('meshes',[]):
    t=0
    for p in m['primitives']:
      if 'indices' in p: t+=j['accessors'][p['indices']]['count']//3
    tris+=t; print('  mesh',m.get('name')[:30],'prims',len(m['primitives']),'tris',t,'morph' if any('targets' in p for p in m['primitives']) else '')
  print('  total tris',tris,'| mats',[m.get('name','')[:18] for m in j.get('materials',[])][:14])
  ims=[]
  for im in j.get('images',[]):
    if 'bufferView' in im:
      bv=j['bufferViews'][im['bufferView']]; o=20+n+8+bv.get('byteOffset',0); d=b[o:o+bv['byteLength']]
      if d[:4]==b'\x89PNG': w,h=struct.unpack('>II',d[16:24])
      else:
        i=2;w=h=0
        while i<len(d)-9:
          if d[i]==0xFF and d[i+1] in (0xC0,0xC2): h,w=struct.unpack('>HH',d[i+5:i+9]);break
          i+=2+struct.unpack('>H',d[i+2:i+4])[0]
      ims.append('%dx%d'%(w,h))
  print('  images',ims[:20])
