from pathlib import Path
import math,struct,json,subprocess,hashlib,re,os
import numpy as np
from PIL import Image,ImageDraw
from mesh import Mesh,words
from hudfont import label
ROOT=Path(__file__).parent.resolve();OUT=ROOT/'out';OUT.mkdir(exist_ok=True)
import shutil
TOOL=Path(os.environ['SDCC_BIN']) if os.environ.get('SDCC_BIN') else Path(shutil.which('sdcc') or shutil.which('sdcc.exe') or 'sdcc').resolve().parent
os.environ['PATH']=str(TOOL)+os.pathsep+os.environ.get('PATH','')
TEXTURED=os.environ.get('NEON_TEXTURE','1')=='1'
N=1536;LENGTH=960;F=170
COLORS=[(0,0,0),(9,15,27),(18,27,43),(29,44,60),(48,68,83),(180,222,225),(38,123,145),(245,139,55),(255,199,110),(18,45,61),(17,32,47),(25,53,76),(56,196,204),(115,233,230),(83,107,121),(136,69,111)]
def unit(v):return v/max(np.linalg.norm(v),1e-9)
def road(s):return np.array([660*math.sin(s/1900)+390*math.sin(s/4200),100*math.sin(s/1100)+160*math.sin(s/3600),s])
def axes(s):
    forward=unit(road(s+1)-road(s-1));right=unit(np.cross([0,1,0],forward));up=np.cross(forward,right)
    bank=.19*math.sin(s/1650)
    return np.column_stack((right*math.cos(bank)+up*math.sin(bank),up*math.cos(bank)-right*math.sin(bank),forward))
def point(s,x,y=0):return road(s)+axes(s)@np.array([x,y,0])
def face(m,pts,col,normal=(0,0,0)):
    p=np.array(pts,float);n=np.cross(p[1]-p[0],p[2]-p[0])
    # Road polygons have an upward-facing winding.
    if n[1]<0:p=p[::-1]
    m.poly(p.tolist(),normal,col)
def clean(m):
    vertices=[];mapping={};remap=[]
    for v in m.v:
        key=tuple(round(x) for x in v)
        if key not in mapping:mapping[key]=len(vertices);vertices.append(key)
        remap.append(mapping[key])
    m.v=vertices;m.f=[([remap[i] for i in ids],normal,base) for ids,normal,base in m.f]
    return m
def facet(m,ids,color):
    m.f.append((ids if len(ids)==4 else ids+[ids[-1]],[0,0,0],color))

def prism(m,outline,y0,y1,color=3):
    start=len(m.v);n=len(outline)
    m.v.extend([(x,y0,z) for x,z in outline]+[(x,y1,z) for x,z in outline])
    center=np.mean(np.array(m.v[start:]),axis=0)
    def f(ids,col):
        p=np.array([m.v[i] for i in ids]);normal=np.cross(p[1]-p[0],p[2]-p[0])
        if np.dot(normal,p.mean(axis=0)-center)<0:ids=ids[::-1]
        facet(m,ids,col)
    for i in range(n):f([start+i,start+(i+1)%n,start+n+(i+1)%n,start+n+i],color if i%2 else max(1,color-1))
    for i in range(1,n-1):
        f([start+n,start+n+i,start+n+i+1],color+1 if color<5 else color)
        f([start,start+i,start+i+1],1)

def engine(m,x,y,z,r,length):
    start=len(m.v)
    for zz in (z-length/2,z+length/2):
        for i in range(6):
            t=math.pi*2*i/6;m.v.append((x+r*math.cos(t),y+r*math.sin(t),zz))
    for i in range(6):facet(m,[start+i,start+(i+1)%6,start+6+(i+1)%6,start+6+i],2+i%3)
    for i in range(1,5):facet(m,[start,start+i+1,start+i],12)

def car(color):
    m=Mesh()
    prism(m,[(-8,-36),(-18,-9),(-8,55),(8,55),(18,-9),(8,-36)],3,16,3)
    # Swept wings and underslung engines, no rectangular body blocks.
    for side in (-1,1):
        prism(m,[(side*9,-22),(side*46,-36),(side*38,-7),(side*12,18)],5,9,3)
        engine(m,side*24,6,-21,7,36)
    m.poly([(-7,17,-20),(7,17,-20),(5,25,0),(-5,25,0)],[0,0,0],12 if color==7 else 7)
    m.poly([(-5,25,0),(5,25,0),(0,17,24)],[0,0,0],6)
    return clean(m)

