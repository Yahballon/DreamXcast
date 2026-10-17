// Covers the SAME SMB settings editor compiled into the PS5 UI.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <functional>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>
#include <unistd.h>
#include <sys/stat.h>
namespace ps5 {std::string rootDir; namespace ime {enum class Kind{Text,Name,Password};inline void forget(){}}}
enum {KeyboardSmb=9};
static bool opened=false;
static ps5::ime::Kind openedKind=ps5::ime::Kind::Text;
static bool openKeyboard(int id,const char*,const char*,const std::string&,size_t,ps5::ime::Kind k){
    assert(id==KeyboardSmb);opened=true;openedKind=k;return true;
}
static void os_notify(const char*,int,const char*){}
struct Row{enum Kind{Toggle,Choice,Slider,Action,Info};Kind kind;std::string label,desc;std::function<std::string()> info;std::function<void()> action;};
struct Category{const char* icon;const char* name;std::vector<Row> rows;};
#include "../src/dreamcastx_smb_settings.inc"
int main(){
    char d[]="/tmp/dreamcastx-smb-XXXXXX";
    assert(mkdtemp(d));ps5::rootDir=std::string(d)+"/";
    const std::string file=ps5::rootDir+"network.cfg";
    {
        std::ofstream out(file);
        for(int i=0;i<8;i++)out<<"path = 192.168.1.10/Games/Disc"<<i<<"\n";
        out<<"user = old\npassword = secret\ndomain = WORKGROUP\n";
    }
    Category cat{"","Library",{}};
    dreamcastx_smb_settings::addRows(cat);
    assert(cat.rows.size()==11);
    assert(dreamcastx_smb_settings::cfg.morePaths.size()==2);
    assert(dreamcastx_smb_settings::fieldText(7)=="********");
    dreamcastx_smb_settings::edit(7);
    assert(opened&&openedKind==ps5::ime::Kind::Password);
    assert(dreamcastx_smb_settings::accept("newPassword"));
    dreamcastx_smb_settings::edit(0);
    assert(dreamcastx_smb_settings::accept("10.0.0.2/Share/Games"));
    const auto old=dreamcastx_smb_settings::cfg.paths[0];
    dreamcastx_smb_settings::edit(0);
    assert(!dreamcastx_smb_settings::accept("notAShare"));
    assert(dreamcastx_smb_settings::cfg.paths[0]==old);
    std::ifstream in(file);
    std::string saved((std::istreambuf_iterator<char>(in)),std::istreambuf_iterator<char>());
    assert(saved.find("path = 10.0.0.2/Share/Games")!=std::string::npos);
    assert(saved.find("path = 192.168.1.10/Games/Disc7")!=std::string::npos);
    assert(saved.find("password = newPassword")!=std::string::npos);
    assert(saved.find("password = secret")==std::string::npos);
    struct stat info{};assert(stat(file.c_str(),&info)==0);
    assert((info.st_mode&077)==0);
    std::remove(file.c_str());
    rmdir(d);
}
