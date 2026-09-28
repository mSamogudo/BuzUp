"""Recorta as tres viaturas da fotografia da frota, numa passagem so.

Correr de dentro de `frontend/scripts/`:

    python3 extrair-frota-cheetah.py

Escreve sprinter.webp, hiace-bus.webp e hiace-van.webp, que depois se copiam
para `public/landing/cheetah/frota/`, e imprime as posicoes em percentagem que
o componente `FrotaChegada.tsx` traz escritas.

Porque nao um limiar de cor: as carrinhas sao BRANCAS e o ceu tambem, e o
limiar comia-lhes os tejadilhos. Em vez disso varre-se cada COLUNA de cima ate
encontrar a primeira coisa que nao e ceu — o branco do tejadilho fica, porque a
varredura para nele em vez de o apagar.

As caixas cortam na FRONTEIRA DE OCLUSAO: cada viatura acaba onde o nariz da
seguinte comeca. Nao se perde nada, porque o que fica de fora ja estava
escondido atras da vizinha. As posicoes ficam gravadas em percentagem da
fotografia — e isso que as faz reconstruir a fila exacta quando assentam.
"""
from PIL import Image
from collections import deque
from pathlib import Path
import json, os

ORIGEM = Path(__file__).with_name("frota-cheetah-origem.webp")
im = Image.open(ORIGEM).convert("RGB"); W, H = im.size
VIATURAS = [("sprinter",(28,383,697,766)), ("hiace-bus",(688,450,1172,752)), ("hiace-van",(1156,474,1646,736))]

def extrair(nome, caixa):
    x0,y0,_,_ = caixa
    rec = im.crop(caixa); rw,rh = rec.size; px = rec.load()
    am = [px[x,y] for y in range(0,5) for x in range(0,rw,7)]
    cr,cg,cb = (sum(c[i] for c in am)/len(am) for i in range(3))
    e_ceu  = lambda r,g,b: abs(r-cr)<26 and abs(g-cg)<26 and abs(b-cb)<26
    e_chao = lambda r,g,b: abs(r-g)<16 and abs(g-b)<16 and 88<r<175

    m = [[False]*rw for _ in range(rh)]
    for x in range(rw):
        topo = rh
        for y in range(rh):
            if not e_ceu(*px[x,y]): topo = y; break
        fundo = -1
        for y in range(rh-1, topo, -1):
            if not e_chao(*px[x,y]): fundo = y; break
        for y in range(topo, fundo+1): m[y][x] = True

    visto=[[False]*rw for _ in range(rh)]; melhor,mn=None,0
    for yy in range(rh):
        for xx in range(rw):
            if m[yy][xx] and not visto[yy][xx]:
                f=deque([(xx,yy)]); visto[yy][xx]=True; bl=[]
                while f:
                    x,y=f.popleft(); bl.append((x,y))
                    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                        nx,ny=x+dx,y+dy
                        if 0<=nx<rw and 0<=ny<rh and m[ny][nx] and not visto[ny][nx]:
                            visto[ny][nx]=True; f.append((nx,ny))
                if len(bl)>mn: melhor,mn=bl,len(bl)

    out = Image.new("RGBA",(rw,rh),(0,0,0,0)); sp = out.load()
    for x,y in melhor: sp[x,y] = (*px[x,y],255)
    bb = out.getbbox(); out = out.crop(bb); ow,oh = out.size; op = out.load()

    # 1. Fora a cauda de alcatrao CLARO por baixo da sombra.
    corte = oh
    for y in range(oh-1, int(oh*0.7), -1):
        vis=[x for x in range(ow) if op[x,y][3]>0]
        if not vis: corte=y; continue
        lum=[0.2126*op[x,y][0]+0.7152*op[x,y][1]+0.0722*op[x,y][2] for x in vis]
        if sum(lum)/len(lum)>105 and sum(1 for l in lum if l<95)/len(lum)<0.25: corte=y
        else: break
    if corte<oh: out = out.crop((0,0,ow,corte)); ow,oh = out.size; op = out.load()

    # 2. A sombra que sobra e um BLOCO rectangular. Esbatida, le-se como sombra;
    #    em bruto, le-se como recorte roto. A rampa nunca vai a zero de todo:
    #    uma viatura sem contacto com o chao parece a flutuar.
    banda = max(8, round(oh*0.13))
    inicio = oh - banda
    for y in range(inicio, oh):
        t = (y-inicio)/banda
        fy = 1 - 0.88*(t**1.35)
        vis=[x for x in range(ow) if op[x,y][3]>0]
        if not vis: continue
        e,d = min(vis),max(vis); larg = max(d-e,1)
        for x in vis:
            u=(x-e)/larg
            fx = min(1.0, min(u,1-u)/0.10)
            op[x,y] = (*op[x,y][:3], int(op[x,y][3]*fy*fx))

    out.save(f"{nome}.webp", format="WEBP", quality=88, method=6)
    meta = {"f":f"{nome}.webp","x":round(100*(x0+bb[0])/W,3),"y":round(100*(y0+bb[1])/H,3),
            "w":round(100*ow/W,3),"h":round(100*oh/H,3)}
    print(f"{nome:10s} {ow}x{oh}  {os.path.getsize(nome+'.webp')//1024:3d}KB   x={meta['x']:5.1f}% y={meta['y']:5.1f}% w={meta['w']:5.1f}% h={meta['h']:5.1f}%")
    return meta

metas=[extrair(n,c) for n,c in VIATURAS]
json.dump(metas, open("frota-meta.json","w"), indent=2)
comp = Image.new("RGB",(W,H),(248,199,15))
for m in metas:
    v=Image.open(m["f"]); comp.paste(v,(round(W*m["x"]/100),round(H*m["y"]/100)),v)
comp.crop((0,int(H*0.35),W,int(H*0.92))).resize((W//2,int(H*0.57)//2), Image.LANCZOS).save("composto-meio.png")
print("proporcao da fotografia:", round(W/H,4))
