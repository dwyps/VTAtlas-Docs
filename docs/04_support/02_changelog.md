---
slug: /support/changelog
description: "Release history for VT Atlas, following Keep a Changelog."
---

# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow semantic
versioning. Every breaking change carries a migration note saying what to do about it.

## [Unreleased]

### Added

- **Every exit now pairs with an enter.** An actor that leaves a region is announced whatever the
  reason: walking out, being destroyed, a level change, a streamed-out level, or play ending. All of
  them fire the existing exit events and all of them hand you a live actor, because the teardown cases
  are caught on `End Play` while the actor still exists.

  Before this the plugin only reported actors that MOVED out. An occupant destroyed inside a region was
  cleaned up correctly and silently never announced, so anything held on the enter edge - a buff, an
  entry in a map, a spawned widget - leaked the moment a player died or disconnected, and the only
  symptom was state that slowly stopped matching the world.

  **`On Actor Departed Region`** fires alongside every closure-edge exit and carries the reason:
  Crossed, Destroyed, Level Transition, Removed or Shutdown. Bind it rather than the plain exit if you
  hold per-actor state and need to tell a walk-out from a disconnect.

  Migration: none. Existing exit bindings simply start firing in cases where they previously did not,
  which is what they were always assumed to do.

- **The sample map now demonstrates the region feature seam and per-player discovery.** A fourth
  nesting level, a reliquary alcove, is authored through a region definition asset rather than a tag on
  its volume, and that definition carries a feature which lights the alcove on the occupancy edge and
  tells the minimap what the region is called and how to draw it.
- **A minimap in the sample HUD**, filling in as regions are discovered. Play as Client with two
  players and the two windows show different maps of the same level, which is what per-player,
  owner-scoped discovery looks like from the outside. Drawn in C++ on the canvas with no imported
  assets, so it can be read in a diff like the rest of the sample.
- **Editor tooling.** Region volume wireframes are tinted by how deep the region sits, measured
  relative to Region Root Tag when one is set, and the region tag is drawn in the viewport when a
  volume is selected. The details panel gains Fit To Selection and Add Child Region.
- **A very large region volume is now split into several collision bodies automatically.** Past about
  a kilometre on its longest axis, the physics system stops indexing a body properly, and from then on
  every scene query in your game pays a little for it, including character movement and line traces
  belonging to systems that have nothing to do with regions. VT Atlas divides oversized volumes so that
  does not happen. A box becomes a grid, a capsule divides along its axis, and a spline footprint
  regroups its pieces. All three are exact: the pieces cover precisely what the whole one did. It is
  still one region with one tag and unchanged behaviour, only the collision is split, and below the
  threshold nothing happens at all.
- **A volume that cannot be divided is warned about instead.** A sphere cannot be tiled by spheres, and
  a footprint whose single hull is itself too large cannot be helped by regrouping. The editor
  validation names the span and the cost. It is a warning and not an error, because a very large region
  is a legitimate thing to want.
- Region volumes can be a **polygon**: a set of convex hulls extruded through a vertical span, held in
  whole centimetres. This is what a spline region bakes into. Containment against it is exact integer
  arithmetic, so a point on an edge is inside by definition rather than by tolerance, and the geometry
  a location query tests is the same geometry the collision body is built from.
- `FVTATLVolumeShape::IsUsable`, which answers a stronger question than `IsDegenerate`. A box with a
  size is always usable; a polygon is only usable if its hulls are convex and wound counter-clockwise.
- **`AVTATLRegionVolumeSpline`**, the region you draw. Place it, drag out a closed spline, set the
  height range, and press **Rebuild Footprint**. It bakes the outline into convex hulls at authoring
  time and the level stores the hulls, so nothing is decomposed at runtime and the shape a query tests
  is the shape the collision body was built from.

  Draw an L, a U, or any outline that is not a box. The spline's own Z plays no part: the region spans
  Extrusion Min Z to Extrusion Max Z, in whole centimetres, in the volume's own space.

  Two things are refused rather than guessed at, and both say so in the Data Validation panel. A scaled
  spline volume: resize it by moving points and set the actor's scale back to 1, 1, 1. And a footprint
  that no longer matches its spline: press Rebuild Footprint, then save the level. That second one
  matters at save time, because the geometry that ships is the bake, not the curve.
- `UVTATLRegionSplineComponent`, which locks the closed-loop settings a region cannot be authored
  without, and `UVTATLFootprintComponent`, which owns the baked collision body.
