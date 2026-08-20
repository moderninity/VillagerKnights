#!/usr/bin/env python3
"""
Villager Knights datapack builder.

Emits two datapacks from one spec:
  villagerknights-forge-1.20.1     (Guard Villagers 1.6.x  + Epic Knights 10.11)
  villagerknights-neoforge-1.21.1  (Guard Villagers 2.4.x  + Epic Knights 10.12)

Both mods register the same magistuarmory item ids in both versions, so the
*content* is identical; only the datapack encoding differs:

  1.20.1                              1.21.1
  ------                              ------
  data/<ns>/loot_tables/...           data/<ns>/loot_table/...      (folder renamed)
  {"type":"minecraft:loot_table",     {"type":"minecraft:loot_table",
   "name": "ns:path"}                  "value": "ns:path"}          (field renamed)
  pack_format 15                      pack_format 48
  enchant_with_levels {levels}        enchant_with_levels {levels, options}

Architecture note (this is what changed since the old pack):
Guard Villagers no longer reads guard_helmet / guard_chestplate / guard_legs /
guard_feet / guard_main_hand / guard_off_hand.  Since GV 1.6 / 2.x there is ONE
entry point, hardcoded in Guard.java:

    guardvillagers:entities/guard_armor      (loot context "guardvillagers:slot")

The list of stacks that table returns is *thrown away*.  Gear is only equipped
as a side effect of the `guardvillagers:slot` loot function calling
setItemSlot().  So every entry must sit under a pool that carries that function,
or it does nothing at all.

Two more consequences that this generator is built around:
  * The slot function must be the LAST function applied to a stack, so it lives
    on the outermost pool and never on a pool that nests another table.
    (Pool functions run after entry functions, and after a nested table's own
    functions.)
  * 1.20.1's ArmorSlotFunction is `if (!hasItemInSlot) set` (first write wins);
    1.21.1's is an unconditional set (last write wins).  Writing each slot from
    exactly one pool makes that difference invisible.

Layout produced:

  guardvillagers:entities/guard_armor   -> picks one villagerknights:ranks/*
  villagerknights:ranks/*               -> one armor set + one loadout
  villagerknights:armor_sets/*          -> head/chest/legs/feet, matched pieces
  villagerknights:loadouts/*            -> mainhand + offhand, kept consistent
  villagerknights:weapons/*             -> weapon pools by class and tier
  villagerknights:offhand/*             -> shield pools by tier

Run:  python build_villagerknights.py
"""

import json
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, os.pardir))

MA = "magistuarmory:"
MC = "minecraft:"

# --------------------------------------------------------------------------
# materials
#
# ModItemTier attack bonuses: wood 0, stone 1, copper 0, tin 0, silver 1,
# bronze 2, iron 2, steel 2.5, gold 0, diamond 3, netherite 4.
# Diamond and netherite Epic Knights gear is deliberately left out - village
# guards are not a netherite farm.  Gold is kept as parade gear for the top
# ranks (it looks the part even though it hits like copper).
# --------------------------------------------------------------------------

MATS_T0 = {"wood": 3, "stone": 4, "copper": 2}
MATS_T1 = {"copper": 3, "tin": 3, "bronze": 3, "iron": 4, "gold": 1}
MATS_T2 = {"iron": 4, "bronze": 3, "silver": 2, "steel": 3}
MATS_T3 = {"steel": 5, "silver": 3, "gold": 2}

# --------------------------------------------------------------------------
# weapon families, grouped the way Epic Knights' own WeaponsConfig groups them
# (the trailing number is WeaponType.twoHanded)
# --------------------------------------------------------------------------