def boss(turret=False):
    m=Mesh()
    if turret:
        prism(m,[(-36,-27),(-19,-43),(19,-43),(36,-27),(24,30),(-24,30)],-8,14,3)
        for side in (-1,1):
            prism(m,[(side*17-6,-115),(side*17+6,-115),(side*17+9,-17),(side*17-9,-17)],-3,4,4)
        m.poly([(-15,15,-25),(15,15,-25),(9,21,9),(-9,21,9)],[0,0,0],7)
    else:
        prism(m,[(-110,-45),(-58,-105),(58,-105),(110,-45),(80,99),(-80,99)],-25,24,3)
        m.poly([(-110,24,-45),(0,57,6),(0,24,-105),(-58,24,-105)],[0,0,0],4)
        m.poly([(58,24,-105),(0,24,-105),(0,57,6),(110,24,-45)],[0,0,0],3)
        for side in (-1,1):
            prism(m,[(side*78,-55),(side*220,-18),(side*184,107),(side*80,60)],-3,9,3)
            engine(m,side*144,-9,24,26,140)
            m.poly([(side*88,10,-38),(side*206,10,-9),(side*190,10,1),(side*83,10,-30)],[0,0,0],6)
        m.poly([(-38,-9,-106),(38,-9,-106),(27,15,-106),(-27,15,-106)],[0,0,0],7)
        m.poly([(-15,-2,-107),(15,-2,-107),(12,7,-107),(-12,7,-107)],[0,0,0],8)
    return clean(m)

