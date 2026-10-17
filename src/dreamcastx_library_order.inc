/*
 * PS5DreamcastX: choose the complete library on initial entry.
 * Keep Recently played / Favourites reachable via up/down, but always
 * display All games first when returning to this tab or after a scan.
 * The disc-selection dialog retains its own "This game's discs" priority.
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
inline void dreamcastXPutAllFirst(std::vector<Shelf>& shelves,
                                   const Shelf& all, bool selectDisk)
{
    if (selectDisk)
        shelves.push_back(all);
    else
        shelves.insert(shelves.begin(), all);
}
