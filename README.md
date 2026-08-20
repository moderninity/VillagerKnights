# Villager Knights - Forge 1.20.1

Guard Villagers guards wearing Epic Knights gear, as ranked and matched kits
instead of random pieces.

**This branch is the Forge 1.20.1 build.** The other build lives on
[`NEOFORGE-1.21.1`](https://github.com/moderninity/VillagerKnights/tree/NEOFORGE-1.21.1).

Requires **Guard Villagers 1.6.18** and **Epic Knights 10.11** (or compatible). The pack only ever
names their items; it ships no assets of its own.

## Installing

Downloads are on CurseForge and Modrinth. To build from this branch instead, zip
the contents of the repository root (`pack.mcmeta` and `data/` must sit at the top
level of the zip, not inside a folder) and drop it in `<world>/datapacks/`, or in
`config/paxi/datapacks/` to apply it to every world.

## Encoding for this version

| | this branch | NEOFORGE-1.21.1 |
|---|---|---|
| folder | `data/<ns>/loot_tables/` | `data/<ns>/loot_table/` |
| nested table field | `"name"` | `"value"` |
| `pack_format` | 15 | 48 |
| `enchant_with_levels` | `levels` | `levels` + `options` |

Item ids are identical across both: Epic Knights 10.11 and 10.12 register the same
462 items, so nothing needed renaming between versions.

---

## Issues

Bug reports and feature requests are welcome on the
[issue tracker](https://github.com/moderninity/VillagerKnights/issues). Please say
which branch you're on and which Guard Villagers / Epic Knights versions you have.

