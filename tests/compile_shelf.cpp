// Host regression test: validates the exact native image path and bounds.
// The stub deliberately offers NO AddImageQuad, AddQuadFilled, PrimReserve etc.
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>
using ImU32=uint32_t;using ImTextureID=void*;
struct ImVec2{float x,y;};
struct ImDrawList{
    int clipDepth=0;
    void AddLine(ImVec2,ImVec2,ImU32,float){}
    void PushClipRect(ImVec2,ImVec2,bool){clipDepth++;}
    void PopClipRect(){clipDepth--;}
};
namespace col{constexpr ImU32 accent=1,dim=2,text=3;ImU32 rgba(int,int,int,int){return 0;}}
struct Game{std::string title;};
struct Shelf{std::vector<size_t>items;int focus=0;float focusAnim=-1;std::string name;};
struct Library{std::vector<Shelf>shelves;int shelf=0;bool details=false;};
static Library lib;static std::vector<Game> games;
static constexpr float W=1920,H=1080,S=1.f;
enum Motion{MotionOff,MotionOn};
Motion motion(){return MotionOff;}
ImVec2 V(float x,float y){return{x,y};}
ImU32 alpha(ImU32 c,float){return c;}
float approach(float,float y,float){return y;}
struct Drawn{float x,y,w,h;};
static std::vector<Drawn> images,boxes;
void rect(ImDrawList*,float x,float y,float w,float h,ImU32,float=0.f){
    if(w>120.f&&h>250.f)boxes.push_back({x,y,w,h});
}
void outline(ImDrawList*,float,float,float,float,ImU32,float,float){}
void imageFill(ImDrawList*,ImTextureID,float x,float y,float w,float h,float){
    assert(std::isfinite(x)&&std::isfinite(y)&&w>0.f&&h>0.f);
    images.push_back({x,y,w,h});
}
void placeholder(ImDrawList*,const Game&,float,float,float,float,float){assert(false);}
void text(ImDrawList*,int,float,float,float,ImU32,const char*){}
ImTextureID coverTexture(Game&){return (ImTextureID)(uintptr_t)1;}
int bold(){return 0;}int regular(){return 0;}
ImVec2 textSize(int,int,const char*){return{100.f,24.f};}
std::string fit(int,float,const std::string& s,float){return s;}
std::string metaText(Game&){return "Europe";}
#include "../src/dreamcastx_shelf.inc"
int main(){
    const auto bounds=dreamcastXArtworkBounds(100,200,326,452);
    assert(bounds.x>100&&bounds.y>200);
    assert(bounds.x+bounds.w<=426&&bounds.y+bounds.h<=652);
    ImDrawList dl;
    Shelf sh;sh.items={0,1,2,3,4};sh.focus=2;sh.name="All games";
    lib.shelves.push_back(sh);
    games={{"A"},{"B"},{"Sonic"},{"D"},{"E"}};
    drawDreamcastXShelf(&dl,&games[2],false);
    assert(dl.clipDepth==0);
    assert(images.size()==5);
    // Every cover sits directly under its case header, never outside.
    for(auto &b:images){
        assert(b.x>40.f&&b.y>224.f&&b.x+b.w<W-30.f&&b.y+b.h<795.f);
        assert(b.w<340.f&&b.h<460.f);
    }
    const auto &center=images[2];
    // Draw order is farthest-first; find the largest cover instead.
    float maxW=0.f;Drawn hero{};
    for(const auto &a:images)if(a.w>maxW){maxW=a.w;hero=a;}
    assert(hero.w>280.f&&hero.h>370.f);
    assert(std::fabs((hero.x+hero.w/2.f)-W/2.f)<25.f);
    assert(hero.y>225.f&&hero.y+hero.h<795.f);
    // Side games cannot suddenly jump to the screen corner while switching.
    sh.focus=4;lib.shelves[0].focus=4;images.clear();
    drawDreamcastXShelf(&dl,&games[4],false);
    assert(images.size()==5);
    // Far cases may be partly offscreen while browsing toward the end,
    // but must remain near the viewport and never jump thousands of pixels.
    for(auto &a:images){
        assert(a.x>-250.f&&a.x+a.w<W+250.f);
        assert(a.y>200.f&&a.y+a.h<795.f);
    }
}
