from PIL import Image, ImageDraw, ImageFont, ImageFilter
FD='/var/www/html/Twilight/Game/Content/Fonts/'
W,H=1280,686
def is_arm(c): return 0x0530<=ord(c)<=0x058F
def runs(t):
    out=[]; cur=''; ca=None
    for c in t:
        a = is_arm(c) if c!=' ' else ca
        if ca is None: ca=a
        if a!=ca and cur: out.append((cur,ca)); cur=''; ca=a
        cur+=c
    if cur: out.append((cur,ca))
    return out
def draw_mixed(d, y, text, arm, lat, fill):
    rs=runs(text); widths=[d.textlength(s,font=(arm if a else lat)) for s,a in rs]
    x=(W-sum(widths))/2
    for (s,a),w in zip(rs,widths): d.text((x,y),s,font=(arm if a else lat),fill=fill); x+=w
def card(name,title,sub,bg,lines=()):
    bg=Image.open('cards/'+bg).convert('RGB').crop((0,0,1584,850)).resize((W,H)).filter(ImageFilter.GaussianBlur(4))
    bg=Image.blend(bg, Image.new('RGB',(W,H),(12,6,16)), 0.5)
    d=ImageDraw.Draw(bg)
    sz=84
    while sz>40 and d.textlength(title,font=ImageFont.truetype(FD+'NotoSerifArmenian-Black.ttf',sz))>W-120: sz-=4
    draw_mixed(d,215+(84-sz)//2,title,ImageFont.truetype(FD+'NotoSerifArmenian-Black.ttf',sz),ImageFont.truetype(FD+'NotoSerif-Black.ttf',sz),(255,226,170))
    draw_mixed(d,340,sub,ImageFont.truetype(FD+'NotoSansArmenian-Regular.ttf',34),ImageFont.truetype(FD+'NotoSans-Regular.ttf',34),(240,232,220))
    y=410
    for l in lines:
        draw_mixed(d,y,l,ImageFont.truetype(FD+'NotoSansArmenian-Regular.ttf',28),ImageFont.truetype(FD+'NotoSans-Regular.ttf',28),(225,215,205)); y+=42
    bg.save('cards/%s.png'%name)
card('00_title','ԾԻՐԱՆԻ','Երեք առասպել · երեք խաղ','bg_title.jpg',['«Թռիչք դեպի դիցաբանության խորքերը»','Unreal Engine 5 · Սամվել Խաչատրյան'])
card('01_vahagn','ՎԱՀԱԳՆ ՎԻՇԱՊԱՔԱՂ','Գլուխ I · կրակի և կայծակի աստվածը','bg_vahagn.jpg',['Սևանա լիճ և Գեղամա լեռներ · օձանման վիշապներ'])
card('02_hayk','ՀԱՅԿ ՆԱՀԱՊԵՏ','Գլուխ II · եռաթև նետը','bg_hayk.jpg',['Վանա լճի ափ · Բելը բլրի վրա՝ իր զորքի հետևում'])
card('03_aralez','ԱՐԱԼԵԶՆԵՐ','Գլուխ III · Արայի դաշտը','bg_aralez.jpg',['Արարատյան դաշտ · Արալեզները կենդանացնում են ընկածներին'])
card('04_end','ԱՇԽԱՏԱՆՔԸ ՇԱՐՈՒՆԱԿՎՈՒՄ Է','Սա ընթացիկ տարբերակն է · դեռ շատ բան կա անելու','bg_end.jpg',[])