SIDEARM = {  # twoHanded 0 - fine with a shield
    "stylet": 2,
    "shortsword": 3,
    "katzbalger": 4,
    "morgenstern": 3,
    "chainmorgenstern": 2,
    "heavymace": 3,
    "heavywarhammer": 2,
}
LONGSWORD = {"bastardsword": 4, "estoc": 3}          # twoHanded 1
GREATSWORD = {"claymore": 3, "zweihander": 3, "flamebladedsword": 2}  # twoHanded 2
POLEARM = {  # twoHanded 1-2, never paired with a shield
    "pike": 4,
    "ranseur": 3,
    "ahlspiess": 3,
    "guisarme": 3,
    "lochaberaxe": 2,
    "lucernhammer": 2,
    "concavehalberd": 2,
}
SHIELDS = {
    "heatershield": 4,
    "kiteshield": 3,
    "roundshield": 3,
    "rondache": 2,
    "target": 3,
    "buckler": 3,
    "tartsche": 2,
    "ellipticalshield": 2,
    "pavese": 1,
}


def matrix(families, mats, weight_scale=1):
    """Cross a family dict with a material dict into weighted item entries."""
    out = []
    for fam, fw in families.items():
        for mat, mw in mats.items():
            out.append((MA + mat + "_" + fam, max(1, round(fw * mw * weight_scale / 3))))
    return out


# --------------------------------------------------------------------------
# armor sets
#
# Grouped by the defense totals in Epic Knights' ArmorConfig, so a set's rank
# actually matches how much protection it gives.  Every helmet, chestplate,
# leggings and boots item Epic Knights registers appears in exactly this table.
#
#   name: (tier, {slot: (chance, [(item, weight), ...])}, enchant_chance)
# --------------------------------------------------------------------------

def piece(chance, *items):
    return (chance, [(i, w) for i, w in items])


