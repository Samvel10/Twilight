"""attach props (bow, spear) to hand sockets so they sit correctly in a given clip pose.
solve(): hand bone transform (component space) from the retargeted clip via AnimPose, desired prop transform in component space
(character faces +Y, up +Z), relative = desired * inverse(hand)."""
import unreal, math
def log(m): unreal.log_warning('HUM '+str(m))
EAS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
BOW='/Game/Twilight/Humans/Props/Bow/a2385a27e8a4416a829a08469196a6ce/StaticMeshes/a2385a27e8a4416a829a08469196a6ce'
SPEAR='/Game/Twilight/Humans/Props/Spear2/spear/StaticMeshes/spear'
def mesh_axes(sm):
    b=sm.get_bounding_box(); mn,mx=b.min,b.max; ext=[mx.x-mn.x,mx.y-mn.y,mx.z-mn.z]
    ctr=unreal.Vector((mx.x+mn.x)/2,(mx.y+mn.y)/2,(mx.z+mn.z)/2)
    order=sorted(range(3),key=lambda i:-ext[i]); return ext,ctr,order
def hand_cs(anim, t, bone):
    opt=unreal.AnimPoseEvaluationOptions()
    pose=unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, t, opt)
    return unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
AX=[unreal.Vector(1,0,0),unreal.Vector(0,1,0),unreal.Vector(0,0,1)]
def rot_from_axes(long_i, depth_i, long_to, depth_to):
    """rotation mapping local axis long_i -> long_to and depth_i -> depth_to (unit vectors)"""
    def cross(u,v): return [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
    def norm(u): l=math.sqrt(sum(x*x for x in u)); return [x/l for x in u]
    E=[[1,0,0],[0,1,0],[0,0,1]]; s0=E[long_i]; s1=E[depth_i]; s2=cross(s0,s1)
    av=norm([long_to.x,long_to.y,long_to.z]); dv=[depth_to.x,depth_to.y,depth_to.z]; k=sum(x*y for x,y in zip(av,dv)); dv=norm([d-k*x for d,x in zip(dv,av)]); cv=cross(av,dv)
    # R = dst * src^T  (columns: long, depth, cross)
    R=[[av[i]*s0[j]+dv[i]*s1[j]+cv[i]*s2[j] for j in range(3)] for i in range(3)]
    # matrix -> rotator via quaternion
    m=R
    tr=m[0][0]+m[1][1]+m[2][2]
    if tr>0: s=math.sqrt(tr+1)*2; w=0.25*s; x=(m[2][1]-m[1][2])/s; y=(m[0][2]-m[2][0])/s; z=(m[1][0]-m[0][1])/s
    elif m[0][0]>m[1][1] and m[0][0]>m[2][2]: s=math.sqrt(1+m[0][0]-m[1][1]-m[2][2])*2; w=(m[2][1]-m[1][2])/s; x=0.25*s; y=(m[0][1]+m[1][0])/s; z=(m[0][2]+m[2][0])/s
    elif m[1][1]>m[2][2]: s=math.sqrt(1+m[1][1]-m[0][0]-m[2][2])*2; w=(m[0][2]-m[2][0])/s; x=(m[0][1]+m[1][0])/s; y=0.25*s; z=(m[1][2]+m[2][1])/s
    else: s=math.sqrt(1+m[2][2]-m[0][0]-m[1][1])*2; w=(m[1][0]-m[0][1])/s; x=(m[0][2]+m[2][0])/s; y=(m[1][2]+m[2][1])/s; z=0.25*s
    return unreal.Quat(x,y,z,w)
def attach(char_actor, sm_path, anim, t, bone, length_cm, long_to, depth_to, depth_sign=1, grip_frac=0.5, offset=unreal.Vector(0,0,0)):
    sm=unreal.load_asset(sm_path); ext,ctr,order=mesh_axes(sm); li,di=order[0],order[2]
    s=length_cm/ext[li]
    q=rot_from_axes(li, di, long_to, unreal.Vector(depth_to.x*depth_sign,depth_to.y*depth_sign,depth_to.z*depth_sign))
    # grip point in mesh local: along the long axis at grip_frac
    b=sm.get_bounding_box(); g=[ctr.x,ctr.y,ctr.z]; lo=[b.min.x,b.min.y,b.min.z]; hi=[b.max.x,b.max.y,b.max.z]
    g[li]=lo[li]+(hi[li]-lo[li])*grip_frac; grip=unreal.Vector(*g)
    hand=hand_cs(anim,t,bone)
    # desired comp-space transform: rotation q, scale s, grip lands on the hand (+offset in comp space)
    gp=q.rotate_vector(grip*s)
    desired=unreal.Transform(hand.translation+offset-gp, q.rotator(), unreal.Vector(s,s,s))
    rel=unreal.MathLibrary.compose_transforms(desired, unreal.MathLibrary.invert_transform(hand))
    a=EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0)); c=a.static_mesh_component
    c.set_static_mesh(sm); c.set_mobility(unreal.ComponentMobility.MOVABLE)
    a.attach_to_actor(char_actor, bone, unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
    a.set_actor_relative_transform(rel, False, False)
    log('attach %s ext=%s order=%s scale=%.4f rel loc=%s rot=%s'%(sm_path.split('/')[-1],[round(e,1) for e in ext],order,s,rel.translation,rel.rotation.rotator()))
    return a, rel
