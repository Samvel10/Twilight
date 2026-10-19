import json,struct,sys,os
f,od=sys.argv[1],sys.argv[2]; os.makedirs(od,exist_ok=True)
b=open(f,'rb').read(); n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n]); bin_=b[28+n:]
for i,im in enumerate(j.get('images',[])):
    bv=j['bufferViews'][im['bufferView']]; o=bv.get('byteOffset',0)
    ext='png' if 'png' in im.get('mimeType','') else 'jpg'
    open(f'{od}/img{i}.{ext}','wb').write(bin_[o:o+bv['byteLength']])
for m in j['materials']: print(m)
