import sys; sys.path.insert(0,sys.argv[1]); import glbio,numpy as np,io
from PIL import Image
for f in sys.argv[2:]:
    j,b=glbio.load(f); W=glbio.node_world(j)
    print('==',f.split('/')[-1][:8],'nodes',len(j['nodes']),'meshes',len(j['meshes']),'mats',len(j.get('materials',[])),'imgs',len(j.get('images',[])),'skins',len(j.get('skins',[])),'anims',len(j.get('animations',[])))
    print(' asset',j.get('asset'))
    for ni,n in enumerate(j['nodes']):
        if 'mesh' in n:
            M=W[ni]
            for p in j['meshes'][n['mesh']]['primitives']:
                pos=glbio.acc(j,b,p['attributes']['POSITION']); pw=(np.c_[pos,np.ones(len(pos))]@M.T)[:,:3]
                nt=j['accessors'][p['indices']]['count']//3 if 'indices' in p else len(pos)//3
                print(' node',ni,n.get('name'),'attrs',list(p['attributes']),'v',len(pos),'t',nt,'mat',p.get('material'),'min',pw.min(0).round(3),'max',pw.max(0).round(3))
    for i,m in enumerate(j.get('materials',[])): print(' mat',i,m.get('name'),{k:v for k,v in m.get('pbrMetallicRoughness',{}).items()}, 'normal' in str(m.keys()))
    for i,im in enumerate(j.get('images',[])):
        d,mt=glbio.image(j,b,i); I=Image.open(io.BytesIO(d)); print(' img',i,mt,I.size,len(d)//1024,'KB')
