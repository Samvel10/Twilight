# LODn from the baked LOD0: texture-preserving quadric decimation (same UV atlas -> same textures), then
# per-wedge split, smooth normals, tangents. Output npz for rig.py.
import sys,os,numpy as np,pymeshlab as ml,tempfile
src,out,target=sys.argv[1],sys.argv[2],int(sys.argv[3])
z=np.load(src); P,UV,I=z['P'].astype(np.float64),z['UV'].astype(np.float64),z['I']
ms=ml.MeshSet(); ms.add_mesh(ml.Mesh(vertex_matrix=P,face_matrix=I.astype(np.int32),v_tex_coords_matrix=UV))
ms.compute_texcoord_transfer_vertex_to_wedge()
ms.meshing_merge_close_vertices(threshold=ml.PercentageValue(0.0005))   # weld positions, wedge UVs keep the seams
ms.meshing_decimation_quadric_edge_collapse_with_texture(targetfacenum=target,qualitythr=0.5,extratcoordw=1.0,preserveboundary=True,boundaryweight=1.0,optimalplacement=True,preservenormal=True,planarquadric=True)
d=tempfile.mkdtemp(); f=d+'/l.obj'; ms.save_current_mesh(f,save_wedge_texcoord=True,save_vertex_normal=False)
V=[];VT=[];F=[]
for line in open(f):
    t=line.split()
    if not t: continue
    if t[0]=='v': V.append([float(x) for x in t[1:4]])
    elif t[0]=='vt': VT.append([float(x) for x in t[1:3]])
    elif t[0]=='f': F.append([tuple(int(x)-1 for x in c.split('/')[:2]) for c in t[1:4]])
V=np.array(V);VT=np.array(VT); F=np.array(F)   # (nf,3,2)
keys=F.reshape(-1,2); uk,inv=np.unique(keys,axis=0,return_inverse=True)
P2=V[uk[:,0]]; UV2=VT[uk[:,1]]   # pymeshlab writes the UVs back unchanged (no v flip)
I2=inv.reshape(-1,3)
# smooth normals over welded positions
fn=np.cross(V[F[:,1,0]]-V[F[:,0,0]],V[F[:,2,0]]-V[F[:,0,0]]); vn=np.zeros_like(V)
for k in range(3): np.add.at(vn,F[:,k,0],fn)
vn/=np.linalg.norm(vn,axis=1,keepdims=True)+1e-12; N2=vn[uk[:,0]]
sys.path.insert(0,os.path.dirname(__file__))
t=np.zeros_like(P2); bt=np.zeros_like(P2)
p0,p1,p2=P2[I2[:,0]],P2[I2[:,1]],P2[I2[:,2]]; w0,w1,w2=UV2[I2[:,0]],UV2[I2[:,1]],UV2[I2[:,2]]
e1=p1-p0;e2=p2-p0; d1=w1-w0; d2=w2-w0; r=d1[:,0]*d2[:,1]-d2[:,0]*d1[:,1]; r=np.where(np.abs(r)<1e-12,1e-12,r)
sd=(e1*d2[:,1:2]-e2*d1[:,1:2])/r[:,None]; td=(e2*d1[:,0:1]-e1*d2[:,0:1])/r[:,None]
for k in range(3): np.add.at(t,I2[:,k],sd); np.add.at(bt,I2[:,k],td)
t=t-N2*np.einsum('ij,ij->i',N2,t)[:,None]; t/=np.linalg.norm(t,axis=1,keepdims=True)+1e-12
w=np.sign(np.einsum('ij,ij->i',np.cross(N2,t),bt)); w[w==0]=1
print('LOD v',len(P2),'f',len(I2),'uv range',UV2.min(0),UV2.max(0))
np.savez(out,P=P2.astype(np.float32),N=N2.astype(np.float32),UV=UV2.astype(np.float32),I=I2.astype(np.int64),T=np.c_[t,w].astype(np.float32),headlen=z['headlen'])