FOUNDATIONS=[]
def city_chunk(index,theme=0):
    m=Mesh();m.texture_faces=set();m.block_faces=set();origin=road(index*LENGTH)
    def p(s,x,y=0):return point(s,x,y)-origin
    # One continuous terrain mesh, not isolated road ribbons over empty space.
    for j in range(4):
        ss=index*LENGTH+j*240;t=ss+240
        for left,right,col in [(-1100,-245,3),(-245,-215,4),(-215,215,2),(215,245,4),(245,1100,3)]:
            face(m,[p(ss,left),p(ss,right),p(t,right),p(t,left)],col)
        for x in (-110,110):face(m,[p(ss+35,x-2,1),p(ss+35,x+2,1),p(t-55,x+2,1),p(t-55,x-2,1)],14)
        for side in (-1,1):
            pts=[p(ss,side*239,6),p(t,side*239,6),p(t,side*239,12),p(ss,side*239,12)]
            if side<0:pts.reverse()
            m.poly([v.tolist() for v in pts],[0,0,0],6)
    # Two distant street walls provide several buildings per quad.
    for side in (() if theme==2 else (-1,1)):
        ss=index*LENGTH;tt=ss+LENGTH
        a=point(ss,side*660);b=point(tt,side*660)
        bottom=min(a[1],b[1])-90;top=max(a[1],b[1])+430
        pts=[a.copy(),b.copy(),b.copy(),a.copy()]
        for q,y in zip(pts,[bottom,bottom,top,top]):q[1]=y
        pts=[q-origin for q in pts]
        n=np.cross(pts[1]-pts[0],pts[2]-pts[0])
        if np.dot(n,point((ss+tt)/2,0)-origin-np.mean(pts,axis=0))<0:pts.reverse()
        m.block_faces.add(len(m.f));m.texture_faces.add(len(m.f))
        m.poly([q.tolist() for q in pts],[0,0,0],2)
    # Buildings use world-up and a horizontal heading, independently of road bank.
    for k,(side,offset) in enumerate([(-1,290),(1,740)]):
        ss=index*LENGTH+offset;h=[240,440,120,560,160][theme]+((index*53+k*83)%170)
        xpos=540 if theme==2 else 385
        f=road(ss+1)-road(ss-1);f[1]=0;f=unit(f);right=np.cross([0,1,0],f)
        center=point(ss,side*xpos,0);samples=[point(ss+dz,side*xpos+dx,0)[1] for dx in (-130,130) for dz in (-135,135)]
        base=max(samples)+4;bottom=min(samples)-35
        def world(x,y,z):return center+right*x+f*z+np.array([0,y-center[1],0])-origin
        start=len(m.v)
        # Foundation spans below the pavement at every corner; top is level.
        outline=[(-125,-130),(125,-130),(125,130),(-125,130)]
        for yy in (bottom,base):
            for x,z in outline:m.v.append(tuple(world(x,yy,z)))
        def outward(ids,col,c):
            pts=np.array([m.v[i] for i in ids]);n=np.cross(pts[1]-pts[0],pts[2]-pts[0])
            if np.dot(n,pts.mean(axis=0)-c)<0:ids=ids[::-1]
            facet(m,ids,col)
        c=world(0,(base+bottom)/2,0)
        for i in range(4):outward([start+i,start+(i+1)%4,start+4+(i+1)%4,start+4+i],3,c)
        outward([start+4,start+5,start+6,start+7],4,c)
        start=len(m.v);outline=[(-95,-65),(-65,-95),(65,-95),(95,-65),(95,65),(65,95),(-65,95),(-95,65)]
        for yy in (base,base+h):
            for x,z in outline:m.v.append(tuple(world(x,yy,z)))
        c=world(0,base+h/2,0)
        for i in range(8):
            m.texture_faces.add(len(m.f))
            outward([start+i,start+(i+1)%8,start+8+(i+1)%8,start+8+i],2+i%3,c)
        # Two convex roof quads plus two triangles, instead of a six-triangle fan.
        for ids in [[0,1,2,3],[0,3,4,7],[4,5,6,7]]:outward([start+8+i for i in ids],4,c)
        # Facade accents in the same building coordinate system.
        for yy in (base+38,base+h-24):
            pts=[world(-side*96,yy,-48),world(-side*96,yy,48),world(-side*96,yy+4,48),world(-side*96,yy+4,-48)]
            ids=list(range(len(m.v),len(m.v)+4));m.v.extend(map(tuple,pts));outward(ids,7 if (index+k)%3==0 else 6,c)
        for i in range(8):
            lo=np.array(m.v[start+i]);hi=np.array(m.v[start+8+i]);assert np.allclose(hi-lo,[0,h,0])
        assert bottom<min(samples) and base>max(samples)
        FOUNDATIONS.append({'chunk':index,'side':side,'base':base,'bottom':bottom,'ground_min':min(samples),'ground_max':max(samples),'height':h,'world_up':True})
    # Stage landmarks share the same grounded coordinate system as the road.
    if theme in (2,3) and index%2==0:
        ss=index*LENGTH+500
        f=road(ss+1)-road(ss-1);f[1]=0;f=unit(f);right=np.cross([0,1,0],f);center=road(ss)
        base=max(point(ss,x)[1] for x in (-300,300))+2
        t=Mesh()
        for side in (-1,1):
            x=side*290
            prism(t,[(x-17,-24),(x+17,-24),(x+17,24),(x-17,24)],base-center[1]-100,base-center[1]+210,4)
        prism(t,[(-307,-24),(307,-24),(307,24),(-307,24)],base-center[1]+195,base-center[1]+216,4 if theme==2 else 3)
        first=len(m.v)
        m.v.extend([tuple(center+right*x+np.array([0,y,0])+f*z-origin) for x,y,z in t.v])
        m.f.extend(([first+i for i in ids],normal,col) for ids,normal,col in t.f)
    m=clean(m);assert len(m.v)<=255 and len(m.f)<=255
    return m,origin

def chunk(index,theme=0):
    if theme==1:return city_chunk(index,theme)
    from environments import environment_chunk
    return environment_chunk(index,theme)

def packmesh(m,kind='none'):
    m.f=[(ids,[v*.45 for v in normal],1) if base in (1,3,4,9) and any(normal)
         else (ids,[0,0,0],base) for ids,normal,base in m.f]
    uvs=bytearray();faces=[];uv_end=0
    for fi,(ids,normal,col) in enumerate(m.f):
        pts=np.array([m.v[i] for i in ids]);span=np.ptp(pts,axis=0)
        use=TEXTURED and len(set(ids))==4 and ((kind=='city' and fi in m.texture_faces) or (kind=='boss' and span[0]>50 and span[2]>30 and (not hasattr(m,'boss_texture_faces') or fi in m.boss_texture_faces)))
        if use:
            harbor=fi in getattr(m,'harbor_faces',set())
            uaxis=0 if kind=='boss' or span[0]>span[2] else 2;vaxis=1 if kind=='city' else 2
            for q in pts:
                u=round((q[uaxis]-pts[:,uaxis].min())/max(span[uaxis],1)*63)
                v=round((q[vaxis]-pts[:,vaxis].min())/max(span[vaxis],1)*(127 if kind=='city' and not harbor else 63))
                uvs.extend((u+(128 if harbor else getattr(m,'boss_texture_x',128) if kind=='boss' else (64 if fi in m.block_faces else 0)),127-v if kind=='city' else v))
            uv_end=len(uvs);faces.append((ids,[0,0,0],128))
        else:
            uvs.extend(bytes(8));faces.append((ids,normal,col))
    m.f=faces;d=m.data()+uvs;assert len(d)<=16384
    return bytearray(d+bytes(16382-len(d))+struct.pack("<H",uv_end))

