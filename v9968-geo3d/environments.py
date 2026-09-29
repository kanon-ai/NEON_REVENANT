"""Distinct three-dimensional spaces for the private Geo3D adaptation."""
import math
import numpy as np
from mesh import Mesh

def environment_chunk(index,theme):
    from build import road,point,clean,LENGTH
    m=Mesh();m.texture_faces=set();m.block_faces=set();m.harbor_faces=set()
    start=index*LENGTH;origin=road(start)
    def p(z,x,y):return point(z,x,y)-origin
    def surface(vertices,color,target):
        q=np.array(vertices);n=np.cross(q[1]-q[0],q[2]-q[0])
        if np.dot(n,np.array(target)-q.mean(axis=0))<0:q=q[::-1]
        m.poly(q.tolist(),[0,0,0],color)
    def strip(a,b,x0,y0,x1,y1,col):
        surface([p(a,x0,y0),p(b,x0,y0),p(b,x1,y1),p(a,x1,y1)],col,p((a+b)/2,0,125))
    def box(z,x,y,w,h,d,col):
        # Shared vertices are merged below. Exclude the hidden bottom face.
        for side in (-1,1):
            xx=x+side*w/2
            surface([p(z-d/2,xx,y),p(z+d/2,xx,y),p(z+d/2,xx,y+h),p(z-d/2,xx,y+h)],col,p(z,x+side*w, y+h/2))
            zz=z+side*d/2
            surface([p(zz,x-w/2,y),p(zz,x+w/2,y),p(zz,x+w/2,y+h),p(zz,x-w/2,y+h)],col+1 if col<4 else col,p(z+side*d,x,y+h/2))
        surface([p(z-d/2,x-w/2,y+h),p(z-d/2,x+w/2,y+h),p(z+d/2,x+w/2,y+h),p(z+d/2,x-w/2,y+h)],4,p(z,x,y+h+100))
    def frame(z,section,width,col):
        outer=section
        section=[(x-(width if x>0 else -width),y-width) for x,y in section]
        for i in range(len(section)-1):
            a,b=section[i:i+2];c,d=outer[i:i+2]
            surface([p(z,*a),p(z,*b),p(z,*d),p(z,*c)],col,p(z-100,0,125))
    # The same banked carriageway is retained; scenery is no longer a city skin.
    for j in range(4):
        a=start+j*240;b=a+240
        for left,right,col in [(-1100,-245,3),(-245,-215,4),(-215,215,2),(215,245,4),(245,1100,3)]:
            strip(a,b,left,0,right,0,col)
        for x in (-110,110):strip(a+35,b-55,x-2,1,x+2,1,14)
        for side in (-1,1):strip(a,b,side*239,6,side*239,12,6)
    if theme==0:
        # Open water to the left; low harbor sheds and cranes to the right.
        for side in (-1,1):
            strip(start,start+LENGTH,side*265,0,side*265,45,4)
        for z,x,w,h,d,col in [(450,510,270,100,410,2),(720,780,130,65,190,4)]:
            first=len(m.f)
            box(start+z,x,0,w,h,d,col)
            # Only the near shed's road-facing wall earns a texture upload.
            if x==510:
                m.harbor_faces.add(first)
                m.texture_faces.add(first)
        if index%2==0:
            box(start+440,650,100,24,250,24,4)
            box(start+440,520,325,300,20,24,4)
            strip(start+426,start+435,380,170,383,325,7)
        # Water streaks are world geometry, hence have real perspective motion.
        for k in range(3):strip(start+150+k*250,start+230+k*250,-950+k*170,1,-880+k*170,1,9)
    elif theme==2:
        # Tall machinery banks, circular ventilation equipment, overhead girders.
        z=start+520;side=-1 if index%2 else 1;x=side*327
        fan_side=side
        for side in (-1,1):
            if side==fan_side:
                # Cut a real opening around the fan; a full quad would overpaint it.
                strip(start,z-92,side*330,0,side*330,265,4)
                strip(z+92,start+LENGTH,side*330,0,side*330,265,4)
                strip(z-92,z+92,side*330,0,side*330,43,4)
                strip(z-92,z+92,side*330,227,side*330,265,4)
                strip(z-92,z+92,side*334,43,side*334,227,2)
            else:
                for j in range(4):strip(start+j*240,start+(j+1)*240,side*330,0,side*330,265,4)
            strip(start,start+LENGTH,side*330,265,side*520,265,3)
        side=fan_side
        # Recessed octagonal ring and four thick rotor blades on the side wall.
        for i in range(8):
            a=math.tau*i/8;b=math.tau*(i+1)/8
            def ring(t,r):return p(z+math.cos(t)*r,x,135+math.sin(t)*r)
            surface([ring(a,88),ring(b,88),ring(b,64),ring(a,64)],14,p(z,0,135))
        for i in range(4):
            a=math.tau*i/4+.3
            pts=[]
            for ang,r in [(a,12),(a+.18,62),(a+.65,54),(a+.9,12)]:pts.append(p(z+math.cos(ang)*r,x-side*2,135+math.sin(ang)*r))
            surface(pts,7,p(z,0,135))
        for side in (-1,1):
            # Wall-mounted cable conduits and a projecting equipment cabinet.
            strip(start,start+LENGTH,side*322,55,side*322,60,6)
            box(start+170,side*300,15,36,85,120,2)
        frame(start+780,[(-290,0),(-290,285),(290,285),(290,0)],22,4)
    elif theme==3:
        # Continuous octagonal tunnel: walls, chamfers and ceiling enclose camera.
        section=[(-290,0),(-290,240),(-210,320),(210,320),(290,240),(290,0)]
        for j in range(4):
            a=start+j*240;b=a+240
            for k in range(len(section)-1):
                x,y=section[k];xx,yy=section[k+1]
                strip(a,b,x,y,xx,yy,[3,4,2,4,3][k])
        for z in (start+240,start+720):frame(z,section,12,14)
        for j in range(4):
            a=start+j*240+32;b=a+176
            for side in (-1,1):
                strip(a,b,side*288,73,side*288,197,2)
                strip(a+20,b-20,side*286,112,side*286,119,6 if j%2==0 else 7)
        strip(start+100,start+380,-32,319,32,319,6)
        strip(start+580,start+860,-32,319,32,319,6)
    elif theme==4:
        # Exposed bridge to the dawn horizon, with pylons and diagonal cables.
        for side in (-1,1):
            strip(start,start+LENGTH,side*264,0,side*264,48,4)
        if index%2==0:
            for side in (-1,1):
                box(start+470,side*285,0,32,350,35,4)
                for offset in (-330,330):
                    surface([p(start+470,side*285,330),p(start+470+offset,side*255,48),p(start+470+offset,side*260,48),p(start+470,side*290,330)],14,p(start+300,0,125))
            box(start+470,0,325,600,22,35,4)
        for k in range(2):strip(start+170+k*440,start+300+k*440,-850,1,-480,1,9)
    if m.harbor_faces:
        # UV uploads end at the last textured face; place this one first so
        # untextured road/crane faces do not force hundreds of zero UV bytes.
        i=next(iter(m.harbor_faces))
        m.f.insert(0,m.f.pop(i))
        m.harbor_faces={0};m.texture_faces={0}
    m=clean(m)
    assert len(m.v)<=255 and len(m.f)<=255,(theme,index,len(m.v),len(m.f))
    return m,origin
