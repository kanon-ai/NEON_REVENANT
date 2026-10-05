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
        # Box-section heavy railgun: fewer faces, larger readable muzzle.
        # The bore centre remains (x,5,-143), matching the projectile table.
        back=[(x+dx,5+dy,-22) for dx,dy in [(-10,-8),(10,-8),(10,8),(-10,8)]]
        rim=[(x+dx,5+dy,-142) for dx,dy in [(-8,-6),(8,-6),(8,6),(-8,6)]]
        bore=[(x+dx,5+dy,-143) for dx,dy in [(-4,-3),(4,-3),(4,3),(-4,3)]]
        for i,n in enumerate([(0,-1,0),(1,0,0),(0,1,0),(-1,0,0)]):
            j=(i+1)%4
            face([back[i],back[j],rim[j],rim[i]],4 if i==2 else 3,n)
            face([rim[i],rim[j],bore[j],bore[i]],14,[0,0,-1])
        face(bore,1,[0,0,-1])
    if turret:
        prism(m,[(-58,-32),(-38,-62),(38,-62),(58,-32),(49,35),(-49,35)],-15,25,4)
        for x in (-27,0,27):cannon(x)
        top([(-22,26,-20),(22,26,-20),(17,26,-10),(-17,26,-10)],7)
        return finish()

    # Armored central keel and two deep, attached side hulls, not thin wings.
    outline=[(-44,-185),(44,-185),(94,-100),(94,120),(62,168),(-62,168),(-94,120),(-94,-100)]
    prism(m,outline,-42,33,3)
    prism(m,[(-44,-125),(44,-125),(68,90),(43,128),(-43,128),(-68,90)],33,51,4)
    for side in (-1,1):
        prism(m,[(side*82,-85),(side*194,-130),(side*277,-62),(side*260,137),(side*148,149),(side*82,63)],-30,28,3)
        # Broad shoulder armor; vents and panel seams are now in the texture.
        prism(m,[(side*117,-69),(side*191,-101),(side*237,-52),(side*223,83),(side*134,96)],28,41,4)
        # Recessed front intake contrasts with the heavy armored nose.
        face([(side*191,-18,-131),(side*219,-10,-111),(side*219,9,-111),(side*191,13,-131)],1,[0,0,-1])
        face([(side*195,-7,-132),(side*212,-4,-119),(side*212,1,-119),(side*195,4,-132)],6,[0,0,-1])
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
    prism(m,[(-29,40),(29,40),(39,91),(26,119),(-26,119),(-39,91)],51,86,3)
    top([(-23,87,67),(23,87,67),(26,87,78),(-26,87,78)],6)
    return finish()