ARMOR_SETS = {
    # ---- tier 0: rusted, padded, scavenged (total defense 6-12) -----------
    "gambeson": (0, {
        "head": piece(0.55, (MA + "coif", 3)),
        "chest": piece(0.95, (MA + "gambeson_chestplate", 1)),
        "legs": piece(0.75, (MA + "pantyhose", 1)),
        "feet": piece(0.80, (MA + "gambeson_boots", 1)),
    }, 0.0),
    "ragged_mail": (0, {
        "head": piece(0.70, (MA + "rustedchainmail_helmet", 3),
                            (MA + "rustednorman_helmet", 2),
                            (MA + "rustedbarbute", 2)),
        "chest": piece(0.90, (MA + "rustedchainmail_chestplate", 1)),
        "legs": piece(0.70, (MA + "rustedchainmail_leggings", 3),
                            (MA + "pantyhose", 1)),
        "feet": piece(0.70, (MA + "rustedchainmail_boots", 1)),
    }, 0.0),
    "rusted_watch": (0, {
        "head": piece(0.75, (MA + "rustedkettlehat", 3), (MA + "rustedbarbute", 2)),
        "chest": piece(0.90, (MA + "rustedhalfarmor_chestplate", 1)),
        "legs": piece(0.65, (MA + "pantyhose", 2), (MA + "rustedchainmail_leggings", 3)),
        "feet": piece(0.70, (MA + "rustedchainmail_boots", 2), (MA + "gambeson_boots", 1)),
    }, 0.0),
    "rusted_crusader": (0, {
        "head": piece(0.80, (MA + "rustedgreathelm", 1)),
        "chest": piece(0.95, (MA + "rustedcrusader_chestplate", 1)),
        "legs": piece(0.70, (MA + "rustedchainmail_leggings", 1)),
        "feet": piece(0.75, (MA + "rustedcrusader_boots", 1)),
    }, 0.0),
    "vanilla_leather": (0, {
        "head": piece(0.65, (MC + "leather_helmet", 1)),
        "chest": piece(0.90, (MC + "leather_chestplate", 1)),
        "legs": piece(0.70, (MC + "leather_leggings", 1)),
        "feet": piece(0.70, (MC + "leather_boots", 1)),
    }, 0.05),

    # ---- tier 1: town watch (total defense 10-15) ------------------------
    "mail": (1, {
        "head": piece(0.80, (MA + "chainmail_helmet", 3), (MA + "coif", 2)),
        "chest": piece(0.95, (MA + "chainmail_chestplate", 1)),
        "legs": piece(0.80, (MA + "chainmail_leggings", 1)),
        "feet": piece(0.80, (MA + "chainmail_boots", 1)),
    }, 0.05),
    "norman": (1, {
        "head": piece(0.85, (MA + "norman_helmet", 1)),
        "chest": piece(0.95, (MA + "chainmail_chestplate", 1)),
        "legs": piece(0.80, (MA + "chainmail_leggings", 1)),
        "feet": piece(0.75, (MA + "chainmail_boots", 1)),
    }, 0.05),
    "kettlehat": (1, {
        "head": piece(0.85, (MA + "kettlehat", 3), (MA + "barbute", 2)),
        "chest": piece(0.95, (MA + "halfarmor_chestplate", 1)),
        "legs": piece(0.75, (MA + "chainmail_leggings", 1)),
        "feet": piece(0.75, (MA + "chainmail_boots", 1)),
    }, 0.05),
    "brigandine": (1, {
        "head": piece(0.80, (MA + "kettlehat", 2), (MA + "sallet", 2), (MA + "face_helmet", 1)),
        "chest": piece(0.95, (MA + "brigandine_chestplate", 1)),
        "legs": piece(0.75, (MA + "chainmail_leggings", 1)),
        "feet": piece(0.75, (MA + "chainmail_boots", 1)),
    }, 0.05),
    "lamellar": (1, {
        "head": piece(0.85, (MA + "shishak", 1)),
        "chest": piece(0.95, (MA + "lamellar_chestplate", 1)),
        "legs": piece(0.70, (MA + "chainmail_leggings", 1)),
        "feet": piece(0.80, (MA + "lamellar_boots", 1)),
    }, 0.05),
    "vanilla_chainmail": (1, {
        "head": piece(0.70, (MC + "chainmail_helmet", 1)),
        "chest": piece(0.90, (MC + "chainmail_chestplate", 1)),
        "legs": piece(0.75, (MC + "chainmail_leggings", 1)),
        "feet": piece(0.70, (MC + "chainmail_boots", 1)),
    }, 0.08),
    "vanilla_gold": (1, {
        "head": piece(0.70, (MC + "golden_helmet", 1)),
        "chest": piece(0.90, (MC + "golden_chestplate", 1)),
        "legs": piece(0.75, (MC + "golden_leggings", 1)),
        "feet": piece(0.70, (MC + "golden_boots", 1)),
    }, 0.20),

    # ---- tier 2: men-at-arms (total defense 15-18) -----------------------
    "crusader": (2, {
        "head": piece(0.90, (MA + "greathelm", 1)),
        "chest": piece(0.95, (MA + "crusader_chestplate", 1)),
        "legs": piece(0.85, (MA + "crusader_leggings", 1)),
        "feet": piece(0.85, (MA + "crusader_boots", 1)),
    }, 0.10),
    "platemail": (2, {
        "head": piece(0.85, (MA + "bascinet", 3), (MA + "barbute", 2), (MA + "kettlehat", 2)),
        "chest": piece(0.95, (MA + "platemail_chestplate", 1)),
        "legs": piece(0.85, (MA + "platemail_leggings", 1)),
        "feet": piece(0.85, (MA + "platemail_boots", 1)),
    }, 0.10),
    "xiv_century": (2, {
        "head": piece(0.90, (MA + "bascinet", 3), (MA + "greathelm", 2)),
        "chest": piece(0.95, (MA + "xivcenturyknight_chestplate", 1)),
        "legs": piece(0.85, (MA + "xivcenturyknight_leggings", 1)),
        "feet": piece(0.85, (MA + "xivcenturyknight_boots", 1)),
    }, 0.10),
    "cuirassier": (2, {
        "head": piece(0.90, (MA + "cuirassier_helmet", 1)),
        "chest": piece(0.95, (MA + "cuirassier_chestplate", 1)),
        "legs": piece(0.85, (MA + "cuirassier_leggings", 1)),
        "feet": piece(0.85, (MA + "cuirassier_boots", 1)),
    }, 0.10),
    "vanilla_iron": (2, {
        "head": piece(0.80, (MC + "iron_helmet", 1)),
        "chest": piece(0.90, (MC + "iron_chestplate", 1)),
        "legs": piece(0.80, (MC + "iron_leggings", 1)),
        "feet": piece(0.80, (MC + "iron_boots", 1)),
    }, 0.12),

    # ---- tier 3: knights (total defense 18-21) ---------------------------
    "knight": (3, {
        "head": piece(0.95, (MA + "armet", 3), (MA + "grand_bascinet", 2), (MA + "bascinet", 2)),
        "chest": piece(1.0, (MA + "knight_chestplate", 1)),
        "legs": piece(0.90, (MA + "knight_leggings", 1)),
        "feet": piece(0.90, (MA + "knight_boots", 1)),
    }, 0.20),
    "gothic": (3, {
        "head": piece(0.95, (MA + "sallet", 3), (MA + "armet", 2)),
        "chest": piece(1.0, (MA + "gothic_chestplate", 1)),
        "legs": piece(0.90, (MA + "gothic_leggings", 1)),
        "feet": piece(0.90, (MA + "gothic_boots", 1)),
    }, 0.20),
    "kastenbrust": (3, {
        "head": piece(0.95, (MA + "grand_bascinet", 3), (MA + "bascinet", 2)),
        "chest": piece(1.0, (MA + "kastenbrust_chestplate", 1)),
        "legs": piece(0.90, (MA + "kastenbrust_leggings", 1)),
        "feet": piece(0.90, (MA + "kastenbrust_boots", 1)),
    }, 0.20),
    "winged_hussar": (3, {
        "head": piece(0.95, (MA + "shishak", 3), (MA + "face_helmet", 1)),
        "chest": piece(1.0, (MA + "wingedhussar_chestplate", 1)),
        "legs": piece(0.90, (MA + "kastenbrust_leggings", 1)),
        "feet": piece(0.90, (MA + "cuirassier_boots", 1)),
    }, 0.20),

    # ---- tier 4: captains and parade armor (total defense 22+) -----------
    "maximilian": (4, {
        "head": piece(1.0, (MA + "maximilian_helmet", 1)),
        "chest": piece(1.0, (MA + "maximilian_chestplate", 1)),
        "legs": piece(0.95, (MA + "maximilian_leggings", 1)),
        "feet": piece(0.95, (MA + "maximilian_boots", 1)),
    }, 0.35),
    "jousting": (4, {
        "head": piece(1.0, (MA + "stechhelm", 1)),
        "chest": piece(1.0, (MA + "jousting_chestplate", 1)),
        "legs": piece(0.95, (MA + "jousting_leggings", 1)),
        "feet": piece(0.95, (MA + "jousting_boots", 1)),
    }, 0.35),
    "ceremonial": (4, {
        # Epic Knights ships no ceremonial leggings - knight leggings match.
        "head": piece(1.0, (MA + "ceremonialarmet", 1)),
        "chest": piece(1.0, (MA + "ceremonial_chestplate", 1)),
        "legs": piece(0.95, (MA + "knight_leggings", 1)),
        "feet": piece(0.95, (MA + "ceremonial_boots", 1)),
    }, 0.35),
    "vanilla_diamond": (4, {
        "head": piece(0.90, (MC + "diamond_helmet", 1)),
        "chest": piece(0.95, (MC + "diamond_chestplate", 1)),
        "legs": piece(0.90, (MC + "diamond_leggings", 1)),
        "feet": piece(0.90, (MC + "diamond_boots", 1)),
    }, 0.35),
}

