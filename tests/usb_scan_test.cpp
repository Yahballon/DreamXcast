#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <dirent.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <sys/stat.h>
#include <vector>
#include "../src/dreamcastx_usb.inc"

int main()
{
    namespace fs=std::filesystem;
    char tmp[]="/tmp/ps5dreamcastx-usb-XXXXXX";
    char* root=mkdtemp(tmp);
    assert(root);
    const std::string prefix=std::string(root)+"/usb";
    const std::string base=prefix+"0/PS5DreamcastX";
    fs::create_directories(base+"/games");
    fs::create_directories(base+"/Games/Extra");
    fs::create_directories(prefix+"1/PS5DreamcastX");
    fs::create_directories(prefix+"2/Dreamcast");
    fs::create_directories(prefix+"3/unrelated");
    fs::create_directories(prefix+"4/ps5dreamcastx/games");

    // Regression: 6 different game images split across the USB root and
    // multiple child folders. Previous code returned only root/games,
    // leaving four of these six games invisible.
    const std::vector<std::string> sample={
        "CrazyTaxi.chd","DinoCrisis.CHD",
        "games/SonicAdventure.gdi","games/SoulCalibur.GDI",
        "Games/Extra/ReVolt.cdi","Games/Extra/SkiesOfArcadia.CUE"
    };
    for(const auto& file:sample){
        fs::create_directories(fs::path(base+"/"+file).parent_path());
        std::ofstream(base+"/"+file).put('x');
    }
    std::ofstream(base+"/not-a-game.txt").put('x');
    auto dirs=discoverDreamcastXUsbDirs(prefix,8);
    std::sort(dirs.begin(),dirs.end());
    assert(dirs.size()==4);
    assert(std::find(dirs.begin(),dirs.end(),base)!=dirs.end());
    assert(std::find(dirs.begin(),dirs.end(),base+"/games")==dirs.end());
    assert(std::find(dirs.begin(),dirs.end(),prefix+"1/PS5DreamcastX")!=dirs.end());
    assert(std::find(dirs.begin(),dirs.end(),prefix+"2/Dreamcast")!=dirs.end());
    assert(std::find(dirs.begin(),dirs.end(),prefix+"4/ps5dreamcastx")!=dirs.end());
    // Model hostfs::DirectoryTree's depth-first recursion with the same
    // extension normalization as the patched native Flycast scanner.
    int found=0;
    for(const auto& entry:fs::recursive_directory_iterator(base)) {
        if(!entry.is_regular_file()) continue;
        std::string ext=entry.path().extension().string();
        std::transform(ext.begin(),ext.end(),ext.begin(),[](unsigned char c){return (char)tolower(c);});
        if(ext==".chd"||ext==".gdi"||ext==".cdi"||ext==".cue") ++found;
    }
    assert(found==6);
    fs::remove_all(root);
    puts("PASS: six USB games from parent/games/Games/Extra, case-insensitive extensions; no duplicate scan roots");
}
