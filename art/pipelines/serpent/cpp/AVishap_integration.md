# Wiring USerpentBodyComponent into the existing AVishap (not applied: the game project was not touched)

AVishap already keeps everything the component needs: `HeadPos`, `Trail` (head positions, newest first, `TrailStep`
apart), `JawOpen` (0..1, set by the breath and spit states), `HitFlash`, `LifeTime`, `bBoss` and `Tier`. The serpent
replaces the winged CC-BY dragon (`BuildDragon`/`UpdateDragon`). The invisible sphere `Segments` stay as hit volumes.

1. Copy `SerpentBodyComponent.h/.cpp` into `Game/Source/Twilight/`. They only need the `Engine` module, which is already
   a dependency. Optionally add `TWILIGHT_API` to the class line.
2. Import the assets into `TwilightAssets.uproject`:
   `SERP_SRC=<deliver dir> SERP_DEST=/Game/Twilight/Vishap SERP_LEVEL=0 UnrealEditor-Cmd TwilightAssets.uproject -ExecutePythonScript=<deliver>/scripts/ue_build.py -unattended -nullrhi`

```cpp
// ---- Vishap.h (members)
#include "SerpentBodyComponent.h"
	UPROPERTY() TObjectPtr<USerpentBodyComponent> Serpent;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> SerpentMat;
	TArray<FVector> SerpentPath;
	float SerpentJaw = 0.f;
	void BuildSerpent();
	void UpdateSerpent(float Dt);

// ---- Vishap.cpp
static const TCHAR* SerpentMeshPath  = TEXT("/Game/Twilight/Vishap/Mesh/SK_VishapSerpent/SkeletalMeshes/SK_VishapSerpent.SK_VishapSerpent");
static const TCHAR* SerpentHornsPath = TEXT("/Game/Twilight/Vishap/Mesh/Horns/SM_VishapHorns/StaticMeshes/SM_VishapHorns.SM_VishapHorns");

void AVishap::BuildSerpent()      // call from BeginPlay() after Build(), instead of BuildDragon()
{
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, SerpentMeshPath);
	if (!Mesh) return;
	Serpent = NewObject<USerpentBodyComponent>(this);
	Serpent->SetupAttachment(RootComponent);
	Serpent->SetAbsolute(true, true, true);              // bones are placed in world space
	Serpent->SetSkinnedAssetAndUpdate(Mesh);
	Serpent->HeadAttachment = LoadObject<UStaticMesh>(nullptr, SerpentHornsPath);   // optional horns
	Serpent->HeadScale = bBoss ? 1.5f : 1.35f;
	// the mesh is 10 m (1000 cm) long at scale 1
	const float WantLen = bBoss ? 9000.f : (Tier ? 3200.f : 2600.f);
	Serpent->SetWorldScale3D(FVector(WantLen / 1000.f));
	Serpent->RegisterComponent();
	const TCHAR* MI = bBoss ? TEXT("/Game/Twilight/Vishap/Materials/MI_Vishap_Storm.MI_Vishap_Storm")
	                 : (Tier ? TEXT("/Game/Twilight/Vishap/Materials/MI_Vishap_Bronze.MI_Vishap_Bronze")
	                         : TEXT("/Game/Twilight/Vishap/Materials/MI_Vishap_Default.MI_Vishap_Default"));
	SerpentMat = Serpent->CreateDynamicMaterialInstance(0, LoadObject<UMaterialInterface>(nullptr, MI));
	for (UStaticMeshComponent* Sg : Segments) if (Sg) Sg->SetVisibility(false, true);
	// hit volumes over the real body: radius about 1.9 % of the length (taper to the tail)
	if (NumSeg > 1)
	{
		const float Step = WantLen / (NumSeg - 1);
		for (int32 i = 0; i < NumSeg && i < Segments.Num(); ++i)
		{
			const float A = float(i) / (NumSeg - 1);
			SegDist[i] = i * Step;
			SegRadius[i] = WantLen * 0.019f * (i == 0 ? 1.6f : FMath::Lerp(1.f, 0.25f, FMath::Square(A)));
			Segments[i]->SetWorldScale3D(FVector(SegRadius[i] / 50.f));
		}
	}
}

void AVishap::UpdateSerpent(float Dt)   // call from Tick() after UpdateBody(); the Trail is long enough because SegDist covers the body
{
	if (!Serpent) return;
	SerpentPath.Reset(Trail.Num() + 1);
	SerpentPath.Add(HeadPos);
	SerpentPath.Append(Trail);
	// the scan's mouth is half open: -0.8 closes it, +1 gapes (breath / spit)
	SerpentJaw = FMath::FInterpTo(SerpentJaw, FMath::Lerp(-0.8f, 1.f, JawOpen), Dt, 8.f);
	Serpent->JawOpen = SerpentJaw;
	Serpent->ApplyPath(SerpentPath, FVector::UpVector, LifeTime);
	if (SerpentMat)
	{
		const bool bFiring = State == EVishapState::Breath || State == EVishapState::BreathWindup;
		SerpentMat->SetScalarParameterValue(TEXT("MouthGlow"), bFiring ? 20.f : 3.f + 1.f * FMath::Sin(LifeTime * 3.f));
		SerpentMat->SetScalarParameterValue(TEXT("HitFlash"), HitFlash);
	}
}

// MouthLocation(): the snout tip is 50 cm in front of the Head bone (mesh scale 1, bone +X = forward)
//	if (Serpent) return Serpent->GetSocketTransform(TEXT("Head")).TransformPosition(FVector(45.f, 0.f, -3.f));
// (the socket transform already carries the component scale and HeadScale, so the offset is in mesh centimetres)
// UpdateDying(): stop calling ApplyPath and let the debris code move the Segments, or keep ApplyPath with a
// falling HeadPos so the corpse sinks into the lake.
```

Notes
- `ApplyPath` accepts a path with any spacing. Points are sampled at each bone's rest distance times the component
  scale, so the body length never changes. If the trail is shorter than the body, the tail continues straight.
- The swim wave (`WaveAmplitude/WaveLength/WaveSpeed`) is added on top of the trail. It is small at the head, so
  aiming and breath still come from the head pose. Set `WaveAmplitude` to 0 for a pure follow-the-leader body.
- Banking comes from the path's own curvature (smoothed). Set `BankPerCurvature` to 0 to turn it off.
- LOD: `LodDistances` (cm at component scale 1) forces LOD0/1/2 by the nearest body point. The defaults are 2500 and 7000,
  which is 100 m and 280 m for a 40 m serpent. Empty the array to fall back to the engine's screen-size LOD.
- Bounds: `CalcBounds` encloses the posed bones (plus head width). Culling and shadows stay correct even when the
  pose is far from the reference pose. No physics asset is needed: import skips it and hits use the Segments.
- The old "hide when the camera is inside" trick still applies: hide `Serpent` if the camera is closer than
  about 1.5 × the body radius to `Serpent->GetBodyPoint(a)` for any a.
