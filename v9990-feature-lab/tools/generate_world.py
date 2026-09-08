"""Original, deterministic perspective worlds for NEON REVENANT.

Each stage is a 16-frame periodic camera flight through opaque 3D geometry.
Output: 256x180 indexed pixels, even-X/high-nibble V9990 packed 4bpp.
Offline depth-buffered material rendering uses the shared MSX3 art palette.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from art_palette import PALETTE, PALETTE_RGB5

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'world'
WIDTH,HEIGHT=256,180
HORIZON=60.0
FOCAL=136.0
EYE=90.0
NEAR=22.0
PERIOD=384.0
FRAME_COUNT=16
FAR=2100.0
SS=2


def clipped(points):
    """Sutherland-Hodgman clipping against the camera's near/far planes."""
    for plane,sign in [(NEAR,1),(FAR,-1)]:
        result=[]
        for a,b in zip(points,points[1:]+points[:1]):
            ai=(a[2]-plane)*sign>=0; bi=(b[2]-plane)*sign>=0
            if ai:
                result.append(a)
            if ai!=bi:
                t=(plane-a[2])/(b[2]-a[2])
                result.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(3)))
        points=result
    return points


def projected(p):
    x,y,z=p
    return (round(WIDTH*.5+FOCAL*x/z),round(HORIZON+FOCAL*(EYE-y)/z))


