import numpy as np
import struct
def words(v): return struct.pack('<'+'h'*len(v),*[round(x) for x in v])

class Mesh:
    def __init__(self): self.v=[]; self.f=[]; self.objects=0
    def poly(self, points, normal, base=1):
        start=len(self.v); self.v.extend(points)
        ids=list(range(start,start+len(points)))
        if len(ids)==3: ids.append(ids[-1])
        self.f.append((ids,normal,base))
    def box(self,x,y,z,sx,sy,sz,base=1):
        first=len(self.v); self.objects+=1
        points=[(x+a*sx/2,y+b*sy/2,z+c*sz/2) for a in (-1,1) for b in (-1,1) for c in (-1,1)]
        self.v.extend(points)
        for axis in range(3):
            axes=[k for k in range(3) if k!=axis]
            for side in (0,1):
                n=[0,0,0]; n[axis]=2*side-1
                ids=[]
                for u,v in ((0,0),(1,0),(1,1),(0,1)):
                    bits=[0,0,0]; bits[axis]=side;bits[axes[0]]=u;bits[axes[1]]=v
                    ids.append(bits[0]*4+bits[1]*2+bits[2])
                p=np.array([points[j] for j in ids])
                if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),n)<0: ids.reverse()
                self.f.append(([first+j for j in ids],n,base))
    def hull(self,z0,z1,w0,w1):
        first=len(self.v); self.objects+=1
        ring=[(-1,0),(-.78,85),(.78,85),(1,0),(.75,-125),(.4,-185),(-.4,-185),(-.75,-125)]
        for z,w in ((z0,w0),(z1,w1)):
            self.v.extend([(x*w,y,z) for x,y in ring])
        for i in range(8):
            ids=[first+i,first+(i+1)%8,first+8+(i+1)%8,first+8+i]
            p=np.array([self.v[j] for j in ids]);n=np.cross(p[1]-p[0],p[2]-p[0]);n=n/np.linalg.norm(n)
            center=p.mean(axis=0)-np.array([0,-35,(z0+z1)/2])
            if np.dot(n,center)<0: ids.reverse();n=-n
            self.f.append((ids,n.tolist(),1))
        # End caps as triangle fans, shared vertices.
        for start,normal in ((first,[0,0,-1]),(first+8,[0,0,1])):
            for i in range(1,7):
                ids=[start,start+i,start+i+1,start+i+1]
                p=np.array([self.v[j] for j in ids])
                if np.dot(np.cross(p[1]-p[0],p[2]-p[0]),normal)<0: ids.reverse()
                self.f.append((ids,normal,1))
    def data(self):
        assert len(self.v)<=255 and len(self.f)<=255,(len(self.v),len(self.f))
        vb=b''.join(words(v) for v in self.v)
        fb=b''.join(bytes(ids)+words([n*16384 for n in normal])+bytes([base]) for ids,normal,base in self.f)
        return bytes([len(self.v),len(self.f)])+struct.pack('<HH',len(vb),len(fb))+vb+fb

