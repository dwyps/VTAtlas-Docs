---
slug: /reference/performance
description: "Measured costs: location queries, memory, the wire, and the spatial structures compared."
---

# Performance

Every number here comes from a capture, not from an impression. The runner, the method and the raw
data are named at the bottom so you can check the work.

## The short version

Regions cost approximately nothing at the scale most games use them.

- **Crossings are free to us.** Entering and leaving a region is driven by the engine's own overlap
  events. VT Atlas does no work per frame and has no tick. What a crossing costs is what an engine
  overlap costs, which you are already paying for any trigger volume.
- **A location query is under 300 nanoseconds at 100 regions.** Ten of those a frame is 3
  microseconds, under 0.02% of a 16 ms frame.
- **Nothing here scales with player count or with time.** It scales with how many volumes are
  registered.

If your level has a few hundred regions, stop reading. This page is for the case where it has
thousands.

## What a location query costs

`Find Regions At Location` and its variants test a point against every registered volume. Measured on
the runner below, in nanoseconds per query, for three ways of scattering the volumes:

| Regions in the level | Uniform | Clustered | Mixed sizes |
|---:|---:|---:|---:|
| 100 | 277 ns | 255 ns | 299 ns |
| 1,000 | 3,688 ns | 3,587 ns | 3,644 ns |
| 5,000 | 25,445 ns | 25,638 ns | 25,215 ns |

Read that as: **the cost grows with the number of volumes, a little faster than linearly**. Per volume
it is about 3 ns at a hundred regions and about 5 ns at five thousand. At a hundred regions, a
thousand queries a frame is about 0.3 ms. At five thousand regions, ten queries a frame is about a
quarter of a millisecond, 1.6% of a 16 ms frame, which is when it starts to be worth thinking about.

**The other queries are cheaper.** Asking about a specific actor (`Is Actor In Region`,
`Get Actor Regions`, `Get Resolved Region`, `Get Time In Region`) reads that actor's own membership
record and does not scan anything. Asking who is in a region reads a reverse index. Only the
by-location family scans.

## Memory

**This is the registry's share only.** A registered volume costs its descriptor there: the tag,
bounds, priority, display name and shape. The registry's tables hold 66,096 bytes at 100 volumes,
578,584 at 1,000 and 2,946,032 at 5,000, so about 590 bytes a volume once there are more than a
handful. Each volume's tag ancestry is a small allocation of its own on top of that.

A volume you **place in a level** also costs an actor, a shape component and a collision body. If you
are budgeting memory for thousands of regions, budget the actors as well as this number. Regions
registered directly through the API, with no actor, cost only the registry's share. Nothing is cached,
nothing is indexed, and nothing runs per frame.

Spline regions additionally hold their baked hulls, which is whatever your outline needs, up to 64
hulls of up to 64 vertices each.

## What it costs on the wire

**Region membership is not replicated at all.** Every machine computes it from level content everyone
loads, so a crossing costs zero bytes. That is tested, not assumed: the plugin's `VT.Atlas.Quiescence`
tests cross a region on every tick and check that the session sends no more than an idle one, within a
small allowance for timing.

**Discovery is the one thing that replicates**, because which regions a player has found is per-player
knowledge that cannot be derived locally. Measured on a local connection over two matched 3-second
windows, one idle and one with 32 discoveries recorded at once:

| | |
|---|---|
| 32 discoveries | **1,478 bytes**, in **one** extra packet |
| Per discovery, in that burst | 46 bytes |
| For scale: the idle connection over the same 3 seconds | 7,276 bytes in 181 packets |

Discoveries coalesce. Thirty-two of them arriving at once cost a single extra packet, because they
travel as one property update rather than one message each. The whole burst is about a fifth of what
the connection spends doing nothing over the same three seconds. The figures were identical across
three runs.

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

Because at the sizes this plugin is built for, one would buy back time nobody is spending. At a
hundred regions the scan answers in under 300 nanoseconds, and an index would add memory, a second
structure to keep correct, and work every time a region streams in or out.

At thousands of regions the trade changes, so we built the alternatives and measured them on the same
corpora, checking every answer against the scan's before timing it. At 5,000 regions, as the median
over three runs and the three scatterings:

| Structure | Query | Add one region | Remove one region | Index memory a region |
|---|---:|---:|---:|---:|
| The shipped registry (a scan) | 25.4 µs | 1.3 µs | 0.2 µs | none |
| The same scan over packed arrays | 8.1 µs | 1.4 µs | 3.1 µs | 52 bytes |
| Sort and sweep on one axis | 1.9 µs | 3.2 µs | 5.0 µs | 72 bytes |
| Uniform grid | 30 ns | 2.2 µs | 3.6 µs | 651 bytes |
| Bounding volume hierarchy | 82 ns | 2.4 ms | 2.4 ms | 118 bytes |
| Engine octree | 248 ns | 0.5 µs | 407 µs | 495 bytes |
| Engine physics scene | 2.2 µs | 35 µs | 3.6 ms | held by the physics engine |

The trees and the physics scene answer quickly and pay heavily when a region streams in or out, which a
streaming level does all the time. The uniform grid does not: it answers in tens of nanoseconds and
adds or removes a region in a few microseconds, for about the registry's own memory again. If VT Atlas
gains an index, that is the candidate, and the roadmap lists one for very large levels.

If your project has thousands of regions and you are seeing this in a profile, get in touch.

## What is not measured here

- **Crossing cost.** That is the engine's overlap system, not ours. Profile it with `stat Physics`.
- **A real scene.** These corpora are synthetic: uniform, clustered and mixed-size scatterings of
  axis-aligned boxes. A real level also has rotated boxes, spheres, capsules and spline regions, and
  each tests its own shape after the same bounds check.
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
`VTATL_RegionsAtLocation`. A `VTATL` CSV category is registered and off by default; it is reserved,
and nothing records into it yet.

## Capture

| | |
|---|---|
| Date | 2026-10-13 |
| Runner | AMD Ryzen 9 9950X3D, 16 cores / 32 threads, 62 GB RAM, Windows 11 Pro, the benchmark held to the first eight cores |
| Engine | UE 5.8.3, Development editor build, `-nullrhi` |
| Method | Three runs; 20,000 queries per cell, half uniformly random and half a coherent walk; medians quoted |
| Corpus | Generated from a fixed seed, so the same corpus reproduces on any machine |
| Raw data | [spatial-2026-10-13.csv](https://docs.vestro.hr/perf/spatial-2026-10-13.csv), all three runs, and [replication-2026-10-13.txt](https://docs.vestro.hr/perf/replication-2026-10-13.txt), the wire measurement's log lines |
| Harness | A benchmark commandlet and a network test in our own development tree; neither ships with the plugin |

In the CSV, `shipped-registry` is the registry itself, and `linear-tmap` is a bare model of its scan
that the harness uses as the reference answer for every other row. Every structure in the comparison
answered every query exactly as the scan did, in all three runs. A benchmark that does not verify its
answers is measuring how fast something produces the wrong result.
