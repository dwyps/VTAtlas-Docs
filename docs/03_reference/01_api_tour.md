---
slug: /reference/api-tour
description: "Every Blueprint-callable node in VT Atlas, grouped by the question you are trying to ask."
---

# API tour

Everything here is callable from Blueprint. Get the **VT Atlas Region Subsystem** from the world and
the whole query surface is on it.

Read Concepts first if you have not: **Exact** and **Or Nested** appear in almost every name here and
they answer different questions.

## Asking about an actor

| Node | Answers |
|---|---|
| `Is Actor In Region Exact` | Is the actor inside a volume that literally carries this tag |
| `Is Actor In Region Or Nested` | Is the actor in this region or anything under it |
| `Get Actor Regions Exact` | Every tag a volume authored that currently holds this actor |
| `Get Resolved Region` | The one region the actor is in, by the documented rule |
| `Get Time In Region` | How long the actor has been in this region, counting nested |

`Get Actor Regions Exact` returns an **array**, not a tag container, and that is deliberate. A gameplay
tag container fills in parent tags on every add, so a container holding `Castle.Keep.Hall` answers yes
to "do you have Castle.Keep" no matter how it was built. "Exactly these tags" cannot be expressed in
that type, so the plugin does not pretend otherwise.

`Get Time In Region` returns **false** when the actor is not in the region, which is not the same as
zero seconds. An actor that entered this frame has been there for zero seconds. Check the return value
before you draw the number.

## Asking about a region

| Node | Answers |
|---|---|
| `Get Actors In Region Exact` | Who is inside a volume carrying this tag |
| `Get Actors In Region Or Nested` | Who is in this region or anything under it |
| `Is Region Defined` | Does any volume carry this tag right now |
| `Get Region Display Name` | The name from the region definition asset, if one supplies it |
| `Get Child Regions With Volumes` | Regions under this one that actually exist in the level |
| `Get Child Regions In Tag Table` | Regions under this one in the project's tag table |

The last two are genuinely different questions. The tag table lists what a designer has named; the
volume list is what the level actually contains. A minimap wants the second one.

Every container query returns a **stable order**. Two machines running the same level get the same
array, which matters more than it sounds: gameplay tags cannot be sorted with the obvious comparison,
because it reports `Zone1` and `Zone01` equal while equality reports them different.

## Asking about a place

`Find Regions At Location Exact` and `Find Regions At Location With Parents` answer which regions
contain a world point, with no actor and no overlap involved. Use them for spawn selection, for
placing something sensibly, or for a cursor.

These test the **shape**, not its bounding box. A rotated box does not claim the corners of its bounds,
and a spline region does not claim the space its outline wraps around.

## Hearing about crossings

Three surfaces, and Concepts explains when to use which.

**The Region Occupant interface**, on an actor:

- `On VTATL Region Entered Exact` / `Exited Exact`
- `On VTATL Region Entered Or Nested` / `Exited Or Nested`

**The Region Listener component**, on an actor:

- `On Entered Region` / `On Exited Region`, filtered by **Watched Regions**
- `On Current Region Changed`, carrying the region info with a display name
- `Get Current Region`, `Get Time In Region`

Watching a region also watches everything nested under it: watch `Castle.Keep` and you hear about
`Castle.Keep.Hall`. Leave **Watched Regions** empty to hear about everything.

**The subsystem's delegates**, for anything that is not the actor crossing:

- `On Actor Entered Region Exact` / `Or Nested`, and the two exits
- `On Region Added` / `On Region Removed`, when a region appears in or disappears from the world

The last pair is about level content, not actors. It fires for the first volume carrying a tag and the
last one leaving, and never for the ones in between, which is what a minimap actually wants.

## Placing regions

Four actors, all placed and sized like any trigger:

- **VT Atlas Region Volume (Box)**
- **VT Atlas Region Volume (Sphere)**
- **VT Atlas Region Volume (Capsule)**
- **VT Atlas Region Volume (Spline)** - draw a closed spline, set the height range, press **Rebuild
  Footprint**

