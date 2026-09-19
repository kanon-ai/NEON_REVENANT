"""Selected native MSX1 dawn material treatment, authored offline."""
import math
import numpy as np
from PIL import Image,ImageDraw
from pcg_expansion_art import Scene,PERIOD
from pcg_art import _two_colors,_approximate

class Dawn(Scene):
    solid_materials=True
    def background(self,step):
        im=Image.new('L',(256,160),0);d=ImageDraw.Draw(im)
        shift=round(2*math.sin(self.phase/PERIOD*math.tau))
        for y,c in ((0,12),(24,13),(40,14),(56,11)):
            d.rectangle((0,y,255,65),fill=c)
        d.ellipse((113,29,147,63),fill=7)
        for k in range(19):
            x=k*16-15+shift;top=39-(k*11%24)
            d.rectangle((x,top,x+10,66),fill=0)
            if k%3==0:d.rectangle((x+3,top+4,x+4,top+5),fill=10)
        return np.array(im.resize((256//step,160//step),Image.Resampling.NEAREST))

def generate_frames():
    frames=np.ones((16,192,256),dtype=np.uint8)
    for p in range(16):frames[p,16:176]=Dawn(4,p*PERIOD/16).render(1)
    return _approximate(_two_colors(frames),512)
