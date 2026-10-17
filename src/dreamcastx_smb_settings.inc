/*
 * PS5DreamcastX - SMB connection editor inside Settings > Library.
 * Supports up to 6 on-console editable paths and preserves additional
 * paths from network.cfg. Files are written atomically with mode 0600.
 *
 * Changes are activated on the NEXT app start. Do not mutate libsmb2's
 * active credentials/connections while the network-scanner thread runs.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
// Includes are provided by bigpicture.cpp before its anonymous namespace.
namespace dreamcastx_smb_settings {
struct Config {
    std::array<std::string,6> paths{};
    std::vector<std::string> morePaths;
    std::string user="guest";
    std::string password;
    std::string domain;
    bool loaded=false;
    bool restartRequired=false;
};
static Config cfg;
static int activeField=-1; // 0..5 paths, 6 user, 7 password, 8 domain

static std::string clean(const std::string& raw) {
    std::string out;
    for(unsigned char c:raw)
        if(c!=0 && c!=10 && c!=13) out.push_back((char)c);
    return out;
}
static std::string trimmed(const std::string& s) {
    const auto a=s.find_first_not_of(" \t");
    return a==std::string::npos?"":s.substr(a,s.find_last_not_of(" \t")-a+1);
}
static bool validPath(const std::string& p) {
    if(p.empty())return true; // clearing a slot is allowed
    std::string s=p;
    std::replace(s.begin(),s.end(),'\\','/');
    if(s.rfind("smb://",0)==0)s.erase(0,6);
    while(!s.empty() && s.front()=='/')s.erase(s.begin());
    const size_t slash=s.find('/');
    if(slash==std::string::npos || slash==0 || slash==s.size()-1)
        return false;
    return s.find("..")==std::string::npos;
}
static void load() {
    if(cfg.loaded)return;
    cfg.loaded=true;
    FILE* f=std::fopen((ps5::rootDir+"network.cfg").c_str(),"rb");
    if(!f)return;
    char buffer[4096];int slot=0;
    while(std::fgets(buffer,sizeof(buffer),f)) {
        std::string line=trimmed(clean(buffer));
        if(line.empty()||line.front()=='#'||line.front()==';')continue;
        const size_t equals=line.find('=');
        if(equals==std::string::npos)continue;
        const std::string key=trimmed(line.substr(0,equals));
        const std::string value=trimmed(line.substr(equals+1));
        if(key=="path") {
            if(slot<6)cfg.paths[slot++]=value;
            else cfg.morePaths.push_back(value);
        }
        else if(key=="user")cfg.user=value.empty()?"guest":value;
        else if(key=="password")cfg.password=value;
        else if(key=="domain")cfg.domain=value;
    }
    std::fclose(f);
}
static bool write() {
    load();
    const std::string path=ps5::rootDir+"network.cfg";
    const std::string temp=path+".dreamcastx-new";
    FILE* f=std::fopen(temp.c_str(),"wb");
    if(!f)return false;
    std::fputs("# PS5DreamcastX SMB configuration - edit in Settings > Library\n",f);
    std::fputs("# Changed values take effect after restarting the app.\n",f);
    for(const auto& path:cfg.paths)
        if(!path.empty())std::fprintf(f,"path = %s\n",path.c_str());
    for(const auto& path:cfg.morePaths)
        if(!path.empty())std::fprintf(f,"path = %s\n",path.c_str());
    std::fprintf(f,"user = %s\n",cfg.user.empty()?"guest":cfg.user.c_str());
    std::fprintf(f,"password = %s\n",cfg.password.c_str());
    std::fprintf(f,"domain = %s\n",cfg.domain.c_str());
    const bool ok=std::fflush(f)==0 && std::ferror(f)==0;
    const bool closed=std::fclose(f)==0;
    if(!ok || !closed) {
        std::remove(temp.c_str());
        return false;
    }
    chmod(temp.c_str(),0600);
    if(std::rename(temp.c_str(),path.c_str())!=0) {
        std::remove(temp.c_str());
        return false;
    }
    cfg.restartRequired=true;
    return true;
}
static std::string pathText(int i) {
    load();return cfg.paths[(size_t)i].empty()?"Not configured":cfg.paths[(size_t)i];
}
static std::string fieldText(int i) {
    load();
    if(i<6)return pathText(i);
    if(i==6)return cfg.user.empty()?"guest":cfg.user;
    if(i==7)return cfg.password.empty()?"Not set":"********";
    return cfg.domain.empty()?"Default":cfg.domain;
}
static void edit(int field) {
    load();
    activeField=field;
    std::string label;
    std::string current;
    size_t length=180;
    ps5::ime::Kind kind=ps5::ime::Kind::Text;
    if(field<6) {
        label="SMB Share "+std::to_string(field+1);
        current=cfg.paths[(size_t)field];
    } else if(field==6) {
        label="SMB Username";
        current=cfg.user;
        length=100;
    } else if(field==7) {
        label="SMB Password";
        // The PS5 keyboard must NOT echo an existing password.
        current="";
        kind=ps5::ime::Kind::Password;
        length=180;
    } else {
        label="SMB Domain";
        current=cfg.domain;
        length=100;
    }
    openKeyboard(KeyboardSmb,label.c_str(),
                 field<6?"192.168.1.10/Share/Dreamcast":
                 field==7?"Leave blank to clear":field==8?"WORKGROUP":"guest",
                 current,length,kind);
}
static bool accept(const std::string& input) {
    load();
    if(activeField<0 || activeField>8)return false;
    std::string value=clean(input);
    if(activeField<6) {
        value=trimmed(value);
        if(!validPath(value)) {
            os_notify("Invalid SMB path",4000,
                      "Use server/share/folder, e.g. 192.168.1.10/Games/Dreamcast");
            activeField=-1;
            return false;
        }
        cfg.paths[(size_t)activeField]=value;
    } else if(activeField==6)cfg.user=trimmed(value);
    else if(activeField==7)cfg.password=value;
    else cfg.domain=trimmed(value);
    activeField=-1;
    const bool saved=write();
    os_notify(saved?"SMB settings saved":"Could not save SMB settings",
              3500,saved?"Restart PS5DreamcastX to use the new connection":"Check data folder permissions");
    return saved;
}
static void addRows(Category& storage) {
    load();
    for(int field=0;field<9;field++){
        const std::string label=field<6?
            "SMB share "+std::to_string(field+1):
            field==6?"SMB username":field==7?"SMB password":"SMB domain";
        Row r{Row::Action,label,
            field<6?"Server/share/folder. Cross opens the PS5 keyboard":
            field==7?"Stored in network.cfg; password is never displayed":
            "Cross to edit using the PS5 keyboard"};
        r.info=[field]{return fieldText(field);};
        r.action=[field]{edit(field);};
        storage.rows.push_back(std::move(r));
    }
    Row extra{Row::Info,"Extra SMB share paths",
              "Entries beyond 6 in network.cfg are preserved"};
    extra.info=[] {load();return std::to_string(cfg.morePaths.size())+" additional share(s)";};
    storage.rows.push_back(extra);
    Row saved{Row::Info,"SMB connection status",
              "Changes saved immediately. Active SMB sessions are not modified while a game is running"};
    saved.info=[] {
        return cfg.restartRequired?
            std::string("Saved - restart app to apply"):
            std::string("Using current network.cfg");
    };
    storage.rows.push_back(saved);
}
} // namespace dreamcastx_smb_settings
