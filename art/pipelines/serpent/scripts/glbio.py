import json,struct,numpy as np
CT={5120:np.int8,5121:np.uint8,5122:np.int16,5123:np.uint16,5125:np.uint32,5126:np.float32}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def load(f):
    b=open(f,'rb').read()
    assert b[:4]==b'glTF'
    jl=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+jl])
    off=20+jl; bl=struct.unpack('<I',b[off:off+4])[0]; bin_=b[off+8:off+8+bl]
    return j,bin_
def acc(j,bin_,i):
    a=j['accessors'][i]; bv=j['bufferViews'][a['bufferView']]
    dt=CT[a['componentType']]; n=NC[a['type']]
    o=bv.get('byteOffset',0)+a.get('byteOffset',0)
    st=bv.get('byteStride',0); isz=np.dtype(dt).itemsize*n
    if st and st!=isz:
        raw=np.frombuffer(bin_,np.uint8,count=st*(a['count']-1)+isz,offset=o)
        arr=np.lib.stride_tricks.as_strided(raw,(a['count'],isz),(st,1)).copy().view(dt).reshape(a['count'],n)
    else:
        arr=np.frombuffer(bin_,dt,count=a['count']*n,offset=o).reshape(a['count'],n).copy()
    if a.get('normalized'):
        arr=arr.astype(np.float32)/np.iinfo(dt).max
    return arr
def image(j,bin_,i):
    im=j['images'][i]; bv=j['bufferViews'][im['bufferView']]
    o=bv.get('byteOffset',0); return bin_[o:o+bv['byteLength']], im.get('mimeType')
def node_world(j):
    import numpy as np
    W={}
    def local(n):
        if 'matrix' in n: return np.array(n['matrix'],float).reshape(4,4).T
        T=np.eye(4); 
        t=n.get('translation',[0,0,0]); r=n.get('rotation',[0,0,0,1]); s=n.get('scale',[1,1,1])
        x,y,z,w=r
        R=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        T[:3,:3]=R*np.array(s)[None,:]; T[:3,3]=t; return T
    def rec(i,P):
        M=P@local(j['nodes'][i]); W[i]=M
        for c in j['nodes'][i].get('children',[]): rec(c,M)
    for s in j['scenes'][j.get('scene',0)]['nodes']: rec(s,np.eye(4))
    return W

def write(f, attrs_list, images=None, extra=None):
    """attrs_list: list of dict(name->np array, 'indices'->uint32 array, 'material'->int) primitives of ONE mesh.
    images: list of (bytes,mime). extra: callable(j, add_view, add_acc) to add skins/nodes. Returns nothing."""
    bin_=bytearray(); j={'asset':{'version':'2.0','generator':'serpent-prep'},'buffers':[{}],'bufferViews':[],'accessors':[],
       'meshes':[{'primitives':[]}],'nodes':[{'mesh':0,'name':'Serpent'}],'scenes':[{'nodes':[0]}],'scene':0}
    def add_view(data,target=None):
        while len(bin_)%4: bin_.append(0)
        o=len(bin_); bin_.extend(data); v={'buffer':0,'byteOffset':o,'byteLength':len(data)}
        if target: v['target']=target
        j['bufferViews'].append(v); return len(j['bufferViews'])-1
    CTR={np.dtype(np.float32):5126,np.dtype(np.uint32):5125,np.dtype(np.uint16):5123,np.dtype(np.uint8):5121}
    TY={1:'SCALAR',2:'VEC2',3:'VEC3',4:'VEC4',16:'MAT4'}
    def add_acc(arr,target=None,minmax=False):
        arr=np.ascontiguousarray(arr); n=1 if arr.ndim==1 else arr.shape[1]
        a={'bufferView':add_view(arr.tobytes(),target),'componentType':CTR[arr.dtype],'count':arr.shape[0],'type':TY[n]}
        if minmax: a['min']=arr.reshape(len(arr),-1).min(0).tolist(); a['max']=arr.reshape(len(arr),-1).max(0).tolist()
        j['accessors'].append(a); return len(j['accessors'])-1
    for pr in attrs_list:
        p={'attributes':{}}
        for k,v in pr.items():
            if k in ('indices','material'): continue
            p['attributes'][k]=add_acc(v,34962,minmax=(k=='POSITION'))
        p['indices']=add_acc(pr['indices'].astype(np.uint32).ravel(),34963)
        if 'material' in pr: p['material']=pr['material']
        j['meshes'][0]['primitives'].append(p)
    if images:
        j['images']=[];j['textures']=[];j['samplers']=[{'magFilter':9729,'minFilter':9987,'wrapS':10497,'wrapT':10497}]
        for d,mt in images:
            j['images'].append({'bufferView':add_view(d),'mimeType':mt}); j['textures'].append({'source':len(j['images'])-1,'sampler':0})
    if extra: extra(j,add_view,add_acc)
    while len(bin_)%4: bin_.append(0)
    j['buffers'][0]['byteLength']=len(bin_)
    js=json.dumps(j).encode();
    while len(js)%4: js+=b' '
    out=struct.pack('<III',0x46546C67,2,12+8+len(js)+8+len(bin_))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(bin_),0x004E4942)+bytes(bin_)
    open(f,'wb').write(out)