# --------------------------------------------------------------------------
# weapon tables:  name -> (entries, enchant_chance, enchant_levels)
# --------------------------------------------------------------------------

WEAPON_TABLES = {
    # split one/two-handed so the shield pairing below stays honest
    "crude_1h": (
        [(MA + "barbedclub", 3), (MA + "blacksmith_hammer", 2),
         (MA + "rusted_heavymace", 4),
         (MC + "wooden_sword", 2), (MC + "wooden_axe", 2),
         (MC + "stone_sword", 3), (MC + "stone_axe", 2)]
        + matrix({"stylet": 2, "shortsword": 3, "katzbalger": 2}, MATS_T0),
        0.0, (5, 12),
    ),
    "crude_2h": (
        [(MA + "club", 4), (MA + "pitchfork", 5),
         (MA + "rusted_bastardsword", 5), (MA + "barbedclub", 2)],
        0.0, (5, 12),
    ),
    "sidearm_t1": (
        matrix(SIDEARM, MATS_T1)
        + [(MA + "messer_sword", 6), (MC + "iron_sword", 8), (MC + "iron_axe", 5)],
        0.06, (5, 15),
    ),
    "sidearm_t2": (
        matrix(SIDEARM, MATS_T2)
        + [(MA + "messer_sword", 5), (MC + "iron_sword", 6), (MC + "iron_axe", 4)],
        0.12, (10, 22),
    ),
    "sidearm_t3": (
        matrix(SIDEARM, MATS_T3) + [(MA + "messer_sword", 4)],
        0.25, (15, 30),
    ),
    "longsword_t2": (
        matrix(LONGSWORD, MATS_T2) + [(MA + "rusted_bastardsword", 2)],
        0.12, (10, 22),
    ),
    "longsword_t3": (
        matrix(LONGSWORD, MATS_T3) + [(MA + "noble_sword", 10)],
        0.25, (15, 30),
    ),
    "greatsword_t3": (
        matrix(GREATSWORD, MATS_T3),
        0.25, (15, 30),
    ),
    "polearm_t1": (matrix(POLEARM, MATS_T1), 0.06, (5, 15)),
    "polearm_t2": (matrix(POLEARM, MATS_T2), 0.12, (10, 22)),
    "polearm_t3": (matrix(POLEARM, MATS_T3), 0.25, (15, 30)),
    "bow_t0": ([(MC + "bow", 6), (MA + "longbow", 2)], 0.05, (5, 15)),
    "bow_t1": ([(MC + "bow", 4), (MA + "longbow", 5)], 0.15, (10, 25)),
    "crossbow_t1": ([(MC + "crossbow", 6), (MA + "heavy_crossbow", 2)], 0.05, (5, 15)),
    "crossbow_t2": ([(MC + "crossbow", 3), (MA + "heavy_crossbow", 5)], 0.15, (10, 25)),
}

