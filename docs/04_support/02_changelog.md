---
slug: /support/changelog
description: "Release history for VT Atlas, following Keep a Changelog."
---

# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow semantic
versioning. Every breaking change carries a migration note saying what to do about it.

## [Unreleased]

Nothing yet.

## [1.0.0] - 2026-09-07

First release.

### Added

- **Regions from your own gameplay tags.** Box, sphere and capsule region volumes are placed and sized
  like any trigger. A location query tests the shape itself, not its bounding box: a rotated box does
  not claim the corners of its bounds, and a sphere or capsule does not claim the box around it. Shape
  dimensions are world-space and ignore the actor's scale, so a query and the collision body always
  agree about the same volume.
- **Spline regions, `AVTATLRegionVolumeSpline`, for the region you draw.** Place it, drag out a closed
  spline, set the height range, and press **Rebuild Footprint**. It bakes the outline into convex hulls
  at authoring time and the level stores the hulls, so nothing is decomposed at runtime and the shape a
  query tests is the shape the collision body was built from.

  Draw an L, a U, or any outline that is not a box. The spline's own Z plays no part: the region spans
  Extrusion Min Z to Extrusion Max Z, in whole centimetres, in the volume's own space.

  Two things are refused rather than guessed at, and both say so in the Data Validation panel. A scaled
  spline volume: resize it by moving points and set the actor's scale back to 1, 1, 1. And a footprint
  that no longer matches its spline: press Rebuild Footprint, then save the level. That second one
  matters at save time, because the geometry that ships is the bake, not the curve.
- Region volumes can be a **polygon**: a set of convex hulls extruded through a vertical span, held in
  whole centimetres. This is what a spline region bakes into. Containment against it is exact integer
  arithmetic, so a point on an edge is inside by definition rather than by tolerance.
- `UVTATLRegionSplineComponent`, which locks the closed-loop settings a region cannot be authored
  without, and `UVTATLFootprintComponent`, which owns the baked collision body.
- `FVTATLVolumeShape::IsUsable`, which answers a stronger question than `IsDegenerate`. A box with a
  size is always usable; a polygon is only usable if its hulls are convex and wound counter-clockwise.
- **Very large region volumes are split into several collision bodies automatically.** Past about a
  kilometre on its longest axis, the physics system stops indexing a body properly, and from then on
  every scene query in your game pays a little for it, including character movement and line traces
  belonging to systems that have nothing to do with regions. VT Atlas divides oversized volumes so that
  does not happen. A box becomes a grid, a capsule divides along its axis, and a spline footprint
  regroups its pieces. All three are exact: the pieces cover precisely what the whole one did. It is
  still one region with one tag and the same behaviour, only the collision is split, and below the
  threshold nothing happens at all.
- **A volume that cannot be divided is warned about instead.** A sphere cannot be tiled by spheres, and
  a footprint whose single hull is itself too large cannot be helped by regrouping. The editor
  validation names the span and the cost. It is a warning and not an error, because a very large region
  is a legitimate thing to want.
- **Every region volume can carry a struct you define.** The plugin owns a small fixed set of
  per-volume settings, and every project wants one more: an ambience bank, a PvP flag, a difficulty
  band, a light preset. Rather than guess at those, each volume has a **User Data** slot holding a
  struct from your own code, which VT Atlas stores and hands back without ever reading a field of it.

  It is an instanced struct, so Blueprint gets Make and Break nodes and no C++ is required. Read it
  with `Get Region User Data`, or in C++ with the templated `GetRegionUserDataPtr<T>`, which returns
  null rather than reinterpreting when the volume carries a different struct than the one you asked
  for. Empty is reported as empty rather than as a zeroed struct, because a caller that cannot tell
  those apart applies defaults nobody attached.
- **Crossing events on the subsystem, for both edges.** `On Actor Entered Region Exact` and
  `On Actor Exited Region Exact` fire for a volume carrying precisely that tag; `On Actor Entered
  Region Or Nested` and `On Actor Exited Region Or Nested` fire when an actor enters or leaves a region
  or anything nested under it.
- **Every enter pairs with an exit.** An actor that leaves a region is announced whatever the reason:
  walking out, being destroyed, a level change, a streamed-out level, or play ending. All of them fire
  the exit events and all of them hand you a live actor, because the teardown cases are caught on
  `End Play` while the actor still exists. Anything you hold on the enter edge, a buff, an entry in a
  map, a spawned widget, can be released when a player dies or disconnects.

  **`On Actor Departed Region`** fires alongside every closure-edge exit and carries the reason:
  Crossed, Destroyed, Level Transition, Removed or Shutdown. Bind it rather than the plain exit if you
  hold per-actor state and need to tell a walk-out from a disconnect.
- **`On Region Occupied` / `On Region Vacated`** on the subsystem, plus `Get Num Actors In Region`.
  Bind these rather than counting the enter and exit events: those name an actor and are dropped once
  that actor is destroyed, so a count built on them drifts upward and never recovers. These carry no
  actor and cannot drift.
- **`Get Time In Region`**, how long an actor has been in a region. False rather than zero when the
  actor is not in it, because an actor that arrived this instant has been there for zero seconds.