- `vt.atl.DrawFootprints` and a gameplay debugger row per spline region, naming its hull count, vertex
  count, height range and the state of its bake. Spline regions draw as their baked hulls rather than
  their bounds, because for an L or a U the bounding box is much larger than the region.
- `VTATLDumpFootprint <Tag>` logs a named region's baked hulls. Read-only, so it runs anywhere, and it
  labels its output `server` or `client`: both sides build their registry from their own copy of the
  level, so a footprint that differs between them is exactly the bug you are looking for.
- A `Polygon containment` cycle counter under `stat VTATL`.
- The sample map gained an **Approach** region, the ground outside the walls, drawn as a spline. It is
  the map's demonstration that a region is its shape and not its bounding box.
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
  but it hears about every region and cannot report how long you have been in one.

  Two things worth reading before you use it. These run on the server AND on every client, because
  regions are computed identically from level content everyone loads, so anything awarded here is
  awarded once per connection unless you gate on Has Authority. (Exits used to be unreliable at
  teardown; as of the entry above they are not. It remains a crossing
  notification, not a lifecycle hook.

- **Discovery survives a dormant PlayerState.** If your project sets PlayerStates dormant to save
  bandwidth, a discovery recorded while the channel is dormant still reaches its owning client: the
  discovery log flushes dormancy on every authoritative change, so you do not have to wake the actor.
  Nothing to configure. It is listed because a dormant channel is where a quiet replication failure
  would hide, and the case is covered by two automated scenarios so it stays true.
- **The discovery log is exercised under Iris.** It carries an Iris replication fragment, and one
  automated scenario replicates a discovery to its owner over a live Iris net driver. Discovery is the
  only thing VT Atlas puts on the wire, so that is the whole of the surface, but this is stated as what
  is tested rather than as a blanket support claim. Projects on Iris need
  `Net.SubObjects.DefaultUseSubObjectReplicationList=1` in `DefaultEngine.ini`, which is an engine
  requirement rather than one of ours; Troubleshooting explains why it cannot be set at run time.

### Fixed

- **An actor whose root is a plain Scene Component is now tracked.** Whether a volume tracks an actor
  was decided from the actor's root component alone, so the ordinary Blueprint layout - a scene root
  with the collision on a child - was refused even while the engine was delivering its overlaps. The
  symptom was a region that simply never fired, and `Explain Actor Tracking` blamed the Tracked Object
  Types list, which had nothing wrong with it. The overlap handler now asks about the component that
  actually overlapped, and `Explain Actor Tracking`, which has no component to name, accepts the actor
  if any of its collision components would overlap.
- `EVTATLTrackingResult` gained **No Collision Component**, appended. "This actor has no body at all"
  used to report as "not a tracked object type", which sent a designer to a list that could not help
  them. Existing values keep their numbers.

### Changed

- **The two closure-edge delegates are renamed** `On Actor Entered Region Or Nested` and
  `On Actor Exited Region Or Nested`. The queries already said Exact and Or Nested; the delegates said
  Exact and nothing, which left the closure edge unnamed. Redirects ship in the plugin's config.

  Migration: rename the two bindings. The Exact pair is unchanged.
- **A location query now tests the shape, not its bounding box.** A rotated box used to claim the
  corners of its own bounds, and a sphere and a capsule used to claim everything a box around them
  would. Containment is analytic per shape.

  Migration: none for placed volumes. If a query used to answer true for a point that was inside the
  bounds but outside the shape, it now answers false, which is the answer it should always have given.
- **Shape dimensions are world-space and ignore the actor's scale.** A sphere scaled non-uniformly
  would otherwise have queried as an ellipsoid while its collision body stayed a sphere, so the two
  halves of the plugin would have disagreed about the same volume.
- **A descriptor whose shape cannot answer containment is now refused at registration instead of
  being replaced by a box.** `UVTATLRegionSubsystem::RegisterVolume` returns no handle and logs which
  of the two reasons applied.

  Migration: nothing to do if you place region volumes in the editor, which fill their own shape. If
  you build an `FVTATLVolumeDesc` in code and hand it to `RegisterVolume`, two cases change.

  A descriptor that declares **no shape at all** still works exactly as before. That is a
  default-constructed shape, which is a Box with a zero extent, and it still becomes an axis-aligned
  box matching the descriptor's World Bounds. This is the documented behaviour of the registration
  seam and it has not moved.

  A descriptor that declares a **sphere or capsule with no radius** used to become that same box.
  It is now refused. It was never going to behave the way its author wrote it, and silently handing
  back a different shape is a wrong answer wearing the costume of a working one. Give the shape a
  size, or leave the shape unset if a box matching the bounds is what you actually wanted.
