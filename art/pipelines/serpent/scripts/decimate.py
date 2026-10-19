# Step 2: positions-only weld + quadric decimation of the straightened scan (pymeshlab). Saves low npz (P,I).
import sys,numpy as np,pymeshlab as ml
z=np.load(sys.argv[1]); out=sys.argv[2]; target=int(sys.argv[3])
ms=ml.MeshSet(); ms.add_mesh(ml.Mesh(vertex_matrix=z['P'].astype(np.float64),face_matrix=z['I'].astype(np.int32)))
ms.meshing_merge_close_vertices(threshold=ml.PercentageValue(0.002))
ms.meshing_remove_duplicate_faces(); ms.meshing_remove_unreferenced_vertices()
m=ms.current_mesh(); print('welded v',m.vertex_number(),'f',m.face_number())
ms.meshing_decimation_quadric_edge_collapse(targetfacenum=target,preservenormal=True,preservetopology=False,optimalplacement=True,planarquadric=True,qualitythr=0.4,boundaryweight=2.0)
ms.meshing_remove_unreferenced_vertices()
try: ms.meshing_repair_non_manifold_edges()
except Exception as e: print('nm',e)
ms.meshing_remove_unreferenced_vertices()
m=ms.current_mesh(); print('low v',m.vertex_number(),'f',m.face_number())
np.savez(out,P=m.vertex_matrix().astype(np.float32),I=m.face_matrix().astype(np.int64))
