---
slug: /reference/performance
description: "Measured costs: query scaling, the spatial-structure comparison, and the oversized-volume guard."
---

# Performance

Every number here comes from a capture, not from an impression. The runner, the method and the raw CSV
are named at the bottom so you can check the work or reproduce it.

## The short version

Regions cost approximately nothing at the scale most games use them.

- **Crossings are free to us.** Entering and leaving a region is driven by the engine's own overlap
  events. VT Atlas does no work per frame and has no tick. What a crossing costs is what an engine
  overlap costs, which you are already paying for any trigger volume.
- **A location query is 200 nanoseconds at 100 regions.** Ten of those a frame is 0.014% of a 16 ms
  budget.
- **Nothing here scales with player count or with time.** It scales with how many volumes contain the
  point you asked about.

If your level has a few hundred regions, stop reading. This page is for the case where it has
thousands.

## What a location query costs

`Find Regions At Location` and its variants test a point against every registered volume. Measured on
the runner below, in nanoseconds per query:

| Regions in the level | Time per query |
|---:|---:|
| 100 | 207 ns |
| 1,000 | 2,967 ns |
| 5,000 | 20,441 ns |

Read that as: **the cost is linear in the number of volumes**, and the constant is small. At a hundred
regions you would need five thousand queries a frame before it showed up in a profile. At five thousand
regions, ten queries a frame is about 1.2% of a 16 ms budget, which is when it starts to be worth
thinking about.

**The other queries are cheaper.** Asking about a specific actor (`Is Actor In Region`,
`Get Actor Regions`, `Get Resolved Region`, `Get Time In Region`) reads that actor's own membership
record and does not scan anything. Asking who is in a region reads a reverse index. Only the
by-location family scans.

## Memory

**This is the registry's share only, and it is the smaller half.** A registered volume costs its
descriptor there: the tag, bounds, priority, display name and shape. At 5,000 volumes the registry
holds about 468 KB.

A volume you **place in a level** also costs an actor, a shape component and a collision body, and
those dominate the descriptor by more than an order of magnitude. If you are budgeting memory for
thousands of regions, budget the actors, not this number. Regions registered directly through the API
with no actor cost only what is below. Nothing is cached, nothing is indexed, and nothing runs
per frame.

Spline regions additionally hold their baked hulls, which is whatever your outline needs: the sample
map's U-shaped approach region is three hulls of eight vertices.

## What it costs on the wire

**Region membership is not replicated at all.** Every machine computes it from level content everyone
loads, so a crossing costs zero bytes. That is measured, not assumed: a session crossing a region on
every tick is indistinguishable on the wire from an idle one.

**Discovery is the one thing that replicates**, because which regions a player has found is per-player
knowledge that cannot be derived locally.

| | |
|---|---|
| One discovery | **46 bytes** |
| 32 discoveries | 1,478 bytes in **one** packet |
| For scale: the connection's own keepalive | 7,276 bytes over the same 3 seconds |

Discoveries coalesce. Thirty-two of them arriving at once cost a single extra packet, because they
travel as one property update rather than one message each. The whole burst is under a fifth of what
the connection spends on keepalive doing nothing.

There are no RPCs in VT Atlas, and nothing here scales with the number of volumes in your level.

## Regions in a partitioned world

In World Partition, a region volume is an ordinary spatially loaded actor, and that is the right
default: it is bounded, so it belongs to the cell it sits in. Epic makes the same distinction in its
own actors. `ANavMeshBoundsVolume` opts out of spatial loading unconditionally, and
`APostProcessVolume` opts out **only when it is unbounded**. Actors whose effect is global stay
resident; bounded ones do not.

**The consequence, which is easy to meet by accident:** a region volume only exists while its cell is
loaded. Outside the loaded set the volume is not there, so it tracks nobody and the region reports no
occupants. That is usually what you want, because nothing is happening there. It is not what you want
for a region whose state matters at a distance, such as one a quest or a map screen asks about while
the player is far away.

For those, clear **Is Spatially Loaded** on the volume so it stays resident, or keep the region's state
somewhere that outlives the volume. In a partitioned world the number worth watching is the actor and
package count, not query time.

## Why there is no spatial index

Because at the sizes this plugin is built for, one would cost more than it saves.

A location query walks the list of volumes and tests each one. That sounds naive, and at a hundred
regions it answers in a fifth of a microsecond, which is far below anything you can measure in a frame.
Adding an index would buy back time nobody was spending, in exchange for memory, a second structure to
keep correct, and a rebuild cost every time a region streams in or out.

We did build and measure the alternatives before deciding, across query time, memory, and the cost of
adding and removing a region as level streaming does. The plain scan is the only one that is cheap on
every axis. The faster structures win on query time by a wide margin and lose badly on streaming, which
is the thing a real level actually does.

If your project has thousands of regions and you are seeing this in a profile, get in touch. The
measurements exist and an index can be added; nothing needs it yet.

## What is not measured here

- **Crossing cost.** That is the engine's overlap system, not ours. Profile it with `stat Physics`.
- **A real scene.** These corpora are synthetic: uniform, clustered and mixed-scale distributions of
  axis-aligned boxes. A real level is somewhere between the first two.
- **Consoles or handhelds.** One machine, named below. Treat the shape of the curve as portable and the
  absolute numbers as not.
- **Bandwidth under packet loss.** The discovery figure is from a local loopback connection with no
  loss and no throttling. Retransmission on a real connection is the engine's business, not the
  plugin's, but it means 46 bytes is a floor rather than a promise.

## Profiling it yourself

VT Atlas ships its own counters. Nothing has to be enabled at build time.

```
stat VTATL
```

Gives cycle counters for the region overlap notification, for location queries, and for the
spline-region point test.

Insights traces the same paths as `VTATL_OverlapBegin`, `VTATL_OverlapEnd` and
`VTATL_RegionsAtLocation`. A `VTATL` CSV category exists and is off by default; enable it with
`-csvCategories=VTATL`.

## Capture

| | |
|---|---|
| Date | 2026-08-13 |
| Runner | AMD Ryzen 9 9950X3D, 16 cores / 32 threads, 62 GB RAM, Windows 11 |
| Engine | UE 5.8.1, Development editor build, `-nullrhi` |
| Method | 20,000 queries per cell, half uniformly random and half a coherent walk |
| Corpus | Generated from a fixed seed, so the same numbers reproduce on any machine |
| Raw data | `docs/perf/captures/spatial-2026-08-13.csv` |
| Harness | `VTATLSpatialBenchmark` commandlet, with the full survey in `docs/perf/SPATIAL_INDEX_SURVEY.md` |

Every alternative in the comparison table was checked against the shipped scan's answers before it was
timed. That check found three real bugs in the harness during development, two of which would have made
an alternative look faster than it is. A benchmark that does not verify its answers is measuring how
fast something produces the wrong result.
