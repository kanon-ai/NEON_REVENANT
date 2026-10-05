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
    from sector_bosses import make_boss
    return make_boss(theme,turret)
