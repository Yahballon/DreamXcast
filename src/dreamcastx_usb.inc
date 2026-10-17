/*
 * PS5DreamcastX USB game library discovery.
 * One scan root per supported folder. IMPORTANT: Flycast's
 * hostfs::DirectoryTree recursively visits children. Returning
 * PS5DreamcastX/games instead of PS5DreamcastX silently hides disc
 * images kept directly in PS5DreamcastX or in other subfolders.
 *
 * /mnt/usb0/PS5DreamcastX/CrazyTaxi.chd
 * /mnt/usb0/PS5DreamcastX/games/SonicAdventure.gdi
 * /mnt/usb0/PS5DreamcastX/Games/DinoCrisis.cdi
 * All three must appear; none may be listed twice.
 */
static std::vector<std::string> discoverDreamcastXUsbDirs(const std::string& mountPrefix, int drives)
{
    std::vector<std::string> paths;
    for (int i=0;i<drives;++i)
    {
        const std::string mount=mountPrefix+std::to_string(i);
        DIR* dir=opendir(mount.c_str());
        if (!dir) continue;
        while (const dirent* entry=readdir(dir))
        {
            if (entry->d_name[0]=='.') continue;
            const std::string folder=entry->d_name;
            std::string lower=folder;
            for (char& c:lower) c=(char)tolower((unsigned char)c);
            const bool supported=lower=="ps5dreamcastx"||lower=="flycast"||
                lower=="dreamcast"||lower=="dc"||lower=="naomi"||
                lower=="atomiswave"||lower=="arcade";
            if (!supported) continue;
            const std::string base=mount+"/"+folder;
            struct stat st{};
            if (stat(base.c_str(),&st)!=0 || !S_ISDIR(st.st_mode))
                continue;
            // Do NOT substitute /games: upstream game scanner is recursive.
            // This includes root, /games, /Games and arbitrary game folders.
            if (std::find(paths.begin(),paths.end(),base)==paths.end())
                paths.push_back(base);
        }
        closedir(dir);
    }
    return paths;
}
