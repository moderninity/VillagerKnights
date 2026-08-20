# Villager Knights - NeoForge 1.21.1

Guard Villagers guards wearing Epic Knights gear, as ranked and matched kits
instead of random pieces.

**This branch is the NeoForge 1.21.1 build.** The other build lives on
[`FORGE-1.20.1`](https://github.com/moderninity/VillagerKnights/tree/FORGE-1.20.1).

Requires **Guard Villagers 2.4.10** and **Epic Knights 10.12** (or compatible). The pack only ever
names their items; it ships no assets of its own.

## Installing

Downloads are on CurseForge and Modrinth. To build from this branch instead, zip
the contents of the repository root (`pack.mcmeta` and `data/` must sit at the top
level of the zip, not inside a folder) and drop it in `<world>/datapacks/`, or in
`config/paxi/datapacks/` to apply it to every world.

## Encoding for this version

| | this branch | FORGE-1.20.1 |
|---|---|---|
| folder | `data/<ns>/loot_table/` | `data/<ns>/loot_tables/` |
| nested table field | `"value"` | `"name"` |
| `pack_format` | 48 | 15 |
| `enchant_with_levels` | `levels` + `options` | `levels` |

Item ids are identical across both: Epic Knights 10.11 and 10.12 register the same
462 items, so nothing needed renaming between versions.

---

## Issues

Bug reports and feature requests are welcome on the
[issue tracker](https://github.com/moderninity/VillagerKnights/issues). Please say
which branch you're on and which Guard Villagers / Epic Knights versions you have.

