import sys,re,os
out=sys.argv[1]; dirs=sys.argv[2:]; CELL=320; COLS=4
def readppm(p):
    b=open(p,'rb').read(); parts=b.split(maxsplit=4); w,h=int(parts[1]),int(parts[2]); return w,h,bytearray(parts[4])
imgs=[]
for d in dirs:
    w,h,px=readppm(d+'/map.ppm'); t=open(d+'/dump.txt').read()
    def mark(x,y,c,r=1):
        for yy in range(y-r,y+r+1):
            for xx in range(x-r,x+r+1):
                if 0<=xx<w and 0<=yy<h: px[(yy*w+xx)*3:(yy*w+xx)*3+3]=bytes(c)
    for m in re.finditer(r' inv=\((\d+),(\d+)\)',t): mark(int(m[1]),int(m[2]),(255,0,0),2)
    m=re.search(r' entry=\((\d+),(\d+)\)',t); m and mark(int(m[1]),int(m[2]),(255,0,255),2)
    m=re.search(r' exit=\((\d+),(\d+)\)',t); m and mark(int(m[1]),int(m[2]),(0,255,255),2)
    m=re.search(r'center=\((\d+),(\d+)\)',t); m and mark(int(m[1]),int(m[2]),(255,255,255),2)
    imgs.append((w,h,px))
rows=(len(imgs)+COLS-1)//COLS; W=COLS*CELL; H=rows*CELL; canvas=bytearray(b'\x20'*W*H*3)
for i,(w,h,px) in enumerate(imgs):
    ox=(i%COLS)*CELL; oy=(i//COLS)*CELL; s=max(w,h)
    for y in range(CELL-4):
        for x in range(CELL-4):
            sx=x*s//(CELL-4); sy=y*s//(CELL-4)
            if sx<w and sy<h:
                o=((oy+y)*W+ox+x)*3; canvas[o:o+3]=px[(sy*w+sx)*3:(sy*w+sx)*3+3]
open(out,'wb').write(b'P6 %d %d 255\n'%(W,H)+canvas)
