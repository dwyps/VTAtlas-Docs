---
slug: /roadmap
description: "What is coming to VT Atlas, what is being considered, and what it will deliberately never do."
---

# Roadmap

What is planned, what is being weighed, and what VT Atlas will not do. The last list is the useful one:
knowing where a plugin stops is worth more than a wish list.

Nothing here is a date. Items move when they are ready, and the order below is roughly the order they
are likely to arrive in.

## Planned

**Save and restore discovery.** Discovery is per player and lives in memory today, so a map that filled
in during a session starts empty in the next one. The plan is a pair of functions that hand you the
discovered set as plain data and take it back, so it goes in whatever save system you already have
rather than one this plugin invents.

**A spatial index for very large levels.** The work is already done and measured: at a hundred regions
a plain scan answers in a fifth of a microsecond and an index would be slower overall once streaming
cost is counted. Past a few thousand regions that reverses. A uniform grid is the measured winner and
it ships behind a setting when somebody has a level that needs it. See
[Performance](./03_reference/02_performance.md) for the numbers behind that decision.

**An editor region browser.** A panel listing every region in the level with its tag, volume count,
depth and current occupants, so you can find the one you mean without hunting the outliner. Today the
gameplay debugger shows this at runtime and the editor shows nothing.

**Region volume presets.** Placing a volume still means setting a tag, a shape and a tracked-object
list every time. A preset asset would carry a configured starting point, which matters most for teams
where one person defines the conventions and everyone else follows them.

## Considering

These are real ideas with real arguments against them. They ship only if the argument for wins.

**A Gameplay Ability System bridge.** Granting an ability or applying an effect while an actor is in a
region is an obvious fit, and it was deliberately left out of v1: VT Atlas has no GAS dependency today
and adding one makes every buyer carry it. The likely answer is a separate optional module rather than
a dependency in the core plugin.

**Region-scoped audio helpers.** Crossfading ambience on region edges is one of the most common things
people build with this. It is also five nodes, and a helper that saves five nodes but only fits one
project's audio setup is worse than the five nodes.

**Volume shapes from static meshes.** Spline regions already cover outlines that a box cannot. Taking
the shape from an arbitrary mesh is possible and would mostly be used to make regions far more
expensive than they need to be.

**Per-region net relevancy hints.** Regions know who is where, which is exactly what relevancy wants.
This one is genuinely hard to do without making promises about netcode that the plugin cannot keep.

## Not planned

Deliberate limits, not gaps.

**A region vocabulary.** VT Atlas will never ship a set of region names or a depth convention. Regions
are your gameplay tags and the hierarchy is yours; a built-in vocabulary would be a second place to say
the same thing.

**Replicated region state.** Membership is computed identically on every machine from level content
everyone loads, so there is nothing worth sending. Discovery replicates because it is genuinely
per-player knowledge. Nothing else will.

**Pathfinding, navigation or AI behaviour.** Regions can tell an AI where it is. What it does about
that belongs in your behaviour tree, not here.

**A quest or objective system.** Regions are a good trigger for objectives and a bad place to keep
them.

## Asking for something

If you need one of these sooner, or something that is not here, say so through the
[contact form](https://vestro.hr/#contact). Knowing that a real project is blocked on an item moves it
up this list faster than anything else.
