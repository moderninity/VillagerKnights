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

## Why the old pack stopped working

The old pack wrote six tables:

```
guardvillagers:entities/guard_helmet
guardvillagers:entities/guard_chestplate
guardvillagers:entities/guard_legs
guardvillagers:entities/guard_feet
guardvillagers:entities/guard_main_hand
guardvillagers:entities/guard_off_hand
```

**Guard Villagers does not read any of those any more.** It hasn't since 1.6 on
1.20.1, so the old pack was already dead on 1.20.1 too, not only on 1.21.1. There
is now one hardcoded entry point (`Guard.java`, `getLootTableFromData`):

```
guardvillagers:entities/guard_armor        loot context type "guardvillagers:slot"
```

and one rule that changes how you have to write it:

> The list of stacks that table returns is **thrown away**. Gear is equipped only
> as a side effect of the `guardvillagers:slot` loot *function* calling
> `setItemSlot()`.

So an entry that is not under a pool carrying `{"function":"guardvillagers:slot",
"slot":"..."}` produces nothing at all. Slot is no longer implied by which file
the item sits in; it is stated per pool.

Two more details this pack is built around:

* **The slot function must be applied last.** Loot pools run entry functions
  first, then pool functions, and for a nested table that table's own functions
  run before the outer pool's. So the slot function lives on the outermost pool,
  and a pool that nests a slot-setting table must not carry one itself.
* **The two versions disagree about repeat writes.** 1.20.1's `ArmorSlotFunction`
  is `if (!hasItemInSlot(slot)) set` (first write wins). 1.21.1's is an
  unconditional `set` (last write wins). Every slot here is written by exactly one
  pool, so the difference never shows.

---

## How it works

```
guardvillagers:entities/guard_armor     one pool, picks a rank
        |
        +- villagerknights:ranks/<rank>          two pools: an armor set, and a loadout
                 +- villagerknights:armor_sets/<set>    head + chest + legs + feet
                 +- villagerknights:loadouts/<kit>      mainhand + offhand
                          +- villagerknights:weapons/<class_tier>
                          +- villagerknights:offhand/shield_<tier>
```

Rolling the rank first is what keeps a guard coherent: armor tier, weapon tier and
offhand are all decided downstream of it, so you don't get a peasant in Maximilian
plate or a captain with a pitchfork.

### Ranks

| rank | share | armor | weapon |
|---|---|---|---|
| militia | 14% | padded, rusted, scavenged | clubs, pitchforks, wood/stone blades |
| watchman | 23% | mail, kettlehat, brigandine | copper-iron sidearms + shield |
| spearman | 14% | mail, kettlehat | pikes, halberds, guisarmes |
| archer | 10% | light | bow / longbow |
| crossbowman | 10% | mail, brigandine | crossbow / heavy crossbow, sometimes a pavise |
| man-at-arms | 17% | crusader, platemail, XIV century | iron-steel sidearms and longswords |
| knight | 8% | knight, gothic, kastenbrust, winged hussar | steel/silver longswords, greatswords |
| captain | 3% | maximilian, jousting, ceremonial | noble sword, steel greatswords |

Roughly 42% of guards spawn in a full four-piece set, 34% in three, 10% bare.
Shields land on 31%, bread on 22%.

### Tiering

Armor sets are grouped by the actual defense totals in Epic Knights'
`ArmorConfig` (gambeson 6 through maximilian 22), not by looks. Weapon materials
follow `ModItemTier` attack bonuses: wood/stone/copper for militia, up through
steel/silver for knights.

Two-handed pairing follows Epic Knights' own `WeaponType.twoHanded` value:

* `twoHanded 2` (pike, ahlspiess, claymore, zweihander, flame-bladed sword,
  concave halberd) never gets a shield; these take a real damage penalty.
* `twoHanded 1` (bastard sword, estoc, noble sword, ranseur, guisarme...) swords
  can carry a shield, polearms don't.
* `twoHanded 0` (katzbalger, short sword, mace, morgenstern...) shield.

Every helmet, chestplate, leggings and boots item Epic Knights registers appears
somewhere in the armor sets: 21 helmets, 19 chestplates, 12 leggings, 15 boots,
plus 141 weapon and shield variants.

### Deliberately left out

Diamond and netherite Epic Knights weapons and armor. Guards drop equipment, and a
village that hands out netherite zweihanders is a farm. Gold is kept for the top
ranks as parade gear. Vanilla diamond armor appears on captains only, at about
0.2% of all guards.

---

## Changing it

Don't hand-edit the JSON, it's generated. Edit `src/build_villagerknights.py` and
re-run it:

```
python src/build_villagerknights.py
```

It writes both versions side by side. Everything worth tuning is a table near the
top of that file:

* `RANKS` - rank frequency, which armor sets and loadouts each rank draws from,
  and `bare_weight` (the chance of no armor).
* `ARMOR_SETS` - the pieces in each set, per-slot presence chance, enchant chance.
* `LOADOUTS` - weapon table plus offhand mix.
* `WEAPON_TABLES` / `SHIELD_TABLES` - what's in each pool.
* `MATS_T0`-`MATS_T3`, `SIDEARM`, `POLEARM`, `SHIELDS` - material and family weights.

Adding a new Epic Knights item is usually one line in a family dict.

## Issues

Bug reports and feature requests are welcome on the
[issue tracker](https://github.com/moderninity/VillagerKnights/issues). Please say
which branch you're on and which Guard Villagers / Epic Knights versions you have.

