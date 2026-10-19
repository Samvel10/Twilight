import sys
from PIL import Image, ImageDraw
out=sys.argv[1]; cols=int(sys.argv[2]); fs=sys.argv[3:]
ims=[Image.open(f).convert('RGB') for f in fs]; w=800; h=int(ims[0].height*w/ims[0].width)
S=Image.new('RGB',(cols*w,((len(ims)+cols-1)//cols)*h))
for i,(im,f) in enumerate(zip(ims,fs)):
    im=im.resize((w,h)); d=ImageDraw.Draw(im); d.rectangle((0,0,260,22),fill=(0,0,0)); d.text((5,5),f.split('/')[-1][:-4],fill=(255,255,0))
    S.paste(im,((i%cols)*w,(i//cols)*h))
S.save(out,quality=88)
