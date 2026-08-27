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
with no actor cost only what is below. There is no acceleration structure, no cached query results,
and nothing per-frame.

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

## Why there is no octree

Because it is slower than not having one, at the sizes that matter, and the alternatives that are
faster cost more than they save.

Seven approaches were implemented and measured against each other, each verified to return exactly the
same answers as the shipped scan before being timed. Nanoseconds per query, clustered corpus, which is
the one that looks most like a real level:

| Approach | 100 | 1,000 | 5,000 | Index memory at 5,000 |
|---|---:|---:|---:|---:|
| **Linear scan (ships)** | **207** | **2,967** | **20,441** | **0** |
| Linear scan, packed arrays | 82 | 934 | 7,438 | 0 |
| Sweep and prune on one axis | 11 | 286 | 1,572 | 351 KB |
| Engine physics scene query | 1,771 | 1,870 | 2,027 | 0 |
| Engine octree (`TOctree2`) | 26 | 91 | 185 | 3,210 KB |
| Bounding volume hierarchy | 4 | 17 | 34 | 574 KB |
| Uniform grid | 19 | 21 | 26 | 2,385 KB |

Three things this shows.

**At 100 regions the difference is nanoseconds.** Every structure answers in under a quarter of a
microsecond. Shipping an index would buy 200 ns per query in exchange for memory, build time, and a
second structure that has to stay correct. That is a bad trade for a cost nobody can measure.

**The engine's own physics scene is not the free answer.** It looked like the obvious one: every volume
already has a collision body, so the scene already indexes them. Measured, it is the slowest option at
100 regions, by a factor of over 400 against a purpose-built structure, because a general scene query
takes a lock and builds hit structures before answering a much broader question than "is this point
inside one of these boxes".

**Query time alone picks the wrong winner, which is why the table above is not the whole comparison.**
Measured across the axes that a real game pays for, at 5,000 regions:

| Approach | Query | Bytes/region | Add one region | Remove one |
|---|---:|---:|---:|---:|
| **Linear scan (ships)** | 21,281 ns | 96 B | **1.1 us** | **2.4 us** |
| Sweep and prune | 1,804 ns | 72 B | 3.0 us | 5.1 us |
| Uniform grid | 29 ns | 488 B | 1.2 us | 3.3 us |
| Engine octree | 193 ns | 658 B | 2.7 us | 536 us |
| Bounding volume hierarchy | **34 ns** | 118 B | **2,292 us** | **2,286 us** |

Add and remove are what **level streaming** does. The BVH has the fastest query of anything here and
costs 2.3 milliseconds to accept one region, because a median-split tree has no incremental insert and
has to be rebuilt: 137 frames at 60 Hz, for one region streaming in. The octree inserts cheaply but
removes slowly, for a structural reason to do with how element identity is tracked.

**The linear scan is the only approach that is cheap on every axis.** It loses query time by three
orders of magnitude and wins everything else, and at the scale this plugin is for, query time is the
axis that does not matter.

If VT Atlas ever does need an index, the grid and the BVH are the candidates, and which one wins
depends on whether your level streams. The work is done and measured; it is not shipped because nothing
needs it yet.

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
