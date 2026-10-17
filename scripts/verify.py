#!/usr/bin/env python3
"""Fail-fast integration verification; no PS5 hardware claims."""
from pathlib import Path
import hashlib,json,sys

root=Path(__file__).resolve().parents[1]
src=root/"build/flycast/shell/ps5"
app=json.loads((root/"app.json").read_text(encoding="utf-8"))
version=app["version"]
assert app["releaseTag"]==f"ps5-dreamcastx-v{version}"
assert src.is_dir(), "Flycast source has not been prepared"
ui=(src/"bigpicture.cpp").read_text()
assert ui.count('drawDreamcastXShelf(dl, focused, selectDisk);')==1
assert ui.count('#include "dreamcastx_shelf.inc"')==1
assert 'col::text, "DreamXcast");' in ui
assert f'col::dim, "by YAHBALLON  v{version}");' in ui
assert 'W - 48 - vs.x' not in ui
assert 'static const char name[] = "DreamXcast";' in ui
assert 'void drawDreamcastXShelf(' in (src/"dreamcastx_shelf.inc").read_text()
meta=json.loads((src/"sce_sys/param.json").read_text())
assert meta["titleId"]==app["titleId"]
assert meta["contentVersion"]==app["contentVersion"]
assert meta["localizedParameters"]["en-US"]["titleName"]=="DreamXcast"
assert "title=PS5DreamcastX" in (src/"build.sh").read_text()
assert "/data/homebrew/PS5DreamcastX/" in (src/"ps5_main.cpp").read_text()
assert 'candidates.push_back("/data/homebrew/PS5DreamcastX");' in (src/"ps5_main.cpp").read_text()
assert 'discoverDreamcastXUsbDirs("/mnt/usb", 8)' in (src/"ps5_main.cpp").read_text()
assert 'bool usb = true;' in (src/"ps5_frontend.h").read_text()
assert '"PS5DreamcastX/"' in (src/"ps5_update.cpp").read_text()
assert "recursive scan root(s)" in (src/"ps5_main.cpp").read_text()
assert "library: scanner=%d media, shown=%d titles" in ui
assert ui.count('dreamcastXPutAllFirst(shelves, all, selectDisk);') == 1
assert ui.count('#include "dreamcastx_library_order.inc"') == 1
assert 'shelves.insert(shelves.begin(), all);' in (src/"dreamcastx_library_order.inc").read_text()
assert 'shelves.push_back(all);' in (src/"dreamcastx_library_order.inc").read_text()
assert 'Shelf recent{ "Recently played" };' in ui
assert '#include "ps5_diag.h"' in ui
assert 'ALL GAMES' in ui and 'refreshGames(true);' in ui
assert 'refreshGames(lib.source == Network)' not in ui
assert 'games[i].source == lib.source' not in ui
assert 'games[i].source != lib.source' not in ui
assert '&& g.source == lib.source' not in ui
assert 'dreamcastx_smb_settings::addRows(storage);' in ui
assert 'dreamcastx_smb_settings::accept(typed);' in ui
assert 'KeyboardRaPassword, KeyboardSmb' in ui
assert (src/"dreamcastx_smb_settings.inc").exists()
assert 'ps5::ime::Kind::Password' in (src/"dreamcastx_smb_settings.inc").read_text()
assert 'chmod(temp.c_str(),0600)' in (src/"dreamcastx_smb_settings.inc").read_text()
assert 'sourceOf(m.path)' in ui

assert "string_tolower(extension);" in (root/"build/flycast/core/ui/game_scanner.cpp").read_text()
usb=(src/"dreamcastx_usb.inc").read_text()
assert "const std::string base=mount+\"/\"+folder;" in usb
assert 'base+"/games"' not in usb

assert 'extern std::string appDir;' in (src/"ps5_frontend.h").read_text()
assert 'const std::string externalData = "/data/PS5DreamcastX";' in (src/"ps5_main.cpp").read_text()
assert 'ps5::rootDir = externalData + "/";' in (src/"ps5_main.cpp").read_text()
assert 'ps5::appDir + "sce_sys/param.json"' in (src/"ps5_main.cpp").read_text()
assert 'swapIn(appDir,' in (src/"ps5_update.cpp").read_text()
assert 'readLine(appDir + "BUILD.txt")' in (src/"ps5_update.cpp").read_text()
shelf=(src/"dreamcastx_shelf.inc").read_text()
# PS5 v0.1.5 broke due to experimental raw ImageQuad/perspective UVs.
# Only native imageFill / rect helpers proven by v0.1.3 are allowed here.
assert "dreamcastXArtworkBounds(" in shelf
assert "drawDreamcastXCase(" in shelf
assert "imageFill(dl,image,art.x,art.y,art.w,art.h" in shelf
for forbidden in ("AddImageQuad(", "AddQuadFilled(", "PrimReserve(", "dreamcastXReflection(", "softDisc("):
    assert forbidden not in shelf, "Unsafe PS5 renderer reintroduced: "+forbidden
assert "ps5-dreamcastx-v" in (src/"ps5_update.cpp").read_text()
assert f'PS5_VERSION "{version}"' in (src/"ps5_build.h").read_text()
async_ui=(root/"build/flycast/core/ui/gui_util.cpp").read_text()
assert '#include "dreamcastx_cover_async.inc"' in async_ui
assert 'dreamcastx_cover_async::texture(path,nearestSampling,textureLoadCount)' in async_ui
assert (root/"build/flycast/core/ui/dreamcastx_cover_async.inc").exists()
assert "loadDisk(path,decoded,w,h)" in (root/"build/flycast/core/ui/dreamcastx_cover_async.inc").read_text()
assert "saveDisk(path,decoded,w,h)" in (root/"build/flycast/core/ui/dreamcastx_cover_async.inc").read_text()
assert "if (path.empty())" in ui
assert "pauseUntil = getTimeMs() + 15 * 60 * 1000;" in (root/"build/flycast/core/ui/boxart/boxart.cpp").read_text()
assert "for(int radius=0;radius<=2;radius++)" in shelf
feed=(src/"ps5_update.cpp").read_text()
assert "Yahballon/DreamXcast/releases" in feed
assert "ps5-dreamcastx-v" in feed
icon=(src/"sce_sys/icon0.png").read_bytes()
source=(root/"build/icon0.png").read_bytes()
assert len(icon)>1000 and icon.startswith(bytes.fromhex("89504e470d0a1a0a"))
assert hashlib.sha256(icon).digest()==hashlib.sha256(source).digest(), "PS5 launcher icon does not match generated neon icon"
print(f"PASS: DreamXcast v{version} menu/version, exact neon launcher icon, storage and updater")
