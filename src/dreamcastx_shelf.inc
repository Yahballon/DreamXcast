/*
 * PS5DreamcastX v0.1.5 -- conservative, PS5-tested CoverFlow.
 * Based on the known-good 0.1.3 case renderer. We deliberately avoid
 * AddImageQuad/AddQuadFilled/PrimReserve for artwork: the custom PS5
 * texture renderer scattered these vertices in v0.1.4 on real hardware.
 *
 * The side cases convey depth by scale/spacing. No fake perspective
 * textured quads or reflection buffers until they pass a hardware test.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
struct DreamcastXCaseBounds { float x,y,w,h; };
static DreamcastXCaseBounds dreamcastXArtworkBounds(float x,float y,float w,float h)
{
    const float spine=std::max(10.f,w*0.047f);
    const float header=std::max(23.f,h*0.065f);
    const float pad=3.f;
    return {x+spine+pad,y+header+1.f,
            std::max(1.f,w-spine-2.f*pad),
            std::max(1.f,h-header-5.f)};
}

static void drawDreamcastXCase(ImDrawList* dl,Game& g,
                              float x,float y,float w,float h,
                              bool selected,float distance)
{
    const float r=std::max(6.f,w*0.024f);
    const float spine=std::max(10.f,w*0.047f);
    const float header=std::max(23.f,h*0.065f);
    const float fade=std::clamp(1.f-distance*0.11f,0.60f,1.f);

    // Bounded shadow (no extended polygons / image reflections).
    rect(dl,x+5.f,y+7.f,w,h,col::rgba(0,0,0,(int)(75.f*fade)),r);
    if(selected)
        rect(dl,x-5.f,y-5.f,w+10.f,h+10.f,alpha(col::accent,0.17f),r+3.f);
    // White jewel case and a slim 3D-like spine. All primitives use the
    // proven axis-aligned rect/outline helpers from v0.1.3.
    rect(dl,x,y,w,h,col::rgba(230,235,240,255),r);
    rect(dl,x+spine,y+3.f,w-spine-4.f,h-6.f,
         col::rgba(248,249,251,255),std::max(2.f,r-2.f));
    rect(dl,x+2.f,y+3.f,spine-2.f,h-6.f,
         col::rgba(151,163,178,244),2.f);
    dl->AddLine(V(x+spine,y+4.f),V(x+spine,y+h-4.f),
                col::rgba(255,255,255,190),1.2f*S);
    // A small, independent header. Artwork starts immediately below it.
    rect(dl,x+spine+2.f,y+2.f,w-spine-6.f,header-2.f,
         col::rgba(245,247,250,255),2.f);
    const float font=std::clamp(header*0.50f,12.f,19.f);
    text(dl,bold(),font,x+spine+8.f,y+header*0.16f,
         col::rgba(82,104,129,255),"DREAMCAST");

    const DreamcastXCaseBounds art=dreamcastXArtworkBounds(x,y,w,h);
    rect(dl,art.x,art.y,art.w,art.h,col::rgba(13,20,30,255),2.f);
    const ImTextureID image=coverTexture(g);
    if(image!=ImTextureID())
    {
        // imageFill() is the same PS5-proven image path used by v0.1.3;
        // it crops to the case face without any custom draw-list geometry.
        imageFill(dl,image,art.x,art.y,art.w,art.h,1.f);
    }
    else
        placeholder(dl,g,art.x,art.y,art.w,art.h,1.f);

    dl->AddLine(V(x+spine+1.f,y+header),V(x+w-4.f,y+header),
                col::rgba(135,155,177,110),1.f*S);
    outline(dl,x,y,w,h,
            selected?alpha(col::accent,0.95f):col::rgba(152,173,194,200),
            r,selected?3.2f:1.4f);
}

void drawDreamcastXShelf(ImDrawList* dl,Game* focused,bool selectDisk)
{
    if(lib.shelves.empty()) return;
    Shelf& sh=lib.shelves[std::clamp(lib.shelf,0,(int)lib.shelves.size()-1)];
    sh.focusAnim=motion()==MotionOff||sh.focusAnim<0.f?
                 (float)sh.focus:approach(sh.focusAnim,(float)sh.focus,13.f);
    const float cx=W*0.5f,cy=472.f;
    const int count=(int)sh.items.size();
    const int start=std::max(0,(int)std::floor(sh.focusAnim)-5);
    const int end=std::min(count-1,(int)std::ceil(sh.focusAnim)+5);
    std::vector<int> order;
    for(int i=start;i<=end;i++) order.push_back(i);
    std::sort(order.begin(),order.end(),[&](int a,int b){
        return std::fabs(a-sh.focusAnim)>std::fabs(b-sh.focusAnim);
    });

    // Prime the selected game and both neighbours *before* the farthest-first
    // painting pass. Downloads/scraping and decoding remain asynchronous;
    // this also makes the centre cover the first requested texture on boot.
    for(int radius=0;radius<=2;radius++) {
        for(int dir=-1;dir<=1;dir+=2) {
            if(radius==0 && dir>0) continue;
            const int index=sh.focus+radius*dir;
            if(index>=0 && index<count)
                (void)coverTexture(games[sh.items[(size_t)index]]);
        }
    }

    // The clip is limited to game cases only. The title and footer are drawn
    // outside this clip to avoid the cut-off corruption seen in v0.1.4.
    dl->PushClipRect(V(38.f,224.f),V(W-38.f,795.f),true);
    for(int i:order)
    {
        Game& game=games[sh.items[(size_t)i]];
        const float d=(float)i-sh.focusAnim;
        const float distance=std::fabs(d);
        const float scale=std::max(0.56f,1.f-0.17f*distance);
        const float w=326.f*scale;
        const float h=452.f*scale;
        const float x=cx+d*266.f-w*0.5f;
        const float y=cy+std::min(distance,3.f)*13.f-h*0.5f;
        const bool selected=(i==sh.focus&&distance<0.5f&&!lib.details);
        drawDreamcastXCase(dl,game,x,y,w,h,selected,distance);
    }
    dl->PopClipRect();

    const std::string heading=(selectDisk?"CHOOSE DISC":"DREAMCAST LIBRARY")
        +std::string("   /   ")+sh.name;
    text(dl,bold(),26,96.f,148.f,col::dim,heading.c_str());
    const std::string number=std::to_string(count?sh.focus+1:0)+
                             " / "+std::to_string(count);
    const ImVec2 ns=textSize(regular(),23,number.c_str());
    text(dl,regular(),23,W-96.f-ns.x,148.f,col::dim,number.c_str());
    if(focused)
    {
        const std::string title=fit(bold(),43,focused->title,W-310.f);
        const ImVec2 ts=textSize(bold(),43,title.c_str());
        text(dl,bold(),43,(W-ts.x)*0.5f,194.f,col::text,title.c_str());
        const std::string meta=metaText(*focused);
        const ImVec2 ms=textSize(regular(),23,meta.c_str());
        text(dl,regular(),23,(W-ms.x)*0.5f,864.f,col::dim,meta.c_str());
    }
}
