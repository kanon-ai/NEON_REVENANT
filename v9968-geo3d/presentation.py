"""Native low-poly enemy silhouettes and pixel title for the private prototype."""
from PIL import Image,ImageDraw
from hudfont import label

def enemy_mesh(kind):
    from mesh import Mesh
    from build import prism,clean
    m=Mesh()
    def surface(points,normal,col):
        import numpy as np
        q=np.array(points);n=np.cross(q[1]-q[0],q[2]-q[0])
        desired=np.array([0,1,0]) if len(set(q[:,1]))==1 else np.array([0,0,-1])
        if np.dot(n,desired)<0:points=points[::-1]
        m.poly(points,normal,col)
    if kind==0: # Needle interceptor: nose faces the camera (-Z).
        prism(m,[(0,-75),(-16,-13),(-12,36),(12,36),(16,-13)],0,15,4)
        for s in (-1,1):
            prism(m,[(s*9,-10),(s*62,26),(s*52,43),(s*11,17)],1,6,3)
        surface([(-7,16,-40),(7,16,-40),(5,16,-13),(-5,16,-13)],[0,0,0],7)
        surface([(-9,2,-15),(9,2,-15),(7,10,-24),(-7,10,-24)],[0,0,0],8)
    elif kind==1: # Fork drone: two forward mandibles and a central eye.
        prism(m,[(-20,-23),(20,-23),(30,15),(0,37),(-30,15)],-3,18,3)
        for s in (-1,1):
            prism(m,[(s*19,-15),(s*39,-62),(s*54,-49),(s*45,28),(s*19,20)],-7,8,4)
        surface([(-13,0,-24),(13,0,-24),(10,13,-24),(-10,13,-24)],[0,0,0],7)
    else: # Broad gunship with underslung paired cannon pods.
        prism(m,[(-28,-29),(28,-29),(35,24),(-35,24)],-6,18,3)
        for s in (-1,1):
            prism(m,[(s*20,-8),(s*73,-22),(s*78,19),(s*22,26)],0,9,4)
            prism(m,[(s*43-9,-62),(s*43+9,-62),(s*43+12,18),(s*43-12,18)],-12,2,3)
            x=s*43
            surface([(x-6,-10,-63),(x+6,-10,-63),(x+6,0,-63),(x-6,0,-63)],[0,0,0],7)
        surface([(-16,19,-18),(16,19,-18),(10,19,-3),(-10,19,-3)],[0,0,0],8)
    # Nose-down attack attitude exposes the top silhouette near the horizon.
    import math
    a=math.radians(-22);c=math.cos(a);q=math.sin(a)
    m.v=[(x,c*y-q*z,q*y+c*z) for x,y,z in m.v]
    return clean(m)

def title_image(colors):
    # Preserve the established V9990 artwork and shaded logo, not a placeholder.
    from pathlib import Path
    import numpy as np
    src=Image.open(Path(__file__).parent/'assets/title-reference.png').convert('RGB').crop((32,16,288,228))
    rgb=np.array(src,dtype=np.int32);pal=np.array(colors,dtype=np.int32)
    idx=np.argmin(((rgb[:,:,None,:]-pal[None,None,:,:])**2).sum(axis=3),axis=2).astype('uint8')
    im=Image.new('P',(256,256));im.putpalette(sum(map(list,colors),[])+[0]*720)
    im.paste(Image.fromarray(idx),(0,0));d=ImageDraw.Draw(im)
    d.rectangle((0,0,255,14),fill=0)
    label(d,(5,1),'TURBO R + V9968 / GEO3D',fill=14)
    d.rectangle((43,86,212,153),fill=1)
    d.line((43,86,212,86),fill=6)
    label(d,(62,89),'HC / POLYGON EDITION',fill=12)
    label(d,(77,102),'ARROWS : MOVE',fill=5)
    label(d,(77,113),'SPACE  : FIRE',fill=5)
    label(d,(77,124),'X      : NOVA',fill=5)
    label(d,(77,135),'ESC    : PAUSE',fill=14)
    d.rectangle((33,181,223,191),fill=1)
    label(d,(65,181),'PRESS SPACE TO START',fill=5)
    d.rectangle((0,196,255,211),fill=0)
    label(d,(29,199),'NEON REVENANT HC / GEO3D',fill=14)
    return im
