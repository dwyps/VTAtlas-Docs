---
slug: /support/troubleshooting
description: "Every message VT Atlas can print, what causes it, and what to do about it."
---

# Troubleshooting

Every message below is quoted from the plugin as it ships. Search the Output Log for the first few
words.

## "My region does nothing"

Start here, on the volume, before anything else: **Explain Actor Tracking**. It takes the actor you
expected to be tracked and answers why it is not, and it distinguishes cases that look identical from
the outside.

- **No Collision Component** - the actor has no collision of any kind, so it has no body and can never
  overlap anything. Nothing on the volume can fix this.
- **Not A Tracked Object Type** - the actor has collision, but no component of an object type in this
  volume's **Tracked Object Types**. Add the type, or change the actor's collision object type.
- **Filtered By Class**, **Filtered By Actor Tags**, **Filtered By Gameplay Tags** - collision
  delivered the actor and the volume's **Occupant Filter** turned it away. The verdict names the
  clause, so you know which one to look at.
- **Tracked** - the volume does track it, and your problem is elsewhere. Check the region tag, and
  check you are listening to the edge you think you are (see Concepts).

## "Region volume rejected: its Region Tag is unset"

> Region volume rejected: its Region Tag is unset. Set a tag on the volume, or on the region
> definition asset it points at.

The volume registered with no region. Set **Region Tag** on the volume, or assign a **Region
Definition** asset that carries one. A volume with no region is not a region.

## "Region volume rejected: its Region Tag names a tag that is not in the project's gameplay tag table"

> Region volume rejected: its Region Tag names a tag that is not in the project's gameplay tag table.
> Re-add the tag in Project Settings > GameplayTags, or pick one that exists.

Normally this means somebody deleted the tag after the level was saved. The level still remembers the
name; the project no longer has a node for it.

## "Region volume rejected: its shape cannot answer containment"

> Region volume rejected: its shape cannot answer containment. A sphere or capsule needs a positive
> radius, and a polygon footprint has to be convex and wound counter-clockwise. Rebuild the volume's
> footprint, or give the shape a size.

The volume declared a shape it cannot be asked about. A sphere or capsule with no radius, or a spline
region whose bake failed or is missing.

This is a refusal on purpose. An earlier version quietly substituted a box the size of the volume's
bounds, which is a wrong answer wearing the costume of a working one.

## "Region volume '...' has a stale or missing footprint"

> Region volume '%s' has a stale or missing footprint: its spline has changed since it was baked.
> Open the level, press Rebuild Footprint on the volume, and save.

The geometry a spline region ships is the **bake**, not the curve. Editing the spline without
rebaking leaves the level carrying the old shape. The Data Validation panel says the same thing before
you save, which is the earlier and better place to catch it.

## "Region volume '...' is not tracking anything"

The volume registered and its Tracked Object Types list is empty or matches nothing, so no overlap can
ever reach it. Usually a Tracked Object Types list that was emptied by hand.

## "Region occupant notifications nested past their depth limit and were refused"

> Region occupant notifications nested past their depth limit and were refused. An occupant is doing
> work from inside its own region callback that puts something into a region again. Move that work to
> the next frame.

You are allowed to register a volume or move an actor from inside a region callback, and one or two
levels of that is normal. This message means it went eight deep, which is a loop. The plugin stops it
rather than letting the stack run out.

## "MarkDiscovered rejected: discovery is server-authoritative"

> MarkDiscovered rejected: discovery is server-authoritative. Call it on the server, or use your own
> RPC.

Discovery is the one part of VT Atlas that replicates, so it is recorded on the server. Region
membership itself is not, and you can ask about it anywhere.

## "MarkDiscovered rejected: this player is at Max Discovery Entries Per Player"

A per-player cap, in the plugin's settings. It exists so a runaway caller cannot grow a replicated
array without limit. Raise it if your game genuinely has that many regions.

---

## "Iris requires replicated actors to use registered subobjectslists"

Full text: `Ensure condition failed: GDefaultUseSubObjectReplicationList`, from
`EngineReplicationBridge.cpp`.

**This is an engine requirement, not a VT Atlas one**, and you will hit it on any project that turns
Iris on, with or without this plugin. The fix is the one the message gives you:

```ini
[SystemSettings]
Net.SubObjects.DefaultUseSubObjectReplicationList=1
```

in your project's `DefaultEngine.ini`.

**It has to be in the ini and cannot be set at run time.** `AActor` reads the global when its class
default object is constructed, at module load, so a console command or a cvar set from code arrives too
late for every class that already exists. Setting it late clears this ensure and leaves a second one
firing per actor, which looks like a different problem and is not.

## Frequently asked

**Why did entering one volume fire my event four times?**

Because you listened to the nested edge and your tag is four deep. Entering `Castle.Keep.Hall.Vault`
puts the actor in four regions at once. Listen to the exact edge if you want one call per volume. See
Concepts.

**Why does my score go up twice in a listen server?**

Because region events run on the server and on every client. Gate on `Has Authority`. This is the
single most common surprise and it is in Concepts for a reason.

**Can I make a region with a hole in it?**

Not as one spline: a closed spline encloses one outline. Use two regions, or draw a shape that wraps
around the hole.

**Can I nest regions without nesting volumes?**

Yes, and that is the point. The tag hierarchy decides nesting. The volumes do not have to be inside
one another, and often should not be.

**Does adding the Region Listener component make an actor tracked?**

No. Tracking is decided by the volume, at the collision layer. The component only listens.

**Why is there both an interface and a component?**

The interface is lighter to set up and hears everything. The component filters, names, and times.
Neither is cheaper to dispatch. See Concepts.

**Is an exit guaranteed after an enter?**

No, and do not build on it. An actor destroyed inside a region is never told it left, and at level
teardown no exit arrives at all.