# --------------------------------------------------------------------------
# shield tables
# --------------------------------------------------------------------------

SHIELD_TABLES = {
    "shield_t0": (matrix({"buckler": 4, "target": 3, "roundshield": 3}, MATS_T0)
                  + [(MC + "shield", 6)], 0.0, (5, 12)),
    "shield_t1": (matrix(SHIELDS, MATS_T1) + [(MC + "shield", 14)], 0.06, (5, 15)),
    "shield_t2": (matrix(SHIELDS, MATS_T2) + [(MC + "shield", 10)], 0.12, (10, 22)),
    "shield_t3": (matrix(SHIELDS, MATS_T3)
                  + [(MC + "shield", 6), (MA + "corruptedroundshield", 1)], 0.25, (15, 30)),
}

# --------------------------------------------------------------------------
# loadouts: mainhand weapon table + a matching offhand
#
# Epic Knights applies a real penalty to two-handed weapons, and a guard
# holding a zweihander and a kite shield looks wrong, so every two-handed
# loadout gets bread or an empty offhand instead of a shield.
#
#   name -> (weapon_table, [(offhand_kind, weight), ...])
# offhand_kind is a shield table name, "bread", or "empty".
# --------------------------------------------------------------------------

LOADOUTS = {
    "crude":            ("crude_1h",      [("shield_t0", 6), ("bread", 4), ("empty", 4)]),
    "crude_2h":         ("crude_2h",      [("bread", 4), ("empty", 7)]),
    "sidearm_t1":       ("sidearm_t1",    [("shield_t1", 12), ("bread", 3), ("empty", 3)]),
    "sidearm_t2":       ("sidearm_t2",    [("shield_t2", 14), ("bread", 2), ("empty", 3)]),
    "sidearm_t3":       ("sidearm_t3",    [("shield_t3", 14), ("empty", 5)]),
    "longsword_t2":     ("longsword_t2",  [("shield_t2", 7), ("bread", 3), ("empty", 6)]),
    "longsword_t3":     ("longsword_t3",  [("shield_t3", 7), ("bread", 2), ("empty", 6)]),
    "greatsword_t3":    ("greatsword_t3", [("empty", 1)]),
    "polearm_t1":       ("polearm_t1",    [("bread", 4), ("empty", 8)]),
    "polearm_t2":       ("polearm_t2",    [("bread", 3), ("empty", 9)]),
    "polearm_t3":       ("polearm_t3",    [("bread", 2), ("empty", 10)]),
    "archer_t0":        ("bow_t0",        [("bread", 4), ("empty", 8)]),
    "archer_t1":        ("bow_t1",        [("bread", 3), ("empty", 9)]),
    "crossbow_t1":      ("crossbow_t1",   [("bread", 4), ("empty", 8)]),
    "crossbow_t2":      ("crossbow_t2",   [("bread", 3), ("empty", 9)]),
    # pavisiers carried a pavise as a portable wall - the one shield that
    # earns its place next to a crossbow.
    "pavise_crossbow":  ("crossbow_t2",   [("pavise", 1)]),
}

