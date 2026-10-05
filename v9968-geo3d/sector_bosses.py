"""Area-specific bosses; muzzle coordinates retain the existing combat contract."""
import math
import numpy as np
from mesh import Mesh

def make_boss(theme,turret=False):
    from build import prism,clean
    m=Mesh();m.boss_theme=theme
    def face(points,col,target):
        q=np.array(points,float)
        if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),target)<0:q=q[::-1]
        m.poly(q.tolist(),[0,0,0],col)
    def top(points,col):face(points,col,(0,1,0))
    def gun(x):
        # Two armored barrels, ending at the same (+/-24,4,-115) firing points.
        prism(m,[(x-7,-114),(x+7,-114),(x+9,-15),(x-9,-15)],-2,10,4)
        face([(x-4,1,-115),(x+4,1,-115),(x+4,7,-115),(x-4,7,-115)],1,(0,0,-1))
    def finish():
        clean(m);kept=[]
        for ids,n,col in m.f:
            q=np.array([m.v[i] for i in ids]);nn=np.cross(q[1]-q[0],q[2]-q[0])
            if nn[1]<0 and nn[0]==0 and nn[2]==0:continue
            kept.append((ids,n,col))
        # Merge adjacent, convex coplanar deck triangles. UVs are continuous.
        merged=[];i=0
        while i<len(kept):
            ids,n,col=kept[i];a=list(dict.fromkeys(ids));done=False
            if len(a)==3 and i+1<len(kept):
                ids2,n2,col2=kept[i+1];b=list(dict.fromkeys(ids2))
                if len(b)==3 and col==col2 and len(set(a)&set(b))==2:
                    edges=[(q[j],q[(j+1)%3]) for q in (a,b) for j in range(3)]
                    boundary=[e for e in edges if (e[1],e[0]) not in edges]
                    if len(boundary)==4:
                        order=[boundary[0][0]]
                        for _ in range(3):
                            nxt=[v for u,v in boundary if u==order[-1]]
                            if not nxt:break
                            order.append(nxt[0])
                        if len(set(order))==4:
                            q=np.array([m.v[k] for k in order]);nn=np.cross(q[1]-q[0],q[2]-q[0])
                            if np.dot(nn,q[3]-q[0])==0 and all(np.dot(np.cross(q[(j+1)%4]-q[j],q[(j+2)%4]-q[(j+1)%4]),nn)>0 for j in range(4)):
                                merged.append((order,n,col));i+=2;done=True
            if not done:merged.append((ids,n,col));i+=1
        m.f=merged;assert len(m.v)<=255 and len(m.f)<=255
        return m

    if turret:
        if theme==3:
            # Separate box breeches: mechanically readable, no circular aperture.
            for x in (-55,55):
                prism(m,[(x-15,-24),(x+15,-24),(x+19,48),(x-19,48)],-10,10,4)
                face([(x-7,-4,-25),(x+7,-4,-25),(x+7,4,-25),(x-7,4,-25)],1,(0,0,-1))
                top([(x-8,11,-15),(x+8,11,-15),(x+8,11,30),(x-8,11,30)],6)
        else:
            if theme==0:
                w=42
                prism(m,[(-w,-28),(-w+10,-48),(w-10,-48),(w,-28),(w-5,26),(-w+5,26)],-8,18,4)
            for x in (-24,24):gun(x)
            if theme==0:top([(-12,19,-18),(12,19,-18),(8,19,7),(-8,19,7)],7)
        return finish()

    if theme==0:
        # Harbor cutter: wide reinforced bow, low wheelhouse, short drive pods.
        prism(m,[(-117,-95),(117,-95),(152,-53),(126,89),(-126,89),(-152,-53)],-24,15,3)
        prism(m,[(-154,-105),(154,-105),(161,-76),(129,-53),(-129,-53),(-161,-76)],-15,26,4)
        for side in (-1,1):
            x=side*119
            prism(m,[(x-24,5),(x+24,5),(x+31,72),(x+23,106),(x-23,106),(x-31,72)],-21,24,4)
            top([(x-13,25,25),(x+13,25,25),(x+13,25,65),(x-13,25,65)],1)
            face([(side*72,-2,-106),(side*126,-2,-106),(side*126,9,-106),(side*72,9,-106)],7,(0,0,-1))
        prism(m,[(-50,12),(50,12),(42,61),(-42,61)],15,35,4)
        face([(-36,23,11),(36,23,11),(36,30,11),(-36,30,11)],1,(0,0,-1))
    elif theme==1:
        # Short twin-hull interceptor: preserve its horizontal silhouette in bank.
        prism(m,[(-151,-30),(151,-30),(151,42),(-151,42)],-10,12,4)
        for side in (-1,1):
            x=side*115
            prism(m,[(x-27,-101),(x+27,-101),(x+39,-68),(x+35,69),(x-35,69),(x-39,-68)],-18,20,3)
            top([(x-18,21,-81),(x+18,21,-81),(x+18,21,-57),(x-18,21,-57)],1)
            top([(x-24,21,-33),(x-17,21,-33),(x-17,21,53),(x-24,21,53)],7)
    elif theme==2:
        # One deep armored hull. Beveled shoulders replace four overlapping pods.
        outline=[(-90,-116),(90,-116),(142,-48),(100,100),(-100,100),(-142,-48)]
        middle=[(x,5,z) for x,z in outline]
        upper=[(x*.79,57,z*.79) for x,z in outline]
        lower=[(x*.86,-39,z*.86) for x,z in outline]
        for i in range(6):
            j=(i+1)%6;t=(middle[i][0],0,middle[i][2])
            face([upper[i],upper[j],middle[j],middle[i]],4,t)
            face([middle[i],middle[j],lower[j],lower[i]],3,t)
        for i in range(1,5):top([upper[0],upper[i],upper[i+1]],4)
        face([(-45,13,-117),(45,13,-117),(45,23,-117),(-45,23,-117)],7,(0,0,-1))
    else:
        # Armored gate: tall pylons and a shallow transverse gun deck, not a ship.
        prism(m,[(-135,-20),(135,-20),(135,38),(-135,38)],-19,19,4)
        for side in (-1,1):
            x=side*127
            prism(m,[(x-24,-35),(x+24,-35),(x+32,-17),(x+32,36),(x-32,36),(x-32,-17)],-79,79,3)
            for y in (-53,-13,27):
                face([(x-18,y,-36),(x+18,y,-36),(x+18,y+26,-36),(x-18,y+26,-36)],4,(0,0,-1))
                face([(x-13,y+4,-37),(x-8,y+4,-37),(x-8,y+21,-37),(x-13,y+21,-37)],12,(0,0,-1))
    return finish()
