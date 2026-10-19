import sys
from PIL import Image
out=sys.argv[1]; fs=sys.argv[2:]; ims=[Image.open(f).convert('RGB') for f in fs]
cols=min(3,len(ims)); w,h=ims[0].size; rows=(len(ims)+cols-1)//cols
S=Image.new('RGB',(w*cols,h*rows))
for i,im in enumerate(ims): S.paste(im.resize((w,h)),((i%cols)*w,(i//cols)*h))
S.thumbnail((2400,1600)); S.save(out,quality=90)
