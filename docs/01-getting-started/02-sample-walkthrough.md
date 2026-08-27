---
description: "A guided tour of the sample keep: nested regions, per-player discovery, and what the minimap shows."
---

# Sample walkthrough

The sample map is a small stone keep with six regions in it. It is not a showcase level; it is the
shortest thing that shows every idea in the plugin working, and each part of it exists to answer a
question you would otherwise have to take on trust.

Open `L_VTATL_Keep` and press Play.

## What you are looking at

A square keep with a gate on each side, a courtyard on the west, a hall on the east, a vault off the
hall, and a reliquary alcove inside the vault. Outside the walls there is an approach path.

Six regions, and the nesting matters:

```
VTAtlas.Sample.Approach              the path outside, a spline region
VTAtlas.Sample.Keep                  everything inside the walls
  .Keep.Courtyard                    the west half
  .Keep.Hall                         the east half
    .Keep.Hall.Vault                 the room off the hall
      .Keep.Hall.Vault.Reliquary     the alcove with the banner
```

Standing in the reliquary you are in **five** regions at once, and the minimap in the top left shows
which. That is the first thing to internalise: regions nest, and membership is not exclusive.

## The minimap, and why it is the point

The map fills in as you explore. Regions you have not found are dark; regions you have are coloured
and named.

**Now play with two players.** In the toolbar set Play As Client with 2 players, and walk them to
different places. The two windows show **different maps of the same level**. Player one enters by the
west gate and crosses the courtyard; player two enters by the east and reaches the hall directly,
never touching the courtyard. Their maps diverge and stay diverged until they meet.

That is the thing worth seeing, because it is the part you cannot check by reading code: discovery is
per player, it replicates only to its owner, and no player learns what another has found. Nothing in
the sample wires that up. VT Atlas attaches a discovery component to each player as they log in, and
the sample's GameMode deliberately does not do it by hand, because a sample that wired it up itself
would prove nothing.

## The reliquary, and the feature seam

Walk into the alcove at the back of the vault. The light comes up. Walk out and it dims.

Nothing in the level or the GameMode does that. The region volume for the reliquary carries no tag at
all. It carries a **region definition** asset, `RD_VTATL_Reliquary`, and that asset carries a feature.
The feature is what brightens the light, and it is also what tells the minimap that this region is
called "Reliquary", is drawn in gold, and shows an R.

Open the asset and change any of it: the colour, the name, the letter, which light it drives. Nothing
recompiles and no level is touched.

This is the difference between the two ways of saying which region a volume is:

- **A tag on the volume** is the simple path, and five of the six regions here use it.
- **A definition asset** is for when a region has behaviour or presentation, or when several volumes
  make up one region and you want to say so once.

The feature runs on the occupancy edge: it is told when a region gains its **first** occupant and loses
its **last**, not when each actor comes and goes. A feature is never told **who** did it. Anything per
player, like the fog on the map, reads the discovery component instead.

## Things worth trying

**Walk the approach path outside the walls.** It is a spline region, and its bounding box covers the
whole keep. Standing in the courtyard you are not on the approach, even though the box says you might
be. That is the narrow phase doing its job, and it is why the region is drawn as its actual shape in
the debugger rather than as its bounds.

**Open the debugger.** Press the gameplay debugger key and pick the VT Atlas category. It lists the
regions you are in and how many you have discovered, and it draws every volume in the level.

**Select a volume in the editor.** Its wireframe is coloured by how deep its region sits, and its tag
is drawn at its centre. In the details panel, `Fit To Selection` resizes a box volume around whatever
else you have selected, and `Add Child Region` authors a nested region without you typing a tag by
hand.

**Change the keep.** The level is generated, never hand-edited. `Tools/content/author_sample_keep.py`
is its source of truth: change the constants at the top and re-run it.

## What the sample does not show

- **Priority.** Every region here resolves by depth, so the tiebreak never fires.
- **Dwell time.** The API is there; nothing in the map displays it.
- **Very large regions.** Nothing here comes close to the size at which a volume is divided into
  several collision bodies. See Performance.
