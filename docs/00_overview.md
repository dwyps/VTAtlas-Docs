---
slug: /overview
description: "Tag-driven regions and zones for Unreal Engine 5.8. What VT Atlas is, and where to start."
---

# VT Atlas

A region and zone system built on gameplay tags. Place a volume, give it a tag, and ask three
questions with one honest answer each:

- **Is this actor in that region?**
- **Which single region is it in?**
- **Who is in that region?**

Everything is callable from Blueprint. Nothing needs C++.

## Regions are your tags

VT Atlas ships no region vocabulary and imposes no depth. You name your regions in the project's
gameplay tag table, and the hierarchy you write is the hierarchy the plugin uses.

```
Castle
Castle.Keep
Castle.Keep.Hall
Castle.Keep.Hall.Vault
```

Place one volume tagged `Castle.Keep.Hall.Vault` and an actor standing in it is in the vault, in the
hall, in the keep and in the castle. You did not place four volumes, and nothing had to be told that a
vault sits inside a hall. The tag said so.

## Two words, everywhere

Every query and every event comes in two forms, and they mean the same thing wherever you see them.
**Exact** is about volumes carrying precisely that tag. **Or Nested** counts the hierarchy too.

Neither implies the other, which is why both exist. See [Concepts](./02_concepts.md)
for the case that catches people out.

## What is in the box

- Box, sphere, capsule and **spline** region volumes. A spline region is the shape you draw, baked to
  convex hulls at save time, so a query tests the same geometry the collision body was built from.
- Per-player **discovery**, server-authoritative and replicated to its owning client only.
- A **region listener** component and a **region occupant** interface, for the two different ways you
  want to hear about a crossing.
- **Region features**: behaviour attached to a region rather than to an actor.
- A gameplay debugger category, console commands, `stat VTATL` counters and Insights scopes.
- A sample keep you can walk through, with a minimap that fogs undiscovered regions.

## Requirements

Unreal Engine **5.8**. Windows and Mac. No third-party plugin dependencies.

## Start here

1. **[Setup](./01_getting_started/01_setup.md)** puts a working region in your level in about ten minutes.
2. **[Sample Walkthrough](./01_getting_started/02_sample_walkthrough.md)** walks the shipped keep and
   shows per-player discovery with two players.
3. **[Concepts](./02_concepts.md)** is the one page worth reading end to end before
   you build on it.
4. **[API Tour](./03_reference/01_api_tour.md)** when you know what you want and need the node name.

Something not behaving? **[Troubleshooting](./04_support/01_troubleshooting.md)** quotes every message
the plugin can print.

## These docs are an Obsidian vault

The `docs` folder is a plain Markdown vault. Point Obsidian's **Open folder as vault** at it and you get
the whole thing offline, with the graph, the file tree and working links between pages. It ships inside
the plugin too, at `Plugins/VTAtlas/Docs`, so you already have it once VT Atlas is installed.