PAVISE_ENTRIES = matrix({"pavese": 1}, MATS_T2)

# --------------------------------------------------------------------------
# ranks: what a guard actually is.  One rank is rolled per guard, and it
# decides both the armor set pool and the loadout pool, so a militiaman never
# spawns in Maximilian plate and a captain never spawns with a pitchfork.
#
#   name -> (rank_weight, bare_weight, [(set, w)...], [(loadout, w)...])
# bare_weight is the chance of no armor at all, as a weight against the sets.
# --------------------------------------------------------------------------

RANKS = {
    "militia": (14, 8, [
        ("gambeson", 5), ("ragged_mail", 4), ("rusted_watch", 4),
        ("vanilla_leather", 4),
    ], [("crude", 7), ("crude_2h", 3)]),

    "watchman": (22, 3, [
        ("mail", 4), ("norman", 3), ("kettlehat", 4), ("brigandine", 3),
        ("lamellar", 2), ("vanilla_chainmail", 3), ("vanilla_gold", 1),
        ("gambeson", 2), ("ragged_mail", 2), ("rusted_watch", 2),
        ("rusted_crusader", 1), ("vanilla_leather", 2),
    ], [("sidearm_t1", 12), ("polearm_t1", 3), ("longsword_t2", 1)]),

    "spearman": (14, 1, [
        ("mail", 4), ("kettlehat", 4), ("brigandine", 3), ("norman", 2),
        ("lamellar", 2), ("gambeson", 2), ("vanilla_chainmail", 3),
        ("vanilla_iron", 1),
    ], [("polearm_t1", 6), ("polearm_t2", 4)]),

    "archer": (10, 3, [
        ("gambeson", 4), ("vanilla_leather", 4), ("mail", 3),
        ("kettlehat", 2), ("brigandine", 2), ("rusted_watch", 2),
    ], [("archer_t0", 6), ("archer_t1", 4)]),

    "crossbowman": (10, 1, [
        ("kettlehat", 4), ("brigandine", 4), ("mail", 3),
        ("vanilla_chainmail", 3), ("gambeson", 2), ("platemail", 1),
        ("vanilla_iron", 1),
    ], [("crossbow_t1", 5), ("crossbow_t2", 3), ("pavise_crossbow", 2)]),

    "man_at_arms": (16, 0, [
        ("crusader", 4), ("platemail", 4), ("xiv_century", 4),
        ("cuirassier", 3), ("vanilla_iron", 3), ("mail", 2),
        ("brigandine", 1), ("rusted_crusader", 1),
    ], [("sidearm_t2", 10), ("longsword_t2", 6), ("polearm_t2", 4)]),

    "knight": (8, 0, [
        ("knight", 5), ("gothic", 4), ("kastenbrust", 4),
        ("winged_hussar", 2), ("crusader", 2), ("xiv_century", 2),
        ("cuirassier", 1),
    ], [("longsword_t3", 8), ("sidearm_t3", 6), ("greatsword_t3", 4),
        ("polearm_t3", 2)]),

    "captain": (3, 0, [
        ("maximilian", 4), ("jousting", 3), ("ceremonial", 3),
        ("knight", 2), ("gothic", 1), ("vanilla_diamond", 1),
    ], [("longsword_t3", 6), ("greatsword_t3", 4), ("sidearm_t3", 3)]),
}