class Scene:
    def __init__(self,stage,phase):
        self.stage=stage
        self.phase=phase
        self.faces=[]

    def face(self,points,color,bias=0,light=0):
        points=clipped(points)
        if len(points)<3:
            return
        xy=[projected(p) for p in points]
        if max(p[0] for p in xy)<0 or min(p[0] for p in xy)>=WIDTH or max(p[1] for p in xy)<0 or min(p[1] for p in xy)>=HEIGHT:
            return
        self.faces.append((sum(p[2] for p in points)/len(points)+bias,points,color,light))

    def ground(self,x0,x1,z0,z1,color,y=0,bias=-1,light=0):
        self.face([(x0,y,z0),(x1,y,z0),(x1,y,z1),(x0,y,z1)],color,bias,light)

    def side(self,x,y0,y1,z0,z1,color,bias=-2,light=0):
        self.face([(x,y0,z0),(x,y1,z0),(x,y1,z1),(x,y0,z1)],color,bias,light)

    def front(self,x0,x1,y0,y1,z,color,bias=-3,light=0):
        self.face([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)],color,bias,light)

    def box(self,x0,x1,y0,y1,z0,z1,front=8,side=2,top=3):
        # Closed opaque mass: three visible surfaces, not a wireframe extrusion.
        self.front(x0,x1,y0,y1,z0,front,0)
        self.side(x0 if x0>0 else x1,y0,y1,z0,z1,side,0)
        self.ground(x0,x1,z0,z1,top,y=y1,bias=0)

    def road(self):
        # Broad wet tarmac is a material, not a neon grid.
        self.ground(-105,105,NEAR,FAR,1,bias=7000)
        self.ground(-80,80,NEAR,FAR,2,bias=6999)
        self.ground(-27,24,NEAR,FAR,2,bias=6998)
        for side in [-1,1]:
            self.ground(*sorted([side*92,side*105]),NEAR,FAR,3,bias=6997)
            self.side(side*105,0,8,NEAR,FAR,2,bias=5000)
            self.ground(*sorted([side*103,side*107]),NEAR,FAR,4,y=8,bias=4999)
        for k in range(-2,29):
            z=k*96-self.phase;cell=k%4
            for side in [-1,1]:
                self.ground(side*31-.9,side*31+.9,z+15,z+47,4,bias=-1)
                self.ground(side*91-1,side*91+1,z+63,z+79,5 if self.stage!=1 else 14,y=.12,bias=-2,light=.3)
                self.side(side*104.8,3,5,z+68,z+78,6 if self.stage!=1 else 15,-3,.6)
            self.ground(-79,79,z+3,z+4.5,3 if cell==0 else 1,y=.03,bias=-1.2)
            for ribbon in range(9):
                x=-75+ribbon*18+(cell%2)*3;start=z+7+(ribbon*17+cell*11)%65
                w=1.4+(ribbon+cell)%3;color=3 if ribbon%3!=1 else 8
                self.ground(x-w,x+w,start,start+31,color,y=.055,bias=-2.5)
                if (ribbon+cell)%3==0:self.ground(x-.65,x+.8,start+8,start+21,5 if ribbon%2==0 else 13,y=.075,bias=-2.7,light=.15)
            # Broken wet reflections bend and vary in width in world coordinates.
            for side in [-1,1]:
                center=side*(59+((cell+2*(side>0))%4)*7)
                accent=5 if (side<0 and self.stage!=1) else 13 if self.stage<2 else 10
                for j in range(5):
                    start=z+8+j*16;w=[5.8,3.0,4.2,1.4,2.5][(j+cell)%5]
                    x=center+math.sin((j+cell)*1.7)*2
                    self.ground(x-w,x+w,start,start+11,3 if accent==5 else 8,y=.05,bias=-3)
                    self.ground(x-w*.45,x+w*.6,start+1,start+12,accent,y=.09,bias=-3.1,light=.18)
                    if (j+cell)%3==0:self.ground(x-.6,x+.9,start+3,start+5,6 if accent==5 else 14,y=.12,bias=-3.2,light=.4)
            if cell==1:
                for j in range(4):self.ground(-96,-87,z+18+j*5,z+20+j*5,1,y=.06,bias=-2)
            if cell==3:self.face([(42,.08,z+19),(51,.08,z+29),(47,.08,z+29),(47,.08,z+45),(37,.08,z+45),(37,.08,z+29),(33,.08,z+29)],3,-2)

    def sign(self,side,x,y,z,width,height,word,accent=5):
        glyphs={'N':[5,7,7,7,5],'O':[7,5,5,5,7],'I':[7,2,2,2,7],
                'R':[6,5,6,5,5],'A':[2,5,7,5,5],'V':[5,5,5,5,2]}
        self.side(x,y,y+height,z,z+width,1,-6)
        self.side(x-side*.12,y+height-2,y+height,z+3,z+width-3,accent,-6.1,.75)
        self.side(x-side*.16,y+2,y+height-5,z+width-12,z+width-4,accent,-6.2,.24)
        size=min((width-18)/(len(word)*4),max(1.5,(height-8)/5))
        for index,ch in enumerate(word):
            for row,bits in enumerate(glyphs[ch]):
                for column in range(3):
                    if bits&(4>>column):
                        offset=(index*4+column)*size
                        zz=z+4+offset if side<0 else z+width-18-offset
                        self.side(x-side*.22,y+4+(4-row)*size,y+4+(5-row)*size,zz,zz+size*.74,6,-6.4,.6)

    def city(self):
        # Glass tower, terraced office and a low retail podium with a taller rear.
        shapes=[(0,144,270,52),(157,97,196,72),(273,84,134,89)]
        for repeat in range(-1,7):
            for side in [-1,1]:
                for kind,(offset,depth,height,width) in enumerate(shapes):
                    z=repeat*PERIOD+offset+(61 if side>0 else 0)-self.phase
                    inner=118+[6,0,12][kind]+(5 if side>0 else 0)
                    height+=([43,-27,35][kind] if side>0 else 0)
                    a,b=sorted([side*inner,side*(inner+width)])
                    self.box(a,b,0,height,z,z+depth,front=3 if kind==1 else 2,side=3 if side<0 else 8,top=4)
                    wall=side*(inner-.2)
                    self.box(*sorted([side*(inner-4),side*(inner+width+5)]),0,27,z+4,z+depth-4,2,1,3)
                    for ledge in ([31,119,height-8] if kind==0 else [31,76,height-8]):
                        self.box(*sorted([side*(inner-2),side*(inner+width+2)]),ledge,ledge+3,z+2,z+depth-2,3,3,4)
                    self.box(*sorted([side*(inner+11),side*(inner+width-7)]),height,height+26,z+17,z+depth-13,3,2,4)
                    # Large glazing masses and sparse, clustered narrow warm rooms.
                    for col in range(12,depth-11,18):
                        self.side(wall,35,height-13,z+col,z+col+12,2 if (col//18+kind)%3 else 3,-3)
                        for level in range(40,height-15,12):
                            cell=(level//12*7+col//18*11+kind*5+(side>0)*3)%17
                            if cell in [0,1,3,4,5,7,10,12,13,15]:
                                color=14 if cell in [3,12] else 13 if cell in [4,5,13,15] else 9
                                ww=6+(cell%3)*2.5
                                self.side(wall-side*.15,level,level+4.5,z+col+1,z+col+1+ww,color,-3.2,.3 if color!=9 else .05)
                                if cell in [3,4,13]:self.side(wall-side*.19,level+3,level+4.5,z+col+2,z+col+ww,15,-3.3,.2)
                            if cell==10:self.side(wall-side*.12,level+5,level+10,z+col+7,z+col+9,4,-3.3)
                    for band in range(48,height-12,36):
                        self.side(wall-side*.04,band,band+2.0,z+3,z+depth-3,4,-3.4)
                        self.side(wall-side*.05,band-2,band,z+3,z+depth-3,1,-3.5)
                    for rib in [5,depth-5]:self.side(wall-side*.1,30,height-6,z+rib,z+rib+1.8,4,-3.4)
                    for level in range(40,height-12,35):
                        self.front(a+4,b-4,level,level+1.5,z-.2,4,-3)
                        if (level//35+kind)%3==0:self.front(a+10,a+19,level+5,level+7,z-.4,13,-3.4,.15)
                    if kind==1:self.sign(side,wall-side*.5,73,z+17,74,48,'NOIR',5 if side<0 else 10)
                    elif kind==0:self.sign(side,wall-side*.5,64,z+77,63,36,'NOVA',10 if side<0 else 5)
                    else:self.sign(side,wall-side*.5,41,z+19,59,25,'NOVA',5 if side<0 else 10)
                    if kind==1:
                        self.side(wall-side*.3,131,161,z+29,z+63,4,-4)
                        for slit in range(5):self.side(wall-side*.4,135+slit*5,137+slit*5,z+32,z+59,1,-4.2)
                    self.side(wall-side*4.4,5,22,z+19,z+depth-14,2,-4)
                    self.side(wall-side*4.6,20,22,z+21,z+depth-17,9,-4.2)
                    for door in range(28,depth-15,31):
                        self.side(wall-side*4.7,5,18,z+door,z+door+11,1,-4.3)
                        self.side(wall-side*4.8,15,17,z+door+1,z+door+9,13,-4.4,.2)
                    if kind==1:
                        for off in [25,57]:self.box(*sorted([side*(inner+18),side*(inner+33)]),height+26,height+37,z+off,z+off+16,3,2,4)
                    if kind==0:
                        self.front(a+width*.5-1,a+width*.5+1,height+26,height+44,z+28,3,-2)
                        self.front(a+width*.5-1,a+width*.5+1,height+41,height+44,z+27.8,11,-2.1,.8)

    def cylinder(self,side,x,cy,cz,radius,depth):
        points=[(cy+math.sin(i*math.tau/16)*radius,cz+math.cos(i*math.tau/16)*radius) for i in range(16)]
        for i,((y,z),(yy,zz)) in enumerate(zip(points,points[1:]+points[:1])):
            self.face([(x,y,z),(x+side*depth,y,z),(x+side*depth,yy,zz),(x,yy,zz)],[3,4,9,4,3,2,2,1][(i//2)%8])
        self.face([(x,y,z) for y,z in points],1,-3)
        for color,r in [(3,radius*.82),(2,radius*.65),(13,radius*.43),(1,radius*.29)]:
            self.face([(x-side*(radius-r)*.015,cy+math.sin(i*math.tau/16)*r,cz+math.cos(i*math.tau/16)*r) for i in range(16)],color,-4,.35 if color==13 else 0)
        for vane in range(7):
            a=vane*math.tau/7
            self.face([(x-side*.7,cy+math.sin(a)*radius*.65,cz+math.cos(a)*radius*.65),
                       (x-side*.7,cy+math.sin(a+.28)*radius*.59,cz+math.cos(a+.28)*radius*.59),
                       (x-side*.7,cy+math.sin(a+.75)*radius*.24,cz+math.cos(a+.75)*radius*.24)],4,-4.5)

    def industrial(self):
        for repeat in range(-1,8):
            for side in [-1,1]:
                z=repeat*PERIOD+(87 if side>0 else 0)-self.phase
                self.box(*sorted([side*136,side*235]),-75,177+(side>0)*36,z,z+158,3,3,4)
                self.box(*sorted([side*150,side*226]),-75,238,z+211,z+316,2,8,3)
                wall=side*135.8
                for off in [12,68,121]:
                    self.side(wall,23,150,z+off,z+off+30,3,-3)
                    self.side(wall-side*.1,32,138,z+off+3,z+off+25,2,-3.1)
                    self.side(wall-side*.2,126,132,z+off+6,z+off+22,9,-3.3)
                    self.side(wall-side*.3,130,132,z+off+7,z+off+14,14,-3.4,.3)
                self.cylinder(side,side*119,78,z+82,45,17)
                # Recessed inspection plates, cable bundles and bolted turbine mounts.
                self.side(wall-side*.4,24,45,z+9,z+47,1,-4)
                for slat in range(5):self.side(wall-side*.5,27+slat*3,28+slat*3,z+13,z+42,9 if slat==0 else 4,-4.2)
                for cable in [0,4,9]:self.side(wall-side*.4,152+cable,154+cable,z+10,z+148,4 if cable==4 else 2,-4)
                for zz in [32,133]:
                    for yy in [25,128]:
                        self.side(side*118.8,yy,yy+7,z+zz,z+zz+7,4,-4.5)
                        self.side(side*118.6,yy+2,yy+4,z+zz+2,z+zz+4,9,-4.6)
                self.side(side*149.7,57,127,z+227,z+298,3,-3)
                for seam in [239,267,288]:self.side(side*149.5,61,122,z+seam,z+seam+2,1,-3.2)
                for off in [236,263,290]:
                    self.side(side*149.4,102,108,z+off,z+off+13,13,-3.4,.15)
                    self.side(side*149.5,70,89,z+off,z+off+15,2,-3.3)
                self.box(*sorted([side*123,side*211]),177,184,z+7,z+149,3,3,9)
                for off in [32,102]:
                    self.box(*sorted([side*158,side*179]),184,236,z+off,z+off+20,3,4,9)
                    self.box(*sorted([side*151,side*186]),217,221,z+off-3,z+off+23,4,2,9)
                # Diagonal steel suspension; warm light is inset, never an outline.
                zz=z+187
                self.box(*sorted([side*111,side*127]),-28,170,zz,zz+18,3,2,4)
                self.face([(side*113,40,zz),(side*120,40,zz),(side*179,181,zz),(side*172,181,zz)],4,-3)
                self.front(*sorted([side*113,side*118]),55,151,zz-.2,9,-3.4)
                self.front(*sorted([side*114,side*117]),69,73,zz-.4,14,-3.5,.4)
                if side<0:
                    self.box(-127,127,160,175,zz,zz+18,3,2,4)
                    self.front(-94,92,163,166,zz-.2,4,-3)
                    self.front(-81,-34,164,166,zz-.4,13,-3.3,.25)
                    self.front(57,76,164,166,zz-.4,6,-3.3,.25)
                    self.front(84,102,162,172,zz-.5,1,-3.4)
                self.box(*sorted([side*109,side*129]),9,29,z+248,z+333,3,2,4)
                self.side(side*108.7,17,21,z+254,z+325,9,-4)
                for off in range(256,326,13):self.side(side*108.5,18,20,z+off,z+off+5,13,-4.2,.25)

    def tunnel(self):
        # Octagonal pressure shell with beveled graphite/metal wall geometry.
        cross=[(-83,0),(-116,34),(-116,169),(-81,205),(81,205),(116,169),(116,34),(83,0)]
        for i,(a,b) in enumerate(zip(cross,cross[1:])):
            self.face([(a[0],a[1],NEAR),(b[0],b[1],NEAR),(b[0],b[1],FAR),(a[0],a[1],FAR)],[2,3,3,2,3,8,2][i],6500)
        for repeat in range(-1,8):
            for block in range(3):
                z=repeat*PERIOD+block*128-self.phase
                for i,(a,b) in enumerate(zip(cross,cross[1:])):
                    aa=(a[0]*.94,102+(a[1]-102)*.94);bb=(b[0]*.94,102+(b[1]-102)*.94)
                    self.face([(a[0],a[1],z),(b[0],b[1],z),(bb[0],bb[1],z),(aa[0],aa[1],z)],3,-2)
                    self.face([(aa[0],aa[1],z),(bb[0],bb[1],z),(bb[0],bb[1],z+10),(aa[0],aa[1],z+10)],4,-2.2)
                for side in [-1,1]:
                    wall=side*115.7
                    self.side(wall,44,157,z+19,z+108,3,-3)
                    self.side(wall-side*.2,49,151,z+24,z+101,1,-3.2)
                    self.side(wall-side*.3,65,137,z+32,z+92,2 if block!=1 else 8,-3.4)
                    if (block+(side>0))%3==1:
                        self.side(wall-side*.5,77,125,z+46,z+80,4,-3.6)
                        self.side(wall-side*.6,85,116,z+49,z+76,5,-3.7,.28)
                        self.side(wall-side*.7,98,103,z+54,z+72,6,-3.8,.7)
                        # Data cells etched into the broad luminous glass.
                        for bar in range(4):
                            self.side(wall-side*.8,88+bar*6,90+bar*6,z+52,z+60+(bar%3)*4,2,-3.9)
                        self.side(wall-side*.85,92,95,z+67,z+73,7,-4,.4)
                    else:
                        for strip in [62,137]:self.side(wall-side*.5,strip,strip+2,z+38,z+84,4,-3.6)
                        self.side(wall-side*.6,78,114,z+61,z+63,3,-3.7)
                        self.side(wall-side*.7,78,82,z+69,z+77,13,-3.8,.25)
                        self.face([(wall-side*.4,68,z+37),(wall-side*.4,73,z+37),(wall-side*.4,131,z+81),(wall-side*.4,126,z+81)],3,-3.65)
                        for row in range(4):self.side(wall-side*.6,115+row*4,116+row*4,z+43,z+58,4,-3.8)
                    # Stacked cable trays and inset status panels below the hatch.
                    for row in [35,38]:self.side(wall-side*.6,row,row+1.5,z+25,z+93,3,-3.8)
                    self.side(wall-side*.6,159,163,z+35,z+86,1,-3.8)
                    for cell in range(4):self.side(wall-side*.7,160,162,z+39+cell*10,z+43+cell*10,9 if cell<3 else 13,-4,.1)
                    self.side(wall-side*.4,28,31,z+14,z+107,4,-3)
                    self.side(wall-side*.5,29,30,z+24,z+87,5,-3.4,.4)
                    for bolt in [29,94]:
                        for h in [54,144]:self.side(wall-side*.7,h,h+2,z+bolt,z+bolt+2,9,-4)
                # Asymmetric recessed roof fixtures and suspended equipment pods.
                self.ground(-77,73,z+20,z+107,1,y=204.6,bias=-3)
                self.ground(-54,-32,z+28,z+99,3,y=204.4,bias=-3.2)
                self.ground(-48,-38,z+35,z+84,6,y=204.2,bias=-3.4,light=.6)
                self.ground(11,63,z+29,z+92,8,y=204.5,bias=-3.3)
                self.ground(21,56,z+33,z+88,2,y=204.3,bias=-3.4)
                if block==0:
                    self.box(69,109,143,170,z+58,z+93,3,2,4)
                    self.front(79,96,149,152,z+57.8,13,-4,.45)
                if block==2:
                    self.box(-113,-99,7,32,z+37,z+80,3,2,4)
                    self.side(-98.8,17,23,z+49,z+68,10,-4,.2)

    def background(self):
        h,w=HEIGHT*SS,WIDTH*SS;yy,xx=np.mgrid[:h,:w]
        haze=np.exp(-(((xx/SS-128)/89)**2+((yy/SS-HORIZON)/37)**2))
        sky=np.array([8,11,20] if self.stage==0 else [10,12,18] if self.stage==1 else [9,17,23],dtype=float)
        tint=np.array([20,32,42] if self.stage!=1 else [26,26,31],dtype=float)
        im=Image.fromarray(np.uint8(np.clip(sky+haze[:,:,None]*tint,0,255)))
        d=ImageDraw.Draw(im)
        def box(coords,fill):d.rectangle(tuple(round(v*SS) for v in coords),fill=fill)
        if self.stage!=2:
            for layer in range(3):
                for k in range(31):
                    x=k*9-8+(layer*17)%9;top=37+(k*19+layer*13)%20-layer*9;width=4+(k*7+layer*3)%10
                    col=[(24,34,46),(18,28,39),(12,21,31)][layer]
                    box((x,top,x+width,63),col)
                    if k%4==layer:box((x+2,top-7,x+3,top),col)
                    for y in range(top+5,61,7):
                        if (k+y//7+layer)%4==0:box((x+2,y,x+3,y+.4),(64,63,62) if k%3 else (91,69,45))
            if self.stage==0:d.arc((166*SS,-10*SS,233*SS,56*SS),190,291,fill=(55,66,79),width=SS)
            for k in range(14):d.point((((k*71+23)%256)*SS,((k*13+7)%34)*SS),fill=(53,60,73))
        return np.array(im,dtype=np.float32)

    def render(self):
        self.road();[self.city,self.industrial,self.tunnel][self.stage]()
        h,w=HEIGHT*SS,WIDTH*SS
        canvas=self.background();depthbuffer=np.full((h,w),np.inf,np.float32);emission=np.zeros((h,w,3),np.float32)
        fog_color=np.array([(46,66,84),(56,61,66),(37,64,74)][self.stage],np.float32)
        for _,points,color,light in sorted(self.faces,key=lambda f:f[0],reverse=True):
            p=np.asarray(points,np.float32);normal=np.cross(p[1]-p[0],p[2]-p[0]);normal/=max(.001,float(np.linalg.norm(normal)))
            shade=.85+.15*abs(normal[1])+.07*abs(normal[0])
            if light:shade=1.0
            base=np.array(PALETTE[color],np.float32)*shade
            screen=np.column_stack(((128+FOCAL*p[:,0]/p[:,2])*SS,(HORIZON+FOCAL*(EYE-p[:,1])/p[:,2])*SS))
            for index in range(1,len(points)-1):
                ids=[0,index,index+1];v=screen[ids];zz=p[ids,2]
                x0=max(0,int(np.floor(v[:,0].min())));x1=min(w,int(np.ceil(v[:,0].max()))+1)
                y0=max(0,int(np.floor(v[:,1].min())));y1=min(h,int(np.ceil(v[:,1].max()))+1)
                if x0>=x1 or y0>=y1:continue
                den=(v[1,1]-v[2,1])*(v[0,0]-v[2,0])+(v[2,0]-v[1,0])*(v[0,1]-v[2,1])
                if abs(den)<.00001:continue
                gy,gx=np.mgrid[y0:y1,x0:x1];gx=gx+.5;gy=gy+.5
                a=((v[1,1]-v[2,1])*(gx-v[2,0])+(v[2,0]-v[1,0])*(gy-v[2,1]))/den
                b=((v[2,1]-v[0,1])*(gx-v[2,0])+(v[0,0]-v[2,0])*(gy-v[2,1]))/den;c=1-a-b
                inside=(a>=-.00001)&(b>=-.00001)&(c>=-.00001);inv=a/zz[0]+b/zz[1]+c/zz[2]
                dep=np.divide(1,inv,out=np.full_like(inv,np.inf),where=inv>0)
                target_depth=depthbuffer[y0:y1,x0:x1];use=inside&(dep<=target_depth+.025)
                if not np.any(use):continue
                fog=np.clip((dep-240)/1900,0,.78)*(.57 if light else .88)
                face_rgb=base[None,None,:]*(1-fog[:,:,None])+fog_color[None,None,:]*fog[:,:,None]
                canvas[y0:y1,x0:x1][use]=face_rgb[use];emission[y0:y1,x0:x1][use]=face_rgb[use]*light;target_depth[use]=dep[use]
        emitted=Image.fromarray(np.uint8(np.clip(emission,0,255)))
        bloom=np.asarray(emitted.filter(ImageFilter.GaussianBlur(1.5*SS)),np.float32)*.18
        bloom+=np.asarray(emitted.filter(ImageFilter.GaussianBlur(4*SS)),np.float32)*.10
        image=Image.fromarray(np.uint8(np.clip(canvas+bloom,0,255))).resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
        pal=Image.new('P',(1,1));pal.putpalette([v for rgb in PALETTE for v in rgb]+[0]*(768-48))
        return image.quantize(palette=pal,dither=Image.Dither.NONE)



def pack(im):
    data=im.tobytes()
    assert len(data)==WIDTH*HEIGHT and max(data)<16
    return bytes((data[i]<<4)|data[i+1] for i in range(0,len(data),2))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preview-only',action='store_true')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    allframes=[]
    report={'width':WIDTH,'height':HEIGHT,'frames_per_stage':16,'world_period':PERIOD,
            'horizon_viewport_y':HORIZON,'packing':'even X high nibble, odd X low nibble','stages':[]}
    for stage in range(3):
        frames=[]
        for f in range(FRAME_COUNT):
            frames.append(Scene(stage,f*PERIOD/FRAME_COUNT).render())
            if f%4==3:print(f'stage {stage+1}: {f+1}/16',flush=True)
        allframes.append(frames)
        # Independent geometric closure: use the absolute camera position 384,
        # not phase modulo 384, and compare with camera position zero.
        assert Scene(stage,PERIOD).render().tobytes()==frames[0].tobytes(),f'stage {stage+1} loop seam'
        frames[0].convert('RGB').save(OUT/f'stage-{stage+1}-native.png')
        frames[0].convert('RGB').resize((768,540),Image.Resampling.NEAREST).save(OUT/f'stage-{stage+1}-preview.png')
        # GIF uses 10 ms timing units: alternate 30/40 ms to approximate 30 fps.
        frames[0].save(OUT/f'stage-{stage+1}.gif',save_all=True,append_images=frames[1:],duration=[30,30,40,30,30,40,30,30,40,30,30,40,30,30,40,30],loop=0,optimize=False,disposal=2)
        # Round-trip GIF verification detects dropped frames, palette changes,
        # or disposal artifacts; every decoded frame must match the RGB source.
        with Image.open(OUT/f'stage-{stage+1}.gif') as gif:
            assert gif.n_frames==FRAME_COUNT
            gif_duration=0
            for index,frame in enumerate(frames):
                gif.seek(index)
                assert gif.convert('RGB').tobytes()==frame.convert('RGB').tobytes()
                gif_duration+=gif.info['duration']
        raw=b''.join(pack(f) for f in frames)
        assert len(raw)==368640
        from world_codec import compress,decompress
        compressed=compress(raw);assert decompress(compressed)==raw
        assert len(set(f.tobytes() for f in frames))==16
        if not args.preview_only:
            (OUT/f'stage-{stage+1}.bin').write_bytes(raw)
        delta=[]
        for a,b in zip(frames,frames[1:]+frames[:1]):
            delta.append(sum(x!=y for x,y in zip(a.tobytes(),b.tobytes())))
        report['stages'].append({'stage':stage+1,'raw_bytes':len(raw),'compressed_bytes':len(compressed),'unique_frames':16,'zlib_bytes':len(zlib.compress(raw,9)),
            'sha256':hashlib.sha256(raw).hexdigest(),'changed_pixels_per_frame':delta,
            'exact_loop_closure':True,'gif_round_trip_frames':16,'gif_duration_ms':gif_duration})
        print(json.dumps(report['stages'][-1]),flush=True)
    contact=Image.new('RGB',(768,540))
    for stage,frames in enumerate(allframes):
        for row,index in enumerate([0,5,10]):
            contact.paste(frames[index].convert('RGB'),(stage*256,row*180))
    contact.save(OUT/'contact-sheet.png')
    report['palette_rgb8']=PALETTE
    report['palette_rgb5']=PALETTE_RGB5
    report['compressed_total']=sum(stage['compressed_bytes'] for stage in report['stages'])
    assert report['compressed_total']<=400*1024,'world exceeds 400 KiB budget'
    # A fixed wall point at (116,42,640) gets nearer as the camera moves;
    # its screen displacement and projected width demonstrate true perspective.
    report['perspective_probe']=[{'frame':f,'screen_xy':projected((116,42,640-f*PERIOD/FRAME_COUNT)),
        'projected_32_unit_width':round(FOCAL*32/(640-f*PERIOD/FRAME_COUNT),3)} for f in [0,5,10,15]]
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
