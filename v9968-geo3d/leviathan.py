"""Final-boss-only geometry. Gameplay and the other bosses are unchanged."""
import math
import numpy as np
from mesh import Mesh

def final_boss(turret=False):
    from build import prism,engine,clean
    m=Mesh()
    def finish():
        clean(m)
        original_quads={frozenset(ids) for ids,n,col in m.f if len(set(ids))==4 and col in (3,4)}
        # The camera always views the upper decks; hidden horizontal undersides
        # need not be transferred. Merge only coplanar, convex triangle pairs.
        kept=[]
        for ids,n,col in m.f:
            q=np.array([m.v[i] for i in ids]);normal=np.cross(q[1]-q[0],q[2]-q[0])
            if normal[1]<0 and normal[0]==0 and normal[2]==0:continue
            kept.append((ids,n,col))
        merged=[];i=0
        while i<len(kept):
            ids,n,col=kept[i];aa=list(dict.fromkeys(ids));done=False
            if len(aa)==3 and i+1<len(kept):
                ids2,n2,col2=kept[i+1];bb=list(dict.fromkeys(ids2))
                if len(bb)==3 and col==col2 and len(set(aa)&set(bb))==2:
                    edges=[(q[j],q[(j+1)%3]) for q in (aa,bb) for j in range(3)]
                    boundary=[e for e in edges if (e[1],e[0]) not in edges]
                    if len(boundary)==4:
                        order=[boundary[0][0]]
                        for _ in range(3):
                            nxt=[v for u,v in boundary if u==order[-1]]
                            if not nxt:break
                            order.append(nxt[0])
                        if len(set(order))==4:
                            q=np.array([m.v[k] for k in order]);normal=np.cross(q[1]-q[0],q[2]-q[0])
                            convex=all(np.dot(np.cross(q[(j+1)%4]-q[j],q[(j+2)%4]-q[(j+1)%4]),normal)>0 for j in range(4))
                            if convex and np.dot(normal,q[3]-q[0])==0:
                                merged.append((order,n,col));i+=2;done=True
            if not done:merged.append((ids,n,col));i+=1
        m.f=merged
        m.boss_texture_faces={i for i,(_,_,col) in enumerate(m.f) if col in (3,4) and (frozenset(m.f[i][0]) in original_quads or (col==4 and len(set(m.f[i][0]))==4))}
        m.boss_texture_x=192
        return m
    def face(points,col,n):
        q=np.array(points,float)
        if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),n)<0:q=q[::-1]
        m.poly(q.tolist(),[0,0,0],col)
    def top(points,col):face(points,col,[0,1,0])
    def cannon(x):
        # Hexagonal barrel with a dark bore, not a solid luminous rod.
        back=[];rim=[];bore=[]
        for i in range(6):
            a=math.tau*i/6
            back.append((x+10*math.cos(a),5+10*math.sin(a),-28))
            rim.append((x+8*math.cos(a),5+8*math.sin(a),-142))
            bore.append((x+4*math.cos(a),5+4*math.sin(a),-143))
        for i in range(6):
            j=(i+1)%6;a=math.tau*(i+.5)/6
            face([back[i],back[j],rim[j],rim[i]],4 if i<3 else 2,[math.cos(a),math.sin(a),0])
            face([rim[i],rim[j],bore[j],bore[i]],14,[0,0,-1])
        for i in range(1,5):face([bore[0],bore[i],bore[i+1]],1,[0,0,-1])
    if turret:
        prism(m,[(-48,-38),(-27,-60),(27,-60),(48,-38),(40,26),(-40,26)],-15,19,4)
        # Armored cheek plates protect the traversing three-gun mount.
        for side in (-1,1):
            prism(m,[(side*32,-42),(side*57,-18),(side*51,30),(side*28,17)],1,27,3)
        for x in (-27,0,27):cannon(x)
        top([(-20,20,-27),(20,20,-27),(15,20,-18),(-15,20,-18)],7)
        return finish()

    # Deep central hull and a narrower raised flight deck.
    outline=[(-48,-185),(48,-185),(98,-100),(98,115),(65,168),(-65,168),(-98,115),(-98,-100)]
    prism(m,outline,-38,28,3)
    prism(m,[(-44,-122),(44,-122),(67,80),(42,124),(-42,124),(-67,80)],28,47,4)
    for side in (-1,1):
        # Swept heavy shoulders, then separate raised armor panels.
        prism(m,[(side*72,-98),(side*182,-132),(side*287,-28),(side*256,94),(side*170,37),(side*75,95)],-15,19,3)
        prism(m,[(side*106,-73),(side*178,-101),(side*239,-31),(side*189,6)],20,31,4)
        engine(m,side*187,-23,82,29,130)
        # Recessed radiator deck; bright seams are deliberately sparse.
        top([(side*96,20,34),(side*146,20,25),(side*162,20,91),(side*109,20,108)],1)
        for z in (48,67,86):
            top([(side*114,21,z),(side*149,21,z-5),(side*149,21,z-1),(side*114,21,z+4)],4)
        top([(side*108,32,-65),(side*174,32,-88),(side*183,32,-79),(side*112,32,-55)],6)
    # A protected forward reactor, with an actual octagonal bezel and inner core.
    outer=[];inner=[]
    for i in range(8):
        a=math.tau*i/8
        outer.append((29*math.cos(a),-2+25*math.sin(a),-186))
        inner.append((19*math.cos(a),-2+16*math.sin(a),-187))
    for i in range(8):
        j=(i+1)%8;face([outer[i],outer[j],inner[j],inner[i]],4 if i%2 else 14,[0,0,-1])
    for i in range(1,7):face([inner[0],inner[i],inner[i+1]],7 if i%2 else 8,[0,0,-1])
    # Crown behind the gun mount: the turret remains a separately moving model.
    prism(m,[(-28,35),(28,35),(37,89),(0,119),(-37,89)],48,72,3)
    top([(-20,73,62),(20,73,62),(24,73,75),(-24,73,75)],6)
    return finish()