- **`On Region Added` / `On Region Removed`**, when a region appears in or disappears from the world.
  About level content rather than actors, for a minimap or an audio layer.
- **`Region Listener` component.** A tag filter in the details panel, enter and exit events, the single
  region its owner is in with a display name ready to put on screen, and dwell time. The two-node path
  to a location banner.
- **`Region Occupant`**, an interface an actor implements to be told about its own crossings without
  subscribing to anything. In Blueprint: Class Settings, Implement Interface, then add the events. In
  C++: inherit `IVTATLRegionOccupant` and override the `_Implementation` you care about.

  Four events, one per edge and direction, because neither edge implies the other. **Entered Exact**
  fires when a volume carrying precisely that tag starts holding you. **Entered Or Nested** fires when
  you enter a region you were not in at all, once for the volume's tag and once per ancestor. One
  doorway into a three-deep tag is four calls; that is the design.

  The light path, next to the region listener component. It costs no component and nothing to set up,
  but it hears about every region and cannot report how long you have been in one. These events run on
  the server and on every client, because regions are computed identically from level content
  everyone loads, so anything awarded here is awarded once per connection unless you gate on Has
  Authority.
- **Region features.** Attach behaviour to a region instead of to an actor. Add one to a **Region
  Definition** asset and it runs when that region gains its first occupant and stops when it loses its
  last, with nothing to place and nothing holding a reference to the region.

  Subclass **VT Atlas Region Feature (Blueprint)** in a Blueprint, or the C++ base in code. The native
  base is deliberately not Blueprintable, which is the same split the engine uses for gameplay effect
  components.

  Every definition naming a region contributes its features, and each definition contributes once
  however many volumes point at it. Two definitions naming the same region both run: behaviour
  composes, so there is nothing to remember about who wins.

  Your feature is **duplicated into each world**, so a variable on it belongs to one world and is safe
  to write even with several play-in-editor clients running at once.
- **Actors are tracked by whichever collision component overlaps.** The ordinary Blueprint layout, a
  scene root with the collision on a child, works with no extra setup.
- **`Explain Actor Tracking`**, the node to call when a region does not fire for an actor. It tells
  apart an actor of an untracked object type, an actor the occupant filter rejected, and an actor with
  no collision component at all (**No Collision Component**), and it accepts an actor if any of its
  collision components would overlap.
- **The registration seam takes plain data.** Build an `FVTATLVolumeDesc` and call
  `UVTATLRegionSubsystem::RegisterVolume`, so a procedural level can make regions without placing
  actors. A descriptor that declares no shape at all becomes an axis-aligned box matching its World
  Bounds. A descriptor whose shape cannot answer containment, such as a sphere or capsule with no
  radius, is refused rather than replaced: `RegisterVolume` returns no handle and logs which of the two
  reasons applied.
- **Discovery survives a dormant PlayerState.** If your project sets PlayerStates dormant to save
  bandwidth, a discovery recorded while the channel is dormant still reaches its owning client: the
  discovery log flushes dormancy on every authoritative change, so you do not have to wake the actor.
  Nothing to configure. It is listed because a dormant channel is where a quiet replication failure
  would hide, and the case is covered by two automated scenarios so it stays true.
- **The discovery log is exercised under Iris.** It carries an Iris replication fragment, and a
  discovery is tested reaching its owner over a live Iris net driver. Discovery is the only thing VT
  Atlas puts on the wire, so that is the whole of the surface, but this is stated as what is tested
  rather than as a blanket support claim. Projects on Iris need
  `Net.SubObjects.DefaultUseSubObjectReplicationList=1` in `DefaultEngine.ini`, which is an engine
  requirement rather than one of ours; Troubleshooting explains why it cannot be set at run time.
- **Editor tooling.** Region volume wireframes are tinted by how deep the region sits, measured
  relative to Region Root Tag when one is set, and the region tag is drawn in the viewport when a
  volume is selected. The details panel has Fit To Selection and Add Child Region.
- **Debugging.** `vt.atl.DrawFootprints` and a gameplay debugger row per spline region, naming its hull
  count, vertex count, height range and the state of its bake. Spline regions draw as their baked hulls
  rather than their bounds, because for an L or a U the bounding box is much larger than the region.
  `VTATLDumpFootprint <Tag>` logs a named region's baked hulls. It only reads, so it runs anywhere, and
  it labels its output `server` or `client`: both sides build their registry from their own copy of
  the level, so a footprint that differs between them is exactly the bug you are looking for. A
  `Polygon containment` cycle counter sits under `stat VTATL`.
- **A sample map, `L_VTATL_Keep`.** A small keep with six nested regions, including an **Approach**
  region outside the walls drawn as a spline, the map's demonstration that a region is its shape and
  not its bounding box. A reliquary alcove is authored through a region definition asset rather than a
  tag on its volume, and that definition carries a feature which lights the alcove on the occupancy
  edge and tells the minimap what the region is called and how to draw it.
- **A minimap in the sample HUD**, filling in as regions are discovered. Play as Client with two
  players and the two windows show different maps of the same level, which is what per-player,
  owner-scoped discovery looks like from the outside. Drawn in C++ on the canvas with no imported
  assets, so it can be read in a diff like the rest of the sample.