# --------------------------------------------------------------------------
# json emitters
# --------------------------------------------------------------------------

class Flavor:
    def __init__(self, key, loot_dir, nested_key, pack_format, enchant_options, label):
        self.key = key
        self.loot_dir = loot_dir          # "loot_tables" (1.20.1) or "loot_table" (1.21.1)
        self.nested_key = nested_key      # "name" (1.20.1) or "value" (1.21.1)
        self.pack_format = pack_format
        self.enchant_options = enchant_options
        self.label = label


FLAVORS = [
    Flavor("forge-1.20.1", "loot_tables", "name", 15, None,
           "Forge 1.20.1 - Guard Villagers 1.6.x + Epic Knights 10.11"),
    Flavor("neoforge-1.21.1", "loot_table", "value", 48,
           "#minecraft:on_mob_spawn_equipment",
           "NeoForge 1.21.1 - Guard Villagers 2.4.x + Epic Knights 10.12"),
]


def chance(c):
    return {"condition": "minecraft:random_chance", "chance": c}


def enchant(fl, levels):
    fn = {
        "function": "minecraft:enchant_with_levels",
        "levels": {"min": levels[0], "max": levels[1]},
    }
    if fl.enchant_options:
        fn["options"] = fl.enchant_options
    return fn


def item(name, weight=1, functions=None, conditions=None):
    e = {"type": "minecraft:item", "name": name}
    if weight != 1:
        e["weight"] = weight
    if functions:
        e["functions"] = functions
    if conditions:
        e["conditions"] = conditions
    return e


def ref(fl, path, weight=1):
    e = {"type": "minecraft:loot_table", fl.nested_key: path}
    if weight != 1:
        e["weight"] = weight
    return e


def empty(weight=1):
    e = {"type": "minecraft:empty"}
    if weight != 1:
        e["weight"] = weight
    return e


def slot_fn(slot):
    return {"function": "guardvillagers:slot", "slot": slot}


def weighted_items(entries):
    return [item(n, w) for n, w in entries]


# --------------------------------------------------------------------------

def build_weapon_table(fl, entries, ench_chance, ench_levels):
    """A plain pool of weapons/shields.  No slot function - the pool that
    nests this table owns the slot, and pool functions run last."""
    functions = []
    if ench_chance > 0:
        fn = enchant(fl, ench_levels)
        fn["conditions"] = [chance(ench_chance)]
        functions.append(fn)
    pool = {"rolls": 1, "entries": weighted_items(entries)}
    if functions:
        pool["functions"] = functions
    return {"type": "guardvillagers:slot", "pools": [pool]}


def build_armor_set(fl, spec, ench_chance):
    pools = []
    for slot in ("head", "chest", "legs", "feet"):
        if slot not in spec:
            continue
        present, entries = spec[slot]
        pool = {
            "rolls": 1,
            "entries": weighted_items(entries),
            "functions": [slot_fn(slot)],
        }
        if ench_chance > 0:
            fn = enchant(fl, (15, 30))
            fn["conditions"] = [chance(ench_chance)]
            # sits before the slot function, which must stay last
            pool["functions"].insert(0, fn)
        if present < 1.0:
            pool["conditions"] = [chance(present)]
        pools.append(pool)
    return {"type": "guardvillagers:slot", "pools": pools}


