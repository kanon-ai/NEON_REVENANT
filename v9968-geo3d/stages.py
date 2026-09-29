"""Private Geo3D campaign assets; no changes to the public HC edition."""
from PIL import Image, ImageDraw
from mesh import Mesh

STAGE_NAMES=['00 BREAKWATER APPROACH','01 CHROME DISTRICT','02 SKYWAY ASSAULT','03 THE BLACK SPIRE','04 DAWN EXODUS']
BOSS_NAMES=['SENTRY / HARBOR GUARD','WARDEN / INTERCEPTOR','RAZOR / SIEGE CARRIER','NOX / CENTRAL CORE','DAWN LEVIATHAN']

def stage_palette(theme, original):
    p=list(original)
    changes={
      0:{3:(14,34,48),9:(24,56,67)},
      1:{1:(12,13,29),2:(21,24,42),3:(34,38,59),4:(69,73,100),6:(100,73,161),7:(244,100,167),9:(28,28,49)},
      2:{1:(13,31,50),2:(23,37,54),3:(30,44,60),4:(66,94,114),6:(55,151,180),7:(242,173,80),9:(22,44,66)},
      3:{1:(7,14,23),2:(13,24,35),3:(24,39,52),4:(47,67,80),6:(38,128,146),7:(232,118,64),9:(14,28,38),14:(86,110,123)},
      4:{1:(77,56,85),2:(31,37,53),3:(30,45,63),4:(106,99,110),6:(62,157,165),7:(255,174,83),9:(62,52,76),14:(189,152,124)},
    }
    for i,c in changes.get(theme,{}).items():p[i]=c
    return p

def stage_sky(theme):
    im=Image.new('P',(256,256),1);d=ImageDraw.Draw(im)
    if theme==3:
        return im  # No city or stars behind the enclosed tunnel.
    if theme in (0,4):
        d.rectangle((0,108,255,255),fill=3)
        for y in (113,119,128):d.line((0,y,255,y),fill=9)
        if theme==4:
            d.ellipse((166,55,202,91),fill=14)
            for y in (95,99,104):d.line((0,y,255,y),fill=9)
        else:
            for x in range(160,256,12):d.rectangle((x,103-x%17,x+8,109),fill=9)
            d.ellipse((40,43,49,52),fill=14)
    elif theme==2:
        for y in (66,89,112):
            for x in range((y*3)%31,256,47):d.line((x,y,x+25,y),fill=9)
    else:
        for x in range(0,256,11):
            h=18+(x*17%42);d.rectangle((x,143-h,x+8,255),fill=9)
    # A quiet deep star field: faint dust, sparse silver stars, dark breathing room.
    import random,math
    stars=random.Random(9968+theme)
    for i in range(95 if theme!=4 else 12):
        x=stars.randrange(256);y=int(17+x*.23+stars.gauss(0,7))
        if 2<=y<94 and im.getpixel((x,y))==1:d.point((x,y),fill=2 if i%4 else 3)
    for i in range(52 if theme!=4 else 17):
        x=stars.randrange(3,253);y=stars.randrange(4,95)
        if im.getpixel((x,y))==1:d.point((x,y),fill=4 if i%5 else 14)
    if theme!=4:
        for x,y in [(28,25),(174,18),(221,63)]:
            if im.getpixel((x,y))==1:
                d.point((x,y),fill=5)
                for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:d.point((x+dx,y+dy),fill=3)
    return im

def stage_boss(theme,turret=False):
    if theme==4:
        from leviathan import final_boss
        return final_boss(turret)
    # Import after build.py has defined the geometry helpers.
    from build import prism,engine,clean
    m=Mesh()
    def finish():
        m.f=[(ids,n,14 if col==4 else 4 if col==3 else col) for ids,n,col in m.f]
        return clean(m)
    if turret:
        if theme==3:
            prism(m,[(-22,0),(0,-28),(22,0),(0,28)],-15,23,7)
            for side in (-1,1):engine(m,side*55,0,0,12,50)
        else:
            w=27 if theme==1 else 42
            prism(m,[(-w,-34),(0,-52),(w,-34),(w,25),(-w,25)],-8,18,4)
            for side in (-1,1):prism(m,[(side*24-6,-115),(side*24+6,-115),(side*24+8,-15),(side*24-8,-15)],0,8,7)
        return finish()
    if theme==1:
        prism(m,[(-20,-160),(0,-210),(20,-160),(48,100),(0,135),(-48,100)],-12,27,4)
        for side in (-1,1):
            prism(m,[(side*25,-110),(side*200,70),(side*180,130),(side*35,52)],-4,10,3)
            engine(m,side*80,-8,96,18,90)
    elif theme==2:
        for side in (-1,1):
            x=side*125
            prism(m,[(x-52,-125),(x,-175),(x+52,-125),(x+58,135),(x-58,135)],-26,38,3)
            engine(m,x,-5,139,28,100)
        prism(m,[(-153,-15),(153,-15),(175,74),(-175,74)],5,25,4)
        prism(m,[(-36,-50),(0,-85),(36,-50),(36,105),(-36,105)],25,63,3)
    elif theme==3:
        # Faceted core with four detached orbital housings.
        ring=[(-65,0,0),(0,0,-65),(65,0,0),(0,0,65)]
        for i in range(4):
            a=ring[i];b=ring[(i+1)%4]
            for y,col in ((95,4),(-80,3)):
                pts=[a,b,(0,y,0)];import numpy as np
                n=np.cross(np.array(b)-a,np.array(pts[2])-a)
                if np.dot(n,np.mean(pts,axis=0))<0:pts.reverse()
                m.poly(pts,[0,0,0],col)
        for side in (-1,1):
            for z in (-65,65):
                x=side*132
                prism(m,[(x-22,z-27),(x,z-43),(x+22,z-27),(x+22,z+27),(x-22,z+27)],-24,24,3)
                engine(m,x,0,z,10,30)
    else:
        prism(m,[(-65,-115),(0,-155),(65,-115),(96,85),(0,142),(-96,85)],-25,40,3)
        for side in (-1,1):
            prism(m,[(side*50,-52),(side*175,-110),(side*258,-10),(side*235,75),(side*170,15),(side*65,74)],-8,17,4)
            engine(m,side*152,-10,62,24,96)
        prism(m,[(-29,-70),(0,-105),(29,-70),(29,90),(-29,90)],40,68,7)
    return finish()
