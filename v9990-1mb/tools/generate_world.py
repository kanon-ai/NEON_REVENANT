"""Five native V9990 environments; preserves all 16 phases of the original worlds."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
from PIL import Image,ImageDraw
from world_original import Scene,pack,PERIOD,SS,WIDTH,HEIGHT,PALETTE
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/world';OUT.mkdir(parents=True,exist_ok=True)
class Expansion(Scene):
    def __init__(self,dawn,phase):
        super().__init__(0,phase);self.dawn=dawn
    def city(self):
        # Low coastal deck exposes water, repeated pylons and distant skyline.
        for side in [-1,1]:
            self.ground(*sorted([side*108,side*2200]),22,2100,2 if self.dawn else 1,y=-25)
        for k in range(-1,23):
            z=k*96-self.phase
            for side in [-1,1]:
                for n in range(5):
                    x=side*(125+n*63)
                    self.ground(x-19,x+19,z+12+n*9,z+14+n*9,13 if self.dawn and n%2 else 4,y=-24.8,light=.12)
                self.box(*sorted([side*111,side*121]),-25,48,z+4,z+16,front=3,side=2,top=8)
                self.front(*sorted([side*111,side*120]),38,41,z+3,14 if self.dawn else 6,light=.5)
                if k%2==0:
                    self.box(*sorted([side*243,side*316]),-23,33,z+18,z+72,front=8,side=2,top=13 if self.dawn else 3)
                    for rib in range(6):
                        self.front(*sorted([side*(247+rib*10),side*(249+rib*10)]),-18,29,z+17.8,3 if self.dawn else 4)
                if k%4==0:
                    self.box(-144,144,207,215,z,z+16,front=3,side=2,top=9)
                    for span in range(4):
                        zz=z+span*96
                        high=205-span*39
                        self.face([(side*139,high,zz),(side*139,high-3,zz),(side*139,high-42,zz+96),(side*139,high-39,zz+96)],4)
                # A bridge structure every four cells; all geometry loops at 384.
                if k%4==0:
                    self.box(*sorted([side*128,side*144]),0,210,z,z+23,front=8,side=2,top=4)
                    self.front(*sorted([side*130,side*133]),25,199,z-1,14 if self.dawn else 5,light=.3)
                    self.box(*sorted([side*143,side*210]),110,118,z+2,z+12,front=3,side=2,top=4)
                    self.sign(side,side*143,88,z+7,37,12,'ION',13 if self.dawn else 5)
                if k%4==2:
                    # Dock cranes, or fractured elevated buildings at daybreak.
                    height=90 if self.dawn else 165
                    self.box(*sorted([side*185,side*213]),-25,height,z,z+48,front=8,side=2,top=4)
                    self.box(*sorted([side*161,side*306]),height,height+9,z+5,z+16,front=13 if self.dawn else 3,side=2,top=4)
                    if self.dawn:
                        for level in range(3):self.front(*sorted([side*186,side*211]),18+level*21,22+level*21,z-.4,14,light=.25)
                    else:self.side(side*166,25,height,z+6,z+7,5,light=.15)
        if self.dawn:
            for k in range(-1,6):
                z=k*384-self.phase+260
                self.box(-190,-114,0,70,z,z+58,front=8,side=2,top=13)
                self.box(145,230,0,120,z+90,z+146,front=3,side=2,top=14)
    def background(self):
        h,w=HEIGHT*SS,WIDTH*SS;yy,xx=np.mgrid[:h,:w]
        if self.dawn:
            glow=np.exp(-(((xx/SS-159)/83)**2+((yy/SS-54)/33)**2))
            rgb=np.array([17,20,36])+glow[:,:,None]*np.array([167,74,36])
        else:
            glow=np.exp(-(((xx/SS-128)/84)**2+((yy/SS-57)/27)**2))
            rgb=np.array([5,10,23])+glow[:,:,None]*np.array([27,48,62])
        im=Image.fromarray(np.uint8(np.clip(rgb,0,255)));d=ImageDraw.Draw(im)
        if self.dawn:d.ellipse((143*SS,34*SS,175*SS,66*SS),fill=(245,157,79))
        else:d.ellipse((48*SS,16*SS,62*SS,30*SS),fill=(94,135,157))
        for layer in range(2):
            for k in range(29):
                x=k*10-10;top=43+(k*17+layer*9)%15
                d.rectangle((x*SS,top*SS,(x+6)*SS,68*SS),fill=(14+layer*8,24+layer*9,36+layer*9))
        return np.asarray(im,dtype=np.float32)
def main():
    report=[]
    for stage in range(5):
        # --new-only retains verified original environments for quick iteration.
        if '--new-only' in sys.argv and stage in (1,2,3):continue
        frames=[(Expansion(stage==4,i*PERIOD/16) if stage in (0,4) else Scene(stage-1,i*PERIOD/16)).render() for i in range(16)]
        raw=b''.join(pack(f) for f in frames);assert len(raw)==368640
        (OUT/f'stage-{stage+1}.bin').write_bytes(raw)
        frames[0].resize((768,540),Image.Resampling.NEAREST).save(OUT/f'stage-{stage+1}-preview.png')
        frames[0].save(OUT/f'stage-{stage+1}-motion.gif',save_all=True,append_images=frames[1:],duration=[30,40,30]*5+[30],loop=0,optimize=False)
        info=dict(stage=stage,unique_frames=len(set(f.tobytes() for f in frames)),sha256=hashlib.sha256(raw).hexdigest())
        assert info['unique_frames']==16;report.append(info);print(info,flush=True)
    (OUT/'campaign-worlds.json').write_text(json.dumps(report,indent=2))
if __name__=='__main__':main()