Each carries a **Region Tag**, or points at a **Region Definition** asset that supplies one along with
a display name. A definition is worth it when several volumes share a region: change the name once.

Shared settings on every volume:

- **Priority**, which decides the resolved region when volumes overlap
- **Tracked Object Types**, layer zero
- **Occupant Filter**, layer one
- **Explain Actor Tracking**, the node to call when nothing happens

## For C++

The queries are on `UVTATLRegionSubsystem` with the same names. Two extension points:

`IVTATLRegionOccupant` - override the `_Implementation` you care about. Test with
`Implements<UVTATLRegionOccupant>()`, never `Cast<>`: a cast silently misses actors that implement the
interface in Blueprint.

`AVTATLRegionVolumeBase` - the shape family's base. Deriving is supported; `CaptureShape` is what a
sibling overrides to describe its geometry.

The registration seam takes plain data: build an `FVTATLVolumeDesc` and call `Register Volume`. It is
public so a procedural level can make regions without placing actors. A descriptor with no shape
becomes a box matching its bounds; a descriptor with a shape that cannot answer containment is
refused rather than substituted.

## From C++

Everything above is equally callable from C++. Add the module dependency and include the subsystem:

```cpp
// YourModule.Build.cs
PublicDependencyModuleNames.AddRange(new[] { "VTAtlas", "GameplayTags" });
```

```cpp
#include "VTATLRegionSubsystem.h"
```

### The three questions

`UVTATLRegionSubsystem` is a world subsystem: one per world, nothing to place, nothing to initialise.

```cpp
UVTATLRegionSubsystem* Atlas = GetWorld()->GetSubsystem<UVTATLRegionSubsystem>();
if (Atlas == nullptr)
{
    return;
}

// Is this actor in that region? "OrNested" counts the hierarchy, "Exact" does not.
const bool bInCastle = Atlas->IsActorInRegionOrNested(Pawn, TAG_Castle);

// Which single region is it in? False when the actor is in none, rather than an empty tag you
// then have to test separately.
FGameplayTag Resolved;
if (Atlas->GetResolvedRegion(Pawn, Resolved))
{
    FText DisplayName;
    Atlas->GetRegionDisplayName(Resolved, DisplayName);
}

// Who is in that region?
const TArray<AActor*> Occupants = Atlas->GetActorsInRegionExact(TAG_Vault);
```

### Hearing about crossings

```cpp
void AMyGameMode::BeginPlay()
{
    Super::BeginPlay();

    if (UVTATLRegionSubsystem* Atlas = GetWorld()->GetSubsystem<UVTATLRegionSubsystem>())
    {
        Atlas->OnActorEnteredRegionOrNested.AddDynamic(this, &AMyGameMode::HandleEntered);
        Atlas->OnRegionOccupied.AddDynamic(this, &AMyGameMode::HandleRegionOccupied);
    }
}

void AMyGameMode::HandleEntered(AActor* Actor, FGameplayTag RegionTag)
{
    // THIS RUNS ON THE SERVER AND ON EVERY CLIENT. Regions are computed from level content that
    // everyone loads, so anything awarded here is awarded once per connection unless you gate it.
    if (!HasAuthority())
    {
        return;
    }

    GrantAreaBonus(Actor, RegionTag);
}

void AMyGameMode::HandleRegionOccupied(FGameplayTag RegionTag)
{
    // The first occupant arrived. This carries no actor, which is the point: enters and exits are
    // not conserved once an actor is destroyed, so a count kept by hand drifts and this one cannot.
    ArmEncounter(RegionTag);
}
```

### Dwell time

```cpp
double Seconds = 0.0;
if (Atlas->GetTimeInRegion(Pawn, TAG_Arena, Seconds) && Seconds >= 120.0)
{
    CompleteObjective();
}
```

It returns false rather than zero when the actor is not in the region, because an actor that arrived
this instant has genuinely been there for zero seconds and the two need telling apart.

