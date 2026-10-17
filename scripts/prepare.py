#!/usr/bin/env python3
"""Fetch a pinned, working PS5 Flycast core; adapt the native shell and shelf.

The big PSFlycast source tree remains unmodified upstream. No precompiled
emulator is used; GitHub Actions compiles this real PS5 C/C++ native port.
"""
from pathlib import Path
import json, re, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"build/flycast"
PIN="1cc6b2978d891f93cd2e36123ba4fd14118bd444"
TITLE="PPSA99765"
APP_FOLDER="PS5DreamcastX"
VERSION=json.loads((ROOT/"app.json").read_text(encoding="utf-8"))["version"]

def cmd(*args):
    subprocess.run(args,check=True)

def prepare_checkout():
    SOURCE.parent.mkdir(parents=True,exist_ok=True)
    if not (SOURCE/".git").is_dir():
        if SOURCE.exists():
            raise RuntimeError("build/flycast exists and is not a Git checkout")
        cmd("git","clone","--recursive","https://github.com/Press5elect/PSFlycast.git",str(SOURCE))
    cmd("git","-C",str(SOURCE),"fetch","origin",PIN)
    cmd("git","-C",str(SOURCE),"checkout","--detach",PIN)
    cmd("git","-C",str(SOURCE),"submodule","update","--init","--recursive")

