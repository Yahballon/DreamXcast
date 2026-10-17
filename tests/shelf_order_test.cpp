// Tests the SAME library-order helper compiled into the native UI.
#include <cassert>
#include <string>
#include <vector>
struct Shelf {
    std::string name;
    std::vector<int> items;
    int focus=0;
};
#include "../src/dreamcastx_library_order.inc"
int main() {
    // Startup: recently played shelf has only 2 titles, catalogue has 5.
    // The selected shelf MUST be All games with 5 games.
    std::vector<Shelf> shelves = {{"Recently played",{1,3}},{"Favourites",{4}}};
    Shelf all{"All games",{0,1,2,3,4}};
    dreamcastXPutAllFirst(shelves,all,false);
    assert(shelves.size()==3);
    assert(shelves[0].name=="All games" && shelves[0].items.size()==5);
    assert(shelves[1].name=="Recently played" && shelves[1].items.size()==2);
    assert(shelves[2].name=="Favourites");
    // A scanner starting from only one detected ROM still selects All games.
    std::vector<Shelf> partial{{"Recently played",{1}}};
    dreamcastXPutAllFirst(partial,{"All games",{1}},false);
    assert(partial[0].name=="All games");
    assert(partial[0].items.size()==1);
    // No recently played shelf: all games still starts first.
    std::vector<Shelf> onlyFaves{{"Favourites",{0}}};
    dreamcastXPutAllFirst(onlyFaves,all,false);
    assert(onlyFaves[0].items.size()==5);
    // Disc-change picker should *not* lose the game's disc shelf priority.
    std::vector<Shelf> picker{{"This game's discs",{3,4}}};
    dreamcastXPutAllFirst(picker,{"Choose a disc",{0,1,2,3,4}},true);
    assert(picker[0].name=="This game's discs");
    assert(picker[1].name=="Choose a disc");
}