def build_loadout(fl, weapon_table, offhands):
    main = {
        "rolls": 1,
        "entries": [ref(fl, "villagerknights:weapons/" + weapon_table)],
        "functions": [slot_fn("mainhand")],
    }
    off_entries = []
    for kind, w in offhands:
        if kind == "empty":
            off_entries.append(empty(w))
        elif kind == "bread":
            off_entries.append(item(
                MC + "bread", w,
                functions=[{"function": "minecraft:set_count",
                            "count": {"min": 4, "max": 16}}]))
        elif kind == "pavise":
            for n, iw in PAVISE_ENTRIES:
                off_entries.append(item(n, iw))
        else:
            off_entries.append(ref(fl, "villagerknights:offhand/" + kind, w))
    off = {
        "rolls": 1,
        "entries": off_entries,
        "functions": [slot_fn("offhand")],
    }
    return {"type": "guardvillagers:slot", "pools": [main, off]}


def build_rank(fl, bare_weight, sets, loadouts):
    armor_entries = [ref(fl, "villagerknights:armor_sets/" + s, w) for s, w in sets]
    if bare_weight:
        armor_entries.append(empty(bare_weight))
    pools = [
        # no slot function here: the nested set tables set their own slots,
        # and a function on this pool would run after them and clobber it.
        {"rolls": 1, "entries": armor_entries},
        {"rolls": 1,
         "entries": [ref(fl, "villagerknights:loadouts/" + l, w) for l, w in loadouts]},
    ]
    return {"type": "guardvillagers:slot", "pools": pools}


def build_entry_point(fl):
    return {
        "type": "guardvillagers:slot",
        "pools": [{
            "rolls": 1,
            "entries": [ref(fl, "villagerknights:ranks/" + r, spec[0])
                        for r, spec in RANKS.items()],
        }],
    }


# --------------------------------------------------------------------------

def write(root, fl, namespace, path, data):
    full = os.path.join(root, "data", namespace, fl.loot_dir, *path.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full + ".json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def build(fl):
    root = os.path.join(OUT, "villagerknights-" + fl.key)
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)

    with open(os.path.join(root, "pack.mcmeta"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"pack": {
            "pack_format": fl.pack_format,
            "description": "Villager Knights - Epic Knights gear for Guard Villagers ("
                           + fl.label + ")",
        }}, f, indent=2)
        f.write("\n")

    # the one table Guard Villagers actually reads
    write(root, fl, "guardvillagers", "entities/guard_armor", build_entry_point(fl))

    for name, (_w, bare, sets, loadouts) in RANKS.items():
        write(root, fl, "villagerknights", "ranks/" + name,
              build_rank(fl, bare, sets, loadouts))

    for name, (_tier, spec, ench) in ARMOR_SETS.items():
        write(root, fl, "villagerknights", "armor_sets/" + name,
              build_armor_set(fl, spec, ench))

    for name, (wt, offs) in LOADOUTS.items():
        write(root, fl, "villagerknights", "loadouts/" + name,
              build_loadout(fl, wt, offs))

    for name, (entries, ec, el) in WEAPON_TABLES.items():
        write(root, fl, "villagerknights", "weapons/" + name,
              build_weapon_table(fl, entries, ec, el))

    for name, (entries, ec, el) in SHIELD_TABLES.items():
        write(root, fl, "villagerknights", "offhand/" + name,
              build_weapon_table(fl, entries, ec, el))

    zip_path = root + ".zip"
    if os.path.exists(zip_path):
        os.remove(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in sorted(filenames):
                full = os.path.join(dirpath, fn)
                z.write(full, os.path.relpath(full, root).replace(os.sep, "/"))

    count = sum(len(f) for _d, _s, f in os.walk(root))
    print("built %-28s %3d files -> %s" % (fl.key, count, os.path.basename(zip_path)))


if __name__ == "__main__":
    for flavor in FLAVORS:
        build(flavor)