def adapt():
    p=SOURCE/"shell/ps5"
    ui=p/"bigpicture.cpp"
    if not ui.exists():
        raise RuntimeError("Expected PSFlycast native BigPicture UI is missing")
    for f in p.rglob("*"):
        if f.is_file() and f.suffix in (".cpp",".h",".sh",".py",".json",".cmake",".inc",".txt",".md"):
            t=f.read_text(encoding="utf-8")
            # Preserve copyright attribution to the original PSFlyCast authors.
            t=t.replace("PPSA99247",TITLE).replace("PSFlyCast","DreamXcast")
            t=t.replace("Copyright 2026 the DreamXcast contributors",
                "Copyright 2026 the PSFlyCast contributors")
            f.write_text(t,encoding="utf-8")

    t=ui.read_text()
    # The SMB settings include is nested inside bigpicture's anonymous
    # namespace. Standard headers must be included BEFORE that namespace.
    assert '#include <algorithm>' in t
    t=t.replace('#include <algorithm>','#include <array>\n#include <algorithm>',1)
    diagInclude='#include "ps5_diag.h"'
    assert '#include "ps5_frontend.h"' in t
    if diagInclude not in t:
        t=t.replace('#include "ps5_frontend.h"',
                    '#include "ps5_frontend.h"\n'+diagInclude,1)
    anchor="\t\tdrawShelves(dl, focused, selectDisk);"
    include='// ---- the grid view: every game\'s cover'
    if anchor in t:
        assert t.count(anchor)==1
        t=t.replace(anchor,"\t\tdrawDreamcastXShelf(dl, focused, selectDisk);")
    assert t.count("drawDreamcastXShelf(dl, focused, selectDisk);")==1
    if '#include "dreamcastx_shelf.inc"' not in t:
        assert t.count(include)==1, "Upstream library layout changed"
        t=t.replace(include,'#include "dreamcastx_shelf.inc"\n\n'+include)
    # UI name + version on author line; no extra clock-version duplicate.
    # Every other exposed PS5 shell text is rebranded in the pass above.
    old='text(dl, bold(), 34, 112, 28, col::text, "DreamXcast");'
    assert t.count(old)==1, "Expected pinned native header title"
    byline=f"by YAHBALLON  v{VERSION}"
    t=t.replace(old,
        'text(dl, bold(), 29, 112, 18, col::text, "DreamXcast");' + chr(10) +
        f'\t\ttext(dl, regular(), 17, 114, 60, col::dim, "{byline}");',1)
    clock='text(dl, bold(), 30, W - 48 - cs.x, 48 - cs.y / 2, col::text, clock);'
    assert t.count(clock)==1
    # Do not add any version label beneath the clock.

    # Log scanner totals when the async catalog grows or shrinks. A scan
    # root count is NOT a game count; record both for PS5 diagnostics.
    catalogAnchor='findDiscSets();\n\treturn true;'
    assert t.count(catalogAnchor)==1, "Flycast game catalogue changed"
    t=t.replace(catalogAnchor,
        'findDiscSets();\n\tps5::diag::mark("library: scanner=%d media, shown=%d titles", '
        '(int)list.size(), (int)games.size());\n\treturn true;',1)
    # Cached local covers win instantly over network metadata discovery.
    # TheGamesDB is queried only if no local cover is present.
    # Offline cover browsing never stalls on online metadata requests.
    old_cover = '''ImTextureID coverTexture(Game& g)
{
	ensureArt(g);
	std::string path = userCover(g);
	if (path.empty())
		path = g.art.boxartPath;'''
    new_cover = '''ImTextureID coverTexture(Game& g)
{
	std::string path = userCover(g);
	if (path.empty())
		ensureArt(g);
	if (path.empty())
		path = g.art.boxartPath;'''
    assert t.count(old_cover) == 1, "Pinned Flycast coverTexture hook changed"
    t=t.replace(old_cover,new_cover,1)
    # When a player has played two games, upstream puts "Recently played"
    # at index 0 and the menu misleadingly shows 2 / 2 even though the
    # scanner has already found 5 / 5. Always put "All games" at index 0.
    # A disc-change picker keeps "This game's discs" first.
    shelf_insert='''\tif (!all.items.empty())
\t\tshelves.push_back(all);
\tif (!arcade.items.empty())'''
    shelf_replacement='''\tif (!all.items.empty())
\t\tdreamcastXPutAllFirst(shelves, all, selectDisk);
\tif (!arcade.items.empty())'''
    assert t.count(shelf_insert)==1, "Pinned Flycast shelf ordering changed"
    t=t.replace(shelf_insert,shelf_replacement,1)
    shelf_function="void buildShelves(bool selectDisk)"
    assert t.count(shelf_function)==1, "Pinned Flycast shelf entry point changed"
    t=t.replace(shelf_function,
       '#include "dreamcastx_library_order.inc"\n\n'+shelf_function,1)
    assert t.count('dreamcastXPutAllFirst(shelves, all, selectDisk)')==1
    ps5_source=p/"dreamcastx_library_order.inc"
    shutil.copy2(ROOT/"src/dreamcastx_library_order.inc",ps5_source)

    # Unified library: all sources are already present in the game's
    # single vector. Do not filter it into separate Internal/USB/SMB tabs.
    # The per-game source is retained for disc launch and SMB streaming.
    barsStart=t.index('\t// Tabs, switched with L1 / R1.')
    barsEnd=t.index('\t// The clock, and the pads.', barsStart)
    t=t[:barsStart]+'''
    const char *allGamesLabel = "ALL GAMES";
    const ImVec2 allSize = textSize(bold(),25,allGamesLabel);
    text(dl,bold(),25,(W-allSize.x)*0.5f,34,col::dim,allGamesLabel);

'''+t[barsEnd:]
    assert t.count("ALL GAMES")==1

    oldChoice='''void switchSource(int source)
{
\tif (source == lib.source)'''
    assert oldChoice in t, "Source selection function changed upstream"
    first=t.index("void switchSource(int source)")
    last=t.index("const char *regionText(u32 r);",first)
    t=t[:first]+'''void switchSource(int source)
{
    // All platforms share the same library. Only launch() distinguishes
    // a game's real location (internal, USB, or SMB).
    (void)source;
    lib.source = Internal;
}
void chooseSource()
{
    if (!sourceChosen) {
        sourceChosen = true;
        lib.source = Internal;
    }
}

'''+t[last:]

    assert t.count("refreshGames(lib.source == Network);")==2
    t=t.replace("refreshGames(lib.source == Network);","refreshGames(true);")
    assert t.count("games[i].source == lib.source && ")==3
    assert t.count(" && games[i].source == lib.source")==2
    assert t.count(" && g.source == lib.source")==1
    assert t.count("games[i].source != lib.source || ")==1
    t=t.replace("games[i].source == lib.source && ","")
    t=t.replace(" && games[i].source == lib.source","")
    t=t.replace(" && g.source == lib.source","")
    t=t.replace("games[i].source != lib.source || ","")
    # All games includes Arcade as well; Arcade stays as an optional shelf.
    oldArcade='''\t\tif (!selectDisk && games[i].media.arcade)
\t\t\tarcade.items.push_back(i);
\t\telse
\t\t\tall.items.push_back(i);'''
    assert t.count(oldArcade)==1
    t=t.replace(oldArcade,'''        all.items.push_back(i);
        if (!selectDisk && games[i].media.arcade)
            arcade.items.push_back(i);''',1)
    # When the cached SMB scanner completes it has always incremented its
    # generation. This invalidates all unified shelves and list variants.
    oldScans='''\t\t\tif (lib.source == Network)
\t\t\t\tscanNetwork();
\t\t\telse
\t\t\t{
\t\t\t\tscanner().refresh();
\t\t\t\tif (lib.source == Usb)
\t\t\t\t\tps5::rescanUsb();
\t\t\t\tscannedCount = (size_t)-1;
\t\t\t}'''
    assert t.count(oldScans)==1
    t=t.replace(oldScans,'''            scanner().refresh();
            ps5::rescanUsb();
            scanNetwork();
            scannedCount = (size_t)-1;''',1)
    # L1/R1 are no longer used for tabs, including the disc picker.
    first=t.index("if (in.l1 || in.r1)",t.index("void libraryScreen(bool selectDisk)"))
    second=t.index("\n\t\t}",first)+4
    original=t[first:second]
    assert "switchSource(next)" in original
    t=t[:first]+'''// L1 / R1 are reserved for future shortcuts; no hidden source tabs.'''+t[second:]
    t=t.replace('{ Glyph::L1R1, "Tab" }, ','')
    t=t.replace('{ Glyph::L1R1, "Source" }, ','')
    t=t.replace('const char *scanHint = lib.source == Network ? "Scan the share" : "Rescan";',
                'const char *scanHint = "Rescan all";')
    t=t.replace('if (lib.source == Network && !empty)','if (!empty)')
    # Show the true origin on each game's subtitle in the unified shelf.
    metaBegin=t.index("std::string metaText(Game& g)")
    metaReturn=t.index(chr(9)+"return meta;",metaBegin)
    newMeta=chr(10).join([
        "    const char *origin = g.source == Network ? \"SMB\" :",
        "                         g.source == Usb ? \"USB\" : \"Internal\";",
        "    meta += (meta.empty() ? \"\" : \"  /  \");",
        "    meta += origin;",
        ""])
    t=t[:metaReturn]+newMeta+t[metaReturn:]
    # Drop stale network-specific empty-library copy; one consistent help.
    noGameHelp='''\t\tbody = "Copy your games to\\n" + root + "games/\\n\\n"'''
    assert t.count(noGameHelp)==1
    t=t.replace(noGameHelp,'''        body = "Internal, USB and SMB games appear together.\\n"
               "Internal: " + root + "games/\\n"
               "Network: Settings > Library > SMB shares\\n\\n"''',1)

    # Move SMB editing into the already existing Library settings screen.
    enumItem="KeyboardRaUser, KeyboardRaPassword };"
    assert t.count(enumItem)==1
    t=t.replace(enumItem,"KeyboardRaUser, KeyboardRaPassword, KeyboardSmb };")
    settingsEntry="std::vector<Category> buildCategories()"
    assert t.count(settingsEntry)==1
    t=t.replace(settingsEntry,'#include "dreamcastx_smb_settings.inc"\n\n'+settingsEntry,1)
    rowsPoint='''\tfor (const auto& [label, sub] : std::vector<std::pair<std::string, std::string>>{'''
    assert t.count(rowsPoint)==1
    t=t.replace(rowsPoint,'''    dreamcastx_smb_settings::addRows(storage);
'''+rowsPoint,1)
    settingsKeyboard='''\t\telse if (keyboard == KeyboardRaUser || keyboard == KeyboardRaPassword)'''
    assert t.count(settingsKeyboard)==1
    t=t.replace(settingsKeyboard,'''        else if (keyboard == KeyboardSmb)
        {
            dreamcastx_smb_settings::accept(typed);
            std::fill(typed.begin(),typed.end(),'\\0');
            ps5::ime::forget();
        }
'''+settingsKeyboard,1)
    # Ensure network status appears in the merged library when SMB is active.
    t=t.replace('if (lib.source == Network && !empty)',
                'if (!ps5::smb::gameFolders().empty() && !empty)')
    assert "dreamcastx_smb_settings::addRows(storage);" in t
    assert "dreamcastx_smb_settings::accept(typed);" in t
    assert t.count("refreshGames(true);")==2
    shutil.copy2(ROOT/"src/dreamcastx_smb_settings.inc",p/"dreamcastx_smb_settings.inc")

    ui.write_text(t)
    shutil.copy2(ROOT/"src/dreamcastx_shelf.inc",p/"dreamcastx_shelf.inc")

    # Async thumbnail decoding: the PS5 UI must NEVER load/decode large
    # cover files on its ImGui frame. Keep GPU uploads on the main thread.
    gui_util=SOURCE/"core/ui/gui_util.cpp"
    gu=gui_util.read_text()
    begin='int ImguiFileTexture::textureLoadCount;'
    assert gu.count(begin)==1, "Upstream ImguiFileTexture loader changed"
    gu=gu.replace(begin,
        '#include "dreamcastx_cover_async.inc"\n\n'+begin,1)
    before='''\tImTextureID id = imguiDriver->getTexture(path);
\tif (id == ImTextureID() && textureLoadCount < 10)'''
    assert gu.count(before)==1, "Upstream sync image loader changed"
    after='''#ifdef USE_PS5
\tif (dreamcastx_cover_async::isCoverPath(path))
\t\treturn dreamcastx_cover_async::texture(path,nearestSampling,textureLoadCount);
#endif
\tImTextureID id = imguiDriver->getTexture(path);
\tif (id == ImTextureID() && textureLoadCount < 10)'''
    gu=gu.replace(before,after,1)
    gui_util.write_text(gu)
    shutil.copy2(ROOT/"src/dreamcastx_cover_async.inc",
                 SOURCE/"core/ui/dreamcastx_cover_async.inc")
    # TheGamesDB sometimes returns HTTP 503. The original scraper retried
    # after just ten seconds, stealing network time from useful libretro art.
    # Back off metadata-only requests; local art and cover downloads continue.
    boxart_cpp=SOURCE/"core/ui/boxart/boxart.cpp"
    box=boxart_cpp.read_text()
    old_backoff='pauseUntil = getTimeMs() + 10 * 1000;'
    assert box.count(old_backoff)==1, "Pinned Flycast metadata retry hook changed"
    box=box.replace(old_backoff,
        'pauseUntil = getTimeMs() + 15 * 60 * 1000;',1)
    boxart_cpp.write_text(box)



    # Flycast's game scanner is recursive. Normalize uppercase .GDI/.CHD/
    # .CDI/.CUE extensions before format checks, just like lowercase dumps.
    scanner=SOURCE/"core/ui/game_scanner.cpp"
    sc=scanner.read_text()
    extline='std::string extension = get_file_extension(item.name);'
    assert sc.count(extline)==1, "Pinned Flycast scanner extension hook changed"
    sc=sc.replace(extline,extline+'\n\t\tstring_tolower(extension);',1)
    scanner.write_text(sc)

    # Rename the physical ShadowMount folder, not the mandatory PPSA titleId.
    main=p/"ps5_main.cpp"
    m=main.read_text()
    assert m.count('candidates.push_back("/data/homebrew/PPSA99765");') == 1
    m=m.replace('/data/homebrew/PPSA99765/', '/data/homebrew/PS5DreamcastX/')
    m=m.replace('candidates.push_back("/data/homebrew/PPSA99765");',
                'candidates.push_back("/data/homebrew/PS5DreamcastX");')
    start=m.index('void findUsbDirs()')
    end=m.index('// The folders in emu.cfg',start)
    m=m[:start]+'''#include "dreamcastx_usb.inc"

void findUsbDirs()
{
    ps5::usbDirs = discoverDreamcastXUsbDirs("/mnt/usb", 8);
    for (const std::string& dir : ps5::usbDirs)
        ps5::diag::mark("usb: DreamcastX game directory: %s", dir.c_str());
    ps5::diag::mark("usb: %d recursive scan root(s) (includes games/ subfolders)", (int)ps5::usbDirs.size());
}

'''+m[end:]
    # App binaries stay in /data/homebrew/PS5DreamcastX/; all emulator
    # user content/settings belong in /data/PS5DreamcastX/ when elevated.
    # A sandbox-only launch still works with a clearly logged fallback.
    assert m.count("std::string rootDir;")==1
    m=m.replace("std::string rootDir;", "std::string rootDir;" + chr(10) + "std::string appDir;", 1)
    old="\tif (ps5::options().usb)\n\t{\n\t\t// Before any other thread exists"
    new="\tif (true) // external /data storage needs elevation even when USB browsing is off\n\t{\n\t\t// Before any other thread exists"
    assert m.count(old)==1, "Expected startup elevation gate changed"
    m=m.replace(old,new,1)

    start=m.index(chr(9)+'std::vector<std::string> candidates;', m.index('int main(int argc, char *argv[])'))
    end=m.index(chr(9)+'ps5::loadOptions(ps5::rootDir);',start)
    m=m[:start]+'''    // Locate the installed PS5 title before selecting its *separate* data root.
    std::vector<std::string> candidates;
    if (ps5::elevated)
    {
        candidates.push_back("/data/homebrew/PS5DreamcastX");
        candidates.push_back("/mnt/sandbox/PPSA99765_000/app0");
    }
    candidates.push_back("/app0");
    candidates.push_back("/download0");
    for (const std::string& candidate : candidates)
        if ((candidate == "/download0" || hasFile(candidate + "/eboot.bin"))
            && writableDir(candidate))
        {
            ps5::appDir = candidate + "/";
            break;
        }
    if (ps5::appDir.empty())
        ps5::appDir = "/app0/";

    const std::string externalData = "/data/PS5DreamcastX";
    if (ps5::elevated && writableDir(externalData))
        ps5::rootDir = externalData + "/";
    else
    {
        ps5::rootDir = ps5::appDir; // PS5 loader/sandbox fallback
        ps5::diag::mark("storage: /data/PS5DreamcastX unavailable: using %s",
                        ps5::rootDir.c_str());
    }
    ps5::diag::mark("storage: app=%s data=%s", ps5::appDir.c_str(), ps5::rootDir.c_str());
'''+m[end:]
    # The app's param.json belongs to the install folder, not the user data folder.
    m=m.replace('hasFile(ps5::rootDir + "sce_sys/param.json")',
                'hasFile(ps5::appDir + "sce_sys/param.json")')
    m=m.replace('(ps5::rootDir + "sce_sys/param.json").c_str()',
                '(ps5::appDir + "sce_sys/param.json").c_str()')
    assert 'storage: app=%s data=%s' in m
    assert 'const std::string externalData = "/data/PS5DreamcastX";' in m
    main.write_text(m)
    shutil.copy2(ROOT/"src/dreamcastx_usb.inc",p/"dreamcastx_usb.inc")

    library=p/"ps5_library.cpp"
    l=library.read_text()
    l=l.replace('"/data/homebrew/PPSA99765/"',
                '"/data/PS5DreamcastX/", "/data/homebrew/PS5DreamcastX/", "/data/homebrew/PPSA99765/"')
    library.write_text(l)

    # Fresh installs discover USB sources automatically when elfldr is available.
    # Existing frontend.cfg with usb=0 stays user-controlled (enable in Settings).
    frontend=p/"ps5_frontend.h"
    f=frontend.read_text()
    assert f.count("bool usb = false;") == 1
    frontend.write_text(f.replace("bool usb = false;", "bool usb = true;", 1))
    hdr=frontend.read_text()
    assert "extern std::string rootDir;" in hdr
    frontend.write_text(hdr.replace("extern std::string rootDir;", 
                                    "extern std::string rootDir;" + chr(10) + "extern std::string appDir;", 1))

    # Remove saved /data content paths from the old app's search, and keep
    # them mapped to the chosen root for backwards-compatible recents.
    main_text=main.read_text()
    assert '"/data/homebrew/PS5DreamcastX/"' in main_text
    main_text=main_text.replace('"/data/homebrew/PS5DreamcastX/", "/mnt/sandbox/"',
                                '"/data/PS5DreamcastX/", "/data/homebrew/PS5DreamcastX/", "/mnt/sandbox/"')
    main.write_text(main_text)

    # Only use this standalone DreamXcast repository's release feed.
    # The upstream download/update code uses a release list; constrain both
    # tag namespace and exact ZIP asset. No auto-update on this test build.
    updater=p/"ps5_update.cpp"
    u=updater.read_text()
    u=u.replace("Press5elect/PSFlycast/releases","Yahballon/DreamXcast/releases")
    # Self-update reads files from the packaged folder; the Title ID is NOT the installation path.
    u=u.replace('constexpr const char *TitleFolder = "PPSA99765/";',
                'constexpr const char *TitleFolder = "PS5DreamcastX/";')
    assert 'constexpr const char *TitleFolder = "PS5DreamcastX/";' in u
    # Title self-update stages/install binaries inside appDir, never in /data/.
    u=u.replace('return rootDir + "update/";', 'return appDir + "update/";')
    u=u.replace('swapIn(rootDir, work + "new/", work + "old/", files, why, restored)',
                'swapIn(appDir, work + "new/", work + "old/", files, why, restored)')
    u=u.replace('readLine(rootDir + "BUILD.txt")', 'readLine(appDir + "BUILD.txt")')
    # The fork's brand has a longer prefix than PSFlyCast, fix version parsing.
    assert 'ownTag = buildLine.substr(10, buildLine.find_first_of(", ", 10) - 10);' in u
    u=u.replace('ownTag = buildLine.substr(10, buildLine.find_first_of(", ", 10) - 10);',
                'ownTag = buildLine.substr(sizeof("DreamXcast ") - 1, '
                'buildLine.find_first_of(", ", sizeof("DreamXcast ") - 1) '
                '- (sizeof("DreamXcast ") - 1));')
    assert 'swapIn(appDir,' in u and 'readLine(appDir + "BUILD.txt")' in u

    tag='release.tag = entry["tag_name"].get<std::string>();'
    if tag not in u:
        raise RuntimeError("Upstream updater tag hook changed")
    u=u.replace(tag,tag+'''
    if (release.tag.rfind("ps5-dreamcastx-v", 0) != 0)
    {
        why = "not a PS5DreamcastX release";
        return false;
    }
    release.tag = release.tag.substr(sizeof("ps5-dreamcastx-") - 1);
''',1)
    wanted='const std::string wanted = "DreamXcast-" + release.tag + ".zip";'
    if wanted not in u:
        raise RuntimeError("Expected renamed updater asset pattern missing")
    u=u.replace(wanted,'const std::string wanted = "PPSA99765.zip";',1)
    fallback='if (chosen == nullptr && endsWith(lower(name), ".zip") && lower(name).find("source") == std::string::npos)'
    if fallback not in u:
        raise RuntimeError("Upstream ZIP fallback changed; review safety")
    u=u.replace(fallback,'if (false && chosen == nullptr)',1)
    updater.write_text(u)

    ver=p/"ps5_build.h"
    v=ver.read_text()
    v,n=re.subn(r'#define PS5_BUILD_NUMBER\s+\d+','#define PS5_BUILD_NUMBER 13',v)
    assert n==1
    v,n=re.subn(r'#define PS5_VERSION\s+"[^"]+"',f'#define PS5_VERSION "{VERSION}"',v)
    assert n==1
    ver.write_text(v)

    meta=p/"sce_sys/param.json"
    data=json.loads(meta.read_text())
    data["titleId"]=TITLE
    data["conceptId"]=TITLE[4:]
    data["contentId"]="UP9000-PPSA99765_00-PS5DREAMCASTX001"
    data["contentVersion"]=json.loads((ROOT/"app.json").read_text(encoding="utf-8"))["contentVersion"]
    data["masterVersion"]="01.00"
    data["localizedParameters"]["en-US"]["titleName"]="DreamXcast"
    meta.write_text(json.dumps(data,indent=2)+"\n")
    # Leave restart/update targeting the title installation while settings
    # and the emulator's writable content use the external data directory.
    # The PS5 home screen icon is the actual user-provided DreamXcast neon artwork.
    # Regenerate from our pinned source on every build; never use upstream icon0.png.
    out=ROOT/"build/icon0.png"
    cmd("python3",str(ROOT/"assets/generate_icon.py"),str(out))
    shutil.copy2(out,p/"sce_sys/icon0.png")
    script=p/"build.sh"
    s=script.read_text()
    assert "title=PPSA99765" in s
    s=s.replace("title=PPSA99765", "title=PS5DreamcastX", 1)
    # Old PSFlyCast startup artwork/audio must not appear under our branding.
    s=re.sub(r'^cp -- "\$src/shell/ps5/sce_sys/pic0.dds".*?\n','',s,flags=re.M)
    s=re.sub(r'^cp -- "\$src/shell/ps5/sce_sys/snd0.at9".*?\n','',s,flags=re.M)
    script.write_text(s)
    for name in ("pic0.dds","pic1.dds","snd0.at9"):
        (p/"sce_sys"/name).unlink(missing_ok=True)
    print("Prepared Flycast PS5 core and GBAX-style native shelf",TITLE)

if __name__=="__main__":
    prepare_checkout()
    adapt()