def foreground(s,cp,view):
    m=Mesh()
    def poly(points,col):
        pts=[view@(q-cp) for q in points]
        # Slightly beyond the viewport avoids integer rounding cracks.
        for normal,offset in [(np.array([0,0,1]),-16),(np.array([F,0,130]),0),(np.array([-F,0,130]),0),(np.array([0,F,94]),0),(np.array([0,-F,108]),0)]:
            out=[]
            for a,b in zip(pts,pts[1:]+pts[:1]):
                da=np.dot(normal,a)+offset;db=np.dot(normal,b)+offset
                if da>=0:out.append(a)
                if (da>=0)!=(db>=0):out.append(a+(b-a)*da/(da-db))
            pts=out
            if len(pts)<3:return
        for i in range(1,len(pts)-1,2):
            q=[pts[0],pts[i],pts[i+1]]
            if i+2<len(pts):q.append(pts[i+2])
            m.poly([v.tolist() for v in q],[0,0,0],col)
    # The nearest original 240-unit road cell may straddle the camera.
    start=math.floor((s-160)/240)*240
    for ss in range(start,start+720,240):
        t=ss+240
        for left,right,col in [(-1800,-245,3),(-245,-215,4),(-215,215,2),(215,245,4),(245,1800,3)]:
            poly([point(ss,left),point(t,left),point(t,right),point(ss,right)],col)
        for x in (-110,110):poly([point(ss+35,x-2,1),point(t-55,x-2,1),point(t-55,x+2,1),point(ss+35,x+2,1)],14)
        for side in (-1,1):
            x=side*239
            poly([point(ss,x-2,7),point(t,x-2,7),point(t,x+2,7),point(ss,x+2,7)],6)
    m=clean(m)
    def screen(i):
        x,y,z=m.v[i];return (128+int(F*x/z),106-int(F*y/z))
    def area(ids):
        (x,y),(u,v),(a,b)=map(screen,ids[:3]);return (u-x)*(b-y)-(v-y)*(a-x)
    # Geo3D culls using the first three projected integer vertices.
    # Clipping can put three on the same viewport edge; rotate the quad.
    m.f=[(max([ids[k:]+ids[:k] for k in range(4)],key=area),normal,col) for ids,normal,col in m.f]
    coverage=Image.new('1',(256,212));draw=ImageDraw.Draw(coverage)
    for ids,normal,col in m.f:
        if col in (2,3,4) and area(ids)>0:draw.polygon([screen(i) for i in ids],fill=1)
    assert all(coverage.getpixel((x,197)) for x in range(256)),('bottom coverage',s)
    return m.data()

def bitmap(im):
    a=np.array(im);return bytes(((a[:,::2]<<4)|a[:,1::2]).flat)
