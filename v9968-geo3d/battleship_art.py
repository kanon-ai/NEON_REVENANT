"""Hand-authored, low-frequency deck markings for the final ship only."""
from PIL import Image,ImageDraw

def deck_texture(palette):
    im=Image.new('P',(64,64));im.putpalette(palette)
    def ink(rgb):
        return min(range(128,224),key=lambda i:sum((palette[i*3+j]-rgb[j])**2 for j in range(3)))
    dark=ink((16,26,39));edge=ink((43,59,73));steel=ink((78,98,112));light=ink((133,155,165))
    d=ImageDraw.Draw(im);d.rectangle((0,0,63,63),fill=dark)
    # Broad plates, restrained bevels, dark separation and large identifiers.
    for left,right in [(3,22),(25,38),(41,60)]:
        for top,bottom in [(3,20),(23,40),(43,60)]:
            d.polygon([(left+2,top),(right-2,top),(right,top+3),(right,bottom-2),(right-2,bottom),(left,bottom),(left,top+3)],fill=steel)
            d.line((left+2,top,right-2,top,right,top+3),fill=light)
            d.line((right,bottom-2,right-2,bottom,left,bottom),fill=edge)
    for x in (10,51):
        d.rectangle((x,7,x+2,30),fill=12)
        d.rectangle((x,33,x+2,37),fill=13)
        d.rectangle((x-4,46,x+6,58),fill=dark)
        for y in (48,52,56):d.line((x-3,y,x+5,y),fill=edge)
    d.polygon([(31,5),(35,11),(31,16),(28,11)],fill=7)
    d.line((30,27,30,38),fill=light,width=2)
    d.line((34,27,34,38),fill=light,width=2)
    return im

def sector_texture(theme,palette):
    im=Image.new('P',(32,32));im.putpalette(palette)
    def ink(rgb):return min(range(128,224),key=lambda i:sum((palette[i*3+j]-rgb[j])**2 for j in range(3)))
    dark=ink((15,25,39));navy=ink((35,52,68));steel=ink((94,115,128));silver=ink((155,177,183))
    d=ImageDraw.Draw(im);d.rectangle((0,0,31,31),fill=navy)
    if theme==0:
        # Harbor equipment: big service covers and warning chevrons.
        for box in [(2,3,12,27),(19,3,29,27)]:
            d.rectangle(box,fill=steel,outline=dark)
            for y in (8,18):d.line((box[0]+1,y,box[2]-1,y),fill=navy)
        for y in (5,12,19):d.line((13,y,16,y+3,18,y),fill=7,width=2)
        d.rectangle((4,24,10,25),fill=12);d.rectangle((21,24,27,25),fill=12)
    elif theme==1:
        # Two straight armor lanes, avoiding a triangular outline in the paint.
        for x in (2,20):
            d.rectangle((x,2,x+9,29),fill=steel,outline=dark)
            d.line((x+1,3,x+8,3),fill=silver)
            d.line((x+2,12,x+2,27),fill=7,width=2)
            d.rectangle((x+4,6,x+7,10),fill=dark)
        d.rectangle((12,13,19,21),fill=navy)
    elif theme==2:
        # Industrial carrier: broad armored decks, orange launch channels.
        for x in (2,19):
            d.rectangle((x,2,x+10,29),fill=steel,outline=dark)
            for y in (7,22):d.rectangle((x+2,y,x+8,y+2),fill=dark)
            d.line((x+4,11,x+4,18),fill=7,width=3)
        d.rectangle((14,1,17,30),fill=dark)
        for y in (4,12,20):d.line((14,y,17,y),fill=8)
    else:
        # Rectilinear blast doors and cooling slots; no eye-like concentric marks.
        for x in (2,12,22):
            d.rectangle((x,2,x+7,29),fill=steel,outline=dark)
            d.line((x+1,3,x+6,3),fill=silver)
            for y in (8,12,16):d.line((x+2,y,x+5,y),fill=dark)
            d.rectangle((x+2,23,x+5,24),fill=12)
    return im