def build():
    subprocess.run([str(TOOL/'sdcc.exe'),'-mz80','--opt-code-speed','-c',str(ROOT/'src/sound.c'),'-o',str(OUT/'sound.rel')],check=True)
    subprocess.run([str(TOOL/'sdcc.exe'),'-mz80','--std-c99','--opt-code-speed','--no-std-crt0','--code-loc','0x8000','--data-loc','0xD000','-Wl-b_HOME=0xB500','-I'+str(ROOT/'src'),str(ROOT/'src/hc_logic.c'),str(OUT/'sound.rel'),'-o',str(OUT/'hc.ihx')],check=True)
    map_text=(OUT/'hc.map').read_text()
    area=re.search(r'_CODE\s+([0-9A-F]{8})\s+([0-9A-F]{8})',map_text)
    assert area and int(area[1],16)+int(area[2],16)<=0xB500
    syms={}
    for line in (OUT/'hc.map').read_text().splitlines():
        match=re.search(r'([0-9A-F]{8})\s+(_hc_init|_hc_tick|_hc_draw|_audio_setup|_mode)\s',line)
        if match:syms[match[2]]=int(match[1],16)
    assert len(syms)==5,syms
    (ROOT/'src/hc_symbols.inc').write_text(''.join(k[1:]+' = '+hex(v)+'\n' for k,v in syms.items()))

    from presentation import enemy_mesh,title_image
    banks=[bytearray(16384),packmesh(car(7)),packmesh(enemy_mesh(0)),packmesh(enemy_mesh(1))]
    from stages import stage_sky
    sky=stage_sky(0);sky.putpalette(sum([list(c) for c in COLORS],[])+[0]*720)
    sky.save(OUT/'sky.png');b=bitmap(sky);banks.extend([bytearray(b[:16384]),bytearray(b[16384:])])
    hud=Image.new('P',(256,256));hud.putpalette(sky.getpalette());d=ImageDraw.Draw(hud)
    label(d,(4,0),'NEON REVENANT HC / 3D',fill=5)
    for i in range(15):
        y=16+i*16
        label(d,(5,y),('SENTRY / HARBOR GUARD' if i>=1 else '00 BREAKWATER APPROACH'),fill=5)
        d.line((4,y+13,251,y+13),fill=11)
    # Unused HUD rows 176..207 map to VRAM 944..975, below the texture atlas.
    d.rectangle((32,176,223,207),fill=1)
    d.line((32,176,223,176),fill=6);d.line((32,207,223,207),fill=6)
    label(d,(101,179),'GAME OVER',fill=7)
    label(d,(65,193),'PRESS FIRE TO RESTART',fill=5)
    hud.save(OUT/'hud.png');b=bitmap(hud);banks.extend([bytearray(b[:16384]),bytearray(b[16384:])])
    chunks=[chunk(i) for i in range(32)]
    banks.extend(packmesh(m,'city') for m,o in chunks)
    assert len(banks)==40
    frames=bytearray();stats=[];near_banks=[bytearray()];near_sizes=[]
    for f in range(N):
        s=350+f*17.3
        cp=point(s,0,125);ax=axes(s+160)
        forward=unit(ax[:,2]-.10*ax[:,1]);camera_up=unit(np.array([0,1,0])*.65+ax[:,1]*.35)
        right=unit(np.cross(camera_up,forward));up=np.cross(forward,right)
        view=np.array([right,up,forward])
        clipped=foreground(s,cp,view);near_sizes.append(len(clipped))
        if len(near_banks[-1])+len(clipped)>16384:near_banks.append(bytearray())
        near_bank=67+len(near_banks)-1;near_offset=len(near_banks[-1]);near_banks[-1]+=clipped
        k=int(s//LENGTH)
        poses=[]
        for j in (3,2,1,0):
            idx=k+j
            if idx>=32 or j==3:poses.append((255,np.eye(3),np.array([0,0,2000])))
            else:poses.append((8+idx,view,view@(chunks[idx][1]-cp)))
        carstates=[]
        positions=[(s+250,0,1),
                   (s+250+500*math.cos(f*.004)-70,-100,2),
                   (s+250+450+220*math.sin(f*.009),110,3)]
        for cs,lane,bank in positions:
            pos=point(cs,lane,4);mat=axes(cs)
            cv=view@(pos-cp)
            carstates.append((bank if cv[2]>90 else 255,view@mat,cv))
        carstates=[carstates[1],carstates[2],carstates[0]]
        phase=(f-675)*.017;dist=650-120*math.sin(phase*.6)
        bpos=point(s+dist,70*math.sin(phase),110+20*math.sin(phase*.7))
        yaw=.28*math.sin(phase)
        rot=np.array([[math.cos(yaw),0,math.sin(yaw)],[0,1,0],[-math.sin(yaw),0,math.cos(yaw)]])
        bm=axes(s+dist)@rot@np.array([[1,0,0],[0,math.cos(.32),math.sin(.32)],[0,-math.sin(.32),math.cos(.32)]])
        turret_yaw=.5*math.sin(phase*1.7)
        tr=np.array([[math.cos(turret_yaw),0,math.sin(turret_yaw)],[0,1,0],[-math.sin(turret_yaw),0,math.cos(turret_yaw)]])
        carstates[0]=(64,view@bm,view@(bpos-cp))
        carstates[1]=(65,view@bm@tr,view@(bpos+bm@np.array([0,76,0])-cp))
        poses.extend(carstates)
        rec=bytearray()
        for bank,mat,pos in poses:rec+=words((mat*16384).flatten().tolist()+pos.tolist())
        rec+=bytes([p[0] for p in poses])+bytes(1)
        # V9968 sky displacement follows heading and pitch; road remains real 3D.
        yaw=math.atan2(forward[0],forward[2]);pitch=math.asin(forward[1])
        rec+=words([int(48+yaw*60),512+int(24-pitch*85),160,0])
        speed=1 if f>=675 else 0;rec+=struct.pack('<HH',768,768+16+speed*16)
        rec+=bytes([1 if f>=675 else 0,near_bank])+struct.pack("<H",near_offset);rec+=bytes(256-len(rec));frames+=rec
        stats.append({'f':f,'segment':k,'banks':[p[0] for p in poses]})
    banks.extend(bytearray(frames[i:i+16384]) for i in range(0,len(frames),16384));assert len(banks)==64
    banks.extend([packmesh(boss(),'boss'),packmesh(boss(True),'boss')])
    tex=Image.new('P',(256,128),2);tex.putpalette(sky.getpalette());td=ImageDraw.Draw(tex)
    for y in range(0,128,20):
        td.line((0,y,63,y),fill=3)
        for x in range(7,60,16):
            c=7 if (x+y*3)%17<2 else (6 if (x*3+y)%7<2 else 3)
            td.rectangle((x,y+4,x+6,y+8),fill=c)
    td.line((1,0,1,127),fill=4);td.line((62,0,62,127),fill=1)
    # Six distinct facades across a single street-wall texture.
    td.rectangle((64,0,127,127),fill=1)
    for i in range(6):
        x=64+i*11;top=[18,2,26,10,34,6][i]
        td.rectangle((x,top,min(x+9,127),127),fill=2+(i%2))
        td.line((x,top,x,127),fill=4)
        for y in range(top+5,122,9):
            for xx in (x+3,x+7):
                if xx<=127:td.point((xx,y),fill=7 if (i*5+y)%13<2 else 6 if (y+i)%4==0 else 4)
        td.line((x,top+2,min(x+9,127),top+2),fill=4)
    td.rectangle((128,0,191,63),fill=3)
    for y in (2,24,46):
        td.line((130,y,189,y),fill=1);td.line((130,y+1,189,y+1),fill=4)
    for x in (130,151,172,189):td.line((x,1,x,61),fill=2)
    for y in range(29,43,3):td.line((157,y,178,y),fill=1)
    td.line((135,9,147,9),fill=6);td.rectangle((182,51,187,53),fill=7)
    # Dedicated final-boss armor: broad markings survive the 256-pixel viewport.
    td.rectangle((192,0,255,63),fill=4)
    for y in (0,21,43,63):td.rectangle((192,y,255,min(y+1,63)),fill=2)
    for x in (192,212,235,254):td.line((x,0,x,63),fill=3)
    td.rectangle((198,8,229,16),fill=2)
    for x in range(200,230,5):td.rectangle((x,9,x+1,15),fill=14)
    td.rectangle((198,28,232,31),fill=12)
    td.rectangle((238,6,248,48),fill=2)
    for y in range(9,48,6):td.rectangle((240,y,246,y+2),fill=1)
    td.rectangle((196,51,251,58),fill=7)
    for x in range(197,252,9):td.polygon([(x,51),(x+4,51),(x-1,58),(x-5,58)],fill=2)
    # Harbor material occupies unused atlas space below the ordinary boss armor.
    # Broad loading doors, steel ribs, lit clerestory and a cyan roof strip.
    td.rectangle((128,64,191,127),fill=3)
    td.rectangle((128,64,191,68),fill=4)
    td.line((130,69,189,69),fill=6)
    for x in range(131,191,10):
        td.line((x,72,x,124),fill=2)
        td.rectangle((x+2,75,min(x+7,190),80),fill=7 if x%3==0 else 14)
    for x in (134,164):
        td.rectangle((x,91,x+19,123),fill=1)
        td.line((x,90,x+19,90),fill=14)
        for y in range(95,121,5):td.line((x+2,y,x+17,y),fill=3)
        td.rectangle((x+21,93,x+23,95),fill=8)
    td.rectangle((128,125,191,127),fill=2)
    tex.save(OUT/'texture-atlas.png');banks.append(bytearray(bitmap(tex)))
    banks.extend(b+bytes(16384-len(b)) for b in near_banks)
    assert len(banks)==101,len(banks)
    from stages import stage_boss,stage_palette,stage_sky,STAGE_NAMES,BOSS_NAMES
    stage_stats=[]
    for theme in range(1,5):
        meshes=[chunk(i,theme)[0] for i in range(32)]
        stage_stats.append({'stage':theme,'max_vertices':max(len(m.v) for m in meshes),'max_faces':max(len(m.f) for m in meshes)})
        banks.extend(packmesh(m,'city') for m in meshes)
    assert len(banks)==229
    for theme in range(1,5):
        for turret in (False,True):banks.append(packmesh(stage_boss(theme,turret),'boss'))
    assert len(banks)==237
    # Ten sector/boss caption strips, each 2 KiB, in banks 237..238.
    labels=bytearray()
    for theme in range(5):
        for title in (STAGE_NAMES[theme],BOSS_NAMES[theme]):
            im=Image.new('P',(256,16));dd=ImageDraw.Draw(im);label(dd,(5,0),title,fill=5);dd.line((4,13,251,13),fill=11);labels+=bitmap(im)
    labels+=bytes(32768-len(labels));banks.extend([labels[:16384],labels[16384:]])
    # Five 48-byte RGB palettes, followed by four separate sky images.
    palette_bank=bytearray()
    for theme in range(5):
        for rgb in stage_palette(theme,COLORS):palette_bank.extend(round(c/255*31) for c in rgb)
    banks.append(palette_bank+bytes(16384-len(palette_bank)))
    for theme in range(1,5):
        im=stage_sky(theme);bb=bitmap(im);banks.extend([bb[:16384],bb[16384:]])
    assert len(banks)==248
    title=title_image(COLORS);title.save(OUT/'title.png');tb=bitmap(title)
    banks.extend([tb[:16384],tb[16384:],packmesh(enemy_mesh(2))])
    banks.extend(bytearray(16384) for _ in range(256-len(banks)))
    pal=[]
    for rgb in COLORS:
        r,g,b=[round(c/255*31) for c in rgb];pal.extend([r,g,b])
    (ROOT/'src/palette.inc').write_text('palette:\n .db '+','.join(map(str,pal))+'\n')
    subprocess.run([str(TOOL/'sdasz80.exe'),'-los',str(OUT/'player.rel'),str(ROOT/'src/player.asm')],cwd=ROOT/'src',check=True)
    subprocess.run([str(TOOL/'sdldz80.exe'),'-n','-i',str(OUT/'player'),str(OUT/'player.rel')],cwd=ROOT,check=True)
    for line in (OUT/'player.ihx').read_text().splitlines():
        r=bytes.fromhex(line[1:]);assert sum(r)%256==0
        if r[3]==0:
            n=r[0];a=int.from_bytes(r[1:3],'big')
            if a>=0xE800:assert a+n<=0xF000;a=a-0xE800+0x4100
            banks[0][a-0x4000:a-0x4000+n]=r[4:4+n]
    for line in (OUT/'hc.ihx').read_text().splitlines():
        r=bytes.fromhex(line[1:]);assert sum(r)%256==0
        if r[3]==0:
            n=r[0];a=int.from_bytes(r[1:3],'big')
            assert 0x8000<=a and a+n<=0xB700,(hex(a),n)
            banks[0][a-0x8000+0x900:a-0x8000+0x900+n]=r[4:4+n]
    rom=b''.join(banks);assert len(rom)==4194304
    (OUT/'NEON_REVENANT_GEO3D.rom').write_bytes(rom)
    report={'stages':5,'stage_geometry':stage_stats,'textured':TEXTURED,'near_banks':len(near_banks),'near_mesh_max_bytes':max(near_sizes),'frames':N,'rom_bytes':len(rom),'chunks':[{'v':len(m.v),'f':len(m.f)} for m,o in chunks],'sha256':hashlib.sha256(rom).hexdigest()}
    (OUT/'foundation-validation.json').write_text(json.dumps(FOUNDATIONS,indent=2))
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':build()
