#include "VahagnWorld.h"
#include "Twilight.h"
#include "TwAssets.h"

#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "TwFx.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "TimerManager.h"
#include "Camera/CameraActor.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

// real relief of Mount Ararat (Masis): 257x257 heights, AWS Terrain Tiles (Mapzen terrarium, public domain sources)
#include "MasisHeight.inl"
#include "IslandHeights.inl"

// sea palette under the HDRI sky: deep water is darker than the sky, it only mirrors the lavender at grazing angles
static const FLinearColor SeaDeep(0.028f, 0.02f, 0.06f);
static const FLinearColor SeaHorizon(0.33f, 0.25f, 0.45f);
static const FLinearColor SeaReflect(0.62f, 0.48f, 0.72f);

AVahagnWorld::AVahagnWorld()
{
	Sea = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Sea"));
	Sea->SetupAttachment(RootComponent);
}

void AVahagnWorld::BuildLevel()
{
	BuildSkyDome();
	BuildSea();
	BuildIslands();
	// the crimson reed of the birth myth, standing out of the sea at the world centre
	UMaterialInstanceDynamic* ReedMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_FireBody")), this);
	if (ReedMat)
	{
		// the crimson reed: its own palette, not the hero gold
		ReedMat->SetScalarParameterValue(TEXT("EmissiveIntensity"), 2.2f);
		ReedMat->SetVectorParameterValue(TEXT("SkinColor"), FLinearColor(0.25f, 0.01f, 0.02f));
		ReedMat->SetVectorParameterValue(TEXT("CrackColorDeep"), FLinearColor(0.45f, 0.f, 0.04f));
		ReedMat->SetVectorParameterValue(TEXT("CrackColorHot"), FLinearColor(1.f, 0.12f, 0.18f));
		ReedMat->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(0.9f, 0.05f, 0.2f));
	}
	const FVector Base(0.f, 0.f, -200.f);
	for (int32 i = 0; i < 4; ++i)
	{
		UStaticMeshComponent* S = NewObject<UStaticMeshComponent>(this);
		S->SetStaticMesh(i == 0 ? TwAssets::Cylinder() : TwAssets::Cone());
		S->SetupAttachment(RootComponent);
		S->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		S->RegisterComponent();
		if (i == 0) { S->SetWorldLocation(Base + FVector(0, 0, 450.f)); S->SetWorldScale3D(FVector(0.3f, 0.3f, 9.f)); }
		else
		{
			// long leaves
			const float Yaw = i * 120.f;
			S->SetWorldLocation(Base + FVector(0, 0, 250.f + i * 120.f) + FRotator(0, Yaw, 0).RotateVector(FVector(40.f, 0, 0)));
			S->SetWorldRotation(FRotator(-25.f, Yaw, 0.f) + FRotator(0, 0, 0));
			S->SetWorldScale3D(FVector(0.18f, 0.05f, 3.2f));
		}
		if (ReedMat) S->SetMaterial(0, ReedMat);
	}
}

void AVahagnWorld::BuildSea()
{
	if (UStaticMesh* PlaneMesh = TwAssets::Plane()) Sea->SetStaticMesh(PlaneMesh);
	Sea->SetMobility(EComponentMobility::Movable);
	Sea->SetWorldLocation(FVector(0, 0, 0));
	Sea->SetWorldScale3D(FVector(40000.f, 40000.f, 1.f)); // 40 km: the plane edge must never show, even from altitude
	Sea->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Sea->SetCastShadow(false);
	UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Water_Purple")), this);
	if (M)
	{
		M->SetVectorParameterValue(TEXT("DeepColor"), SeaDeep);
		M->SetVectorParameterValue(TEXT("HorizonColor"), SeaHorizon);
		M->SetVectorParameterValue(TEXT("SkyReflectColor"), SeaReflect);
		// larger, softer ripples: the hero flies high, small tiles read as a repeating dot pattern
		M->SetScalarParameterValue(TEXT("NormalTile"), 2800.f);
		M->SetScalarParameterValue(TEXT("NormalStrength"), 0.45f);
		// any periodic normal pattern aliases into a dot lattice when seen from altitude (83% res + TAA):
		// ripples only near the lens, glassy dusk water beyond
		M->SetScalarParameterValue(TEXT("NormalFadeDistance"), 30000.f);
		M->SetScalarParameterValue(TEXT("OceanStrength"), 0.35f);
		// the crest tint is a sum of three periodic sines in the base colour: a bright dot lattice from altitude
		M->SetScalarParameterValue(TEXT("CrestAmount"), 0.f);
		// tuning overrides: -TwSea="OceanStrength=0.3,NormalFadeDistance=8000"
		FString Ov;
		if (FParse::Value(FCommandLine::Get(), TEXT("TwSea="), Ov, false))
		{
			TArray<FString> Parts; Ov.ParseIntoArray(Parts, TEXT(","));
			for (const FString& Pp : Parts) { FString K, V; if (Pp.Split(TEXT("="), &K, &V)) M->SetScalarParameterValue(FName(*K), FCString::Atof(*V)); }
		}
		Sea->SetMaterial(0, M);
		SeaMat = M;
	}
}

// ---------------------------------------------------------------- storm (boss phase)
void AVahagnWorld::Tick(float Dt)
{
	Super::Tick(Dt);
	// -TwViewMasis (debug): a fixed camera on the horizon toward Masis, re-asserted every frame
	static bool bViewMasis = FParse::Param(FCommandLine::Get(), TEXT("TwViewMasis"));
	if (bViewMasis && GetWorld()->GetTimeSeconds() > 1.f)
		if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		{
			if (!DebugCam)
			{
				const FVector From(0.f, 0.f, 3000.f);
				DebugCam = GetWorld()->SpawnActor<ACameraActor>(From, (FVector(-1900000.f, 1500000.f, 120000.f) - From).Rotation());
			}
			if (DebugCam && PC->GetViewTarget() != DebugCam) PC->SetViewTarget(DebugCam);
		}
	Storm = FMath::FInterpConstantTo(Storm, StormTarget, Dt, 1.f / 6.f); // ~6 s blend
	if (!FMath::IsNearlyEqual(Storm, LastApplied, 0.002f)) ApplyStorm(Storm);
	// the sky light is a static capture: refresh it halfway through and at the end of the blend
	if (FMath::Abs(Storm - CapturedAt) >= 0.5f || (Storm == StormTarget && CapturedAt != Storm))
	{
		if (SkyLight) SkyLight->RecaptureSky();
		CapturedAt = Storm;
	}

	if (Storm > 0.6f)
	{
		NextStrike -= Dt;
		if (NextStrike <= 0.f) { StrikeLightning(); NextStrike = FMath::FRandRange(3.5f, 8.f); }
	}
	UpdateBolt(Dt);
}

void AVahagnWorld::ApplyStorm(float K)
{
	LastApplied = K;
	const FTwSkyPreset B = GetSkyPreset();
	const float E = K * K * (3.f - 2.f * K);
	auto L = [E](const FLinearColor& A, const FLinearColor& C) { return FMath::Lerp(A, C, E); };
	if (Sun) { Sun->SetIntensity(FMath::Lerp(B.SunIntensity, 4.f, E)); Sun->SetLightColor(L(B.SunColor, FLinearColor(1.f, 0.28f, 0.12f))); }
	if (Atmosphere)
	{
		// keep Rayleigh (it is what lights the upper sky); tint the whole dome crimson and thicken the haze
		Atmosphere->SetSkyLuminanceFactor(L(FLinearColor(1.05f, 0.85f, 1.2f), FLinearColor(1.6f, 0.42f, 0.55f)));
		Atmosphere->SetMieScatteringScale(FMath::Lerp(0.006f, 0.018f, E));
	}
	if (Fog)
	{
		Fog->SetFogInscatteringColor(L(B.FogColor, FLinearColor(0.30f, 0.035f, 0.07f)));
		Fog->SetDirectionalInscatteringColor(L(B.FogSunColor, FLinearColor(1.f, 0.18f, 0.06f)));
		Fog->SetFogDensity(FMath::Lerp(B.FogDensity, 0.018f, E));
	}
	if (SkyLight) { SkyLight->SetIntensity(FMath::Lerp(B.SkyLightIntensity, 0.8f, E)); SkyLight->SetLightColor(L(B.SkyLightColor, FLinearColor(1.f, 0.5f, 0.55f))); }
	if (Post)
	{
		Post->Settings.ColorGainHighlights = FMath::Lerp(B.GainHighlights, FVector4(1.14f, 0.9f, 0.85f, 1.f), E);
	}
	if (SeaMat)
	{
		SeaMat->SetVectorParameterValue(TEXT("DeepColor"), L(SeaDeep, FLinearColor(0.07f, 0.008f, 0.02f)));
		SeaMat->SetVectorParameterValue(TEXT("HorizonColor"), L(SeaHorizon, FLinearColor(0.4f, 0.05f, 0.09f)));
		SeaMat->SetVectorParameterValue(TEXT("SkyReflectColor"), L(SeaReflect, FLinearColor(0.85f, 0.12f, 0.16f)));
		SeaMat->SetVectorParameterValue(TEXT("SunColor"), L(FLinearColor(1.f, 0.55f, 0.25f), FLinearColor(1.f, 0.22f, 0.08f)));
	}
}

void AVahagnWorld::StrikeLightning()
{
	APlayerController* PC = GetWorld()->GetFirstPlayerController();
	if (!PC || !PC->PlayerCameraManager) return;
	const FVector Cam = PC->PlayerCameraManager->GetCameraLocation();
	FVector Fwd = PC->PlayerCameraManager->GetCameraRotation().Vector(); Fwd.Z = 0.f; Fwd = Fwd.GetSafeNormal();
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd);
	// in view, far enough to read as a bolt on the horizon
	const FVector Ground = Cam + Fwd * FMath::FRandRange(12000.f, 26000.f) + Right * FMath::FRandRange(-10000.f, 10000.f);
	const FVector End(Ground.X, Ground.Y, 0.f);
	const FVector Start = End + FVector(FMath::FRandRange(-4000.f, 4000.f), FMath::FRandRange(-4000.f, 4000.f), 30000.f);

	if (BoltSegs.Num() == 0)
	{
		BoltMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
		if (BoltMat)
		{
			BoltMat->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.85f, 0.75f, 1.f));
			BoltMat->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
			BoltMat->SetScalarParameterValue(TEXT("Intensity"), 16.f);
			BoltMat->SetScalarParameterValue(TEXT("Falloff"), 1.f);
		}
		for (int32 i = 0; i < 18; ++i)
		{
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
			C->SetStaticMesh(TwAssets::Cylinder());
			C->SetupAttachment(RootComponent);
			C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			C->SetCastShadow(false);
			C->SetVisibility(false);
			if (BoltMat) C->SetMaterial(0, BoltMat);
			C->RegisterComponent();
			BoltSegs.Add(C);
		}
	}
	int32 Used = 0;
	auto Seg = [this, &Used](const FVector& A, const FVector& Bp, float W)
	{
		if (Used >= BoltSegs.Num()) return;
		UStaticMeshComponent* C = BoltSegs[Used++];
		const FVector D = Bp - A;
		C->SetWorldLocationAndRotation((A + Bp) * 0.5f, FRotationMatrix::MakeFromZ(D.GetSafeNormal()).Rotator());
		C->SetWorldScale3D(FVector(W, W, D.Size() / 100.f));
		C->SetVisibility(true);
	};
	// main channel: 11 jagged segments, two short forks
	TArray<FVector> Pts;
	const int32 N = 11;
	for (int32 i = 0; i <= N; ++i)
	{
		const float T = i / float(N);
		const float J = (i == 0 || i == N) ? 0.f : 1400.f * (1.f - 0.4f * T);
		Pts.Add(FMath::Lerp(Start, End, T) + FVector(FMath::FRandRange(-J, J), FMath::FRandRange(-J, J), 0.f));
	}
	for (int32 i = 0; i < N; ++i) Seg(Pts[i], Pts[i + 1], 1.4f);
	for (int32 f = 0; f < 2; ++f)
	{
		FVector P = Pts[FMath::RandRange(2, 6)];
		const FVector Dir = (FVector(FMath::FRandRange(-1.f, 1.f), FMath::FRandRange(-1.f, 1.f), -1.4f)).GetSafeNormal();
		for (int32 k = 0; k < 3; ++k)
		{
			const FVector Q = P + Dir * 2200.f + FVector(FMath::FRandRange(-700.f, 700.f), FMath::FRandRange(-700.f, 700.f), 0.f);
			Seg(P, Q, 0.7f);
			P = Q;
		}
	}
	for (int32 i = Used; i < BoltSegs.Num(); ++i) BoltSegs[i]->SetVisibility(false);
	BoltAge = 0.f;
	UE_LOG(LogTwilight, Display, TEXT("[TwTest] lightning at %s dist=%.0f"), *End.ToCompactString(), FVector::Dist(Cam, End));
	TwFx::Burst(GetWorld(), TwFx::EFx::Splash, End + FVector(0, 0, 10.f), 3.f);
	// thunder arrives after the flash
	const float Delay = FMath::Clamp((float)FVector::Dist(Cam, End) / 34300.f * 0.6f, 0.25f, 1.4f);
	FTimerHandle H;
	TWeakObjectPtr<AVahagnWorld> Self(this);
	GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateLambda([Self]()
	{
		if (Self.IsValid()) TwFx::Sound2D(Self->GetWorld(), TEXT("sfx_big_explosion"), 0.75f, 0.42f);
	}), Delay, false);
}

void AVahagnWorld::UpdateBolt(float Dt)
{
	if (BoltAge > 1.f) return;
	BoltAge += Dt;
	// flicker: on, off, on again, fade
	const bool bOn = BoltAge < 0.07f || (BoltAge > 0.12f && BoltAge < 0.32f);
	const float Fade = FMath::Clamp(1.f - (BoltAge - 0.12f) / 0.2f, 0.f, 1.f);
	for (UStaticMeshComponent* C : BoltSegs) if (C && C->IsVisible() != (bOn && BoltAge < 0.32f)) C->SetVisibility(bOn && BoltAge < 0.32f);
	if (BoltMat) BoltMat->SetScalarParameterValue(TEXT("Intensity"), 16.f * (BoltAge < 0.12f ? 1.f : Fade));
	// the whole sky lights up violet for an instant
	const FTwSkyPreset B = GetSkyPreset();
	if (Moon)
	{
		const float Flash = bOn ? (BoltAge < 0.07f ? 1.f : Fade * 0.7f) : 0.f;
		Moon->SetIntensity(B.MoonIntensity + 6.f * Flash);
		Moon->SetLightColor(FMath::Lerp(B.MoonColor, FLinearColor(0.7f, 0.6f, 1.f), Flash));
	}
	if (BoltAge > 1.f) for (UStaticMeshComponent* C : BoltSegs) if (C) C->SetVisibility(false);
}

void AVahagnWorld::BuildVishapakar(const FVector& Base, float Yaw, float Scale)
{
	UStaticMesh* Cube = TwAssets::Cube();
	UMaterialInstanceDynamic* Stone = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Stone) Stone->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.5f, 0.42f, 0.45f));
	UMaterialInstanceDynamic* Glyph = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Glyph) { Glyph->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.4f, 0.1f)); Glyph->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Glyph->SetScalarParameterValue(TEXT("Intensity"), 7.f); }

	auto Part = [&](const FVector& Rel, const FVector& Scl, UMaterialInterface* M)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Cube);
		C->SetupAttachment(RootComponent);
		C->RegisterComponent();
		const FTransform Tr(FRotator(0, Yaw, 0), Base);
		C->SetWorldLocationAndRotation(Tr.TransformPosition(Rel * Scale), FRotator(0, Yaw, 0));
		C->SetWorldScale3D(Scl * Scale);
		C->SetCollisionEnabled(M == Glyph ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
		C->SetCollisionObjectType(ECC_WorldStatic);
		C->SetCastShadow(M != Glyph);
		if (M) C->SetMaterial(0, M);
	};
	// tall stele (cube is 100 cm): 1.8 m deep (X), 4 m wide (Y), 18 m tall, slightly tapered by a cap
	Part(FVector(0, 0, 900), FVector(1.8f, 4.f, 18.f), Stone);
	Part(FVector(0, 0, 1850), FVector(1.6f, 3.4f, 1.2f), Stone);
	// glowing carved vishap-head and wavy body lines, standing proud of both faces (face at X = +-90)
	for (const float Fx : { 100.f, -100.f })
	{
		Part(FVector(Fx, 0, 1500), FVector(0.1f, 2.4f, 0.25f), Glyph);
		Part(FVector(Fx, 0, 1300), FVector(0.1f, 1.6f, 0.2f), Glyph);
		Part(FVector(Fx, 0, 1000), FVector(0.1f, 2.0f, 0.2f), Glyph);
		Part(FVector(Fx, 0, 700), FVector(0.1f, 1.2f, 0.2f), Glyph);
		Part(FVector(Fx, 0, 1150), FVector(0.1f, 0.2f, 6.0f), Glyph);
	}

	UPointLightComponent* L = NewObject<UPointLightComponent>(this);
	L->SetupAttachment(RootComponent);
	L->RegisterComponent();
	L->SetWorldLocation(Base + FRotator(0, Yaw, 0).RotateVector(FVector(400, 0, 1200)) * Scale);
	L->SetIntensityUnits(ELightUnits::Unitless);
	L->SetIntensity(30000.f);
	L->SetAttenuationRadius(3500.f * Scale);
	L->SetLightColor(FLinearColor(1.f, 0.4f, 0.12f));
	L->SetCastShadows(false);
}

void AVahagnWorld::BuildSkyDome()
{
	UMaterialInterface* M = TwAssets::Material(TEXT("M_SkyHDRI"));
	if (!M) return;
	SkyMat = UMaterialInstanceDynamic::Create(M, this);
	float Yaw = 0.f;
	FParse::Value(FCommandLine::Get(), TEXT("TwSkyYaw="), Yaw);
	if (SkyMat) SkyMat->SetScalarParameterValue(TEXT("Yaw"), Yaw);
	float Exp = 1.f;
	FParse::Value(FCommandLine::Get(), TEXT("TwSkyExp="), Exp);
	if (SkyMat) SkyMat->SetScalarParameterValue(TEXT("Exposure"), Exp);
	UStaticMeshComponent* Dome = NewObject<UStaticMeshComponent>(this);
	Dome->SetStaticMesh(TwAssets::Sphere());
	Dome->SetupAttachment(RootComponent);
	Dome->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dome->SetCastShadow(false);
	Dome->bAffectDistanceFieldLighting = false;
	Dome->SetWorldScale3D(FVector(400000.f)); // 200 km radius: beyond Masis and the sea
	Dome->SetMaterial(0, SkyMat);
	Dome->RegisterComponent();
}

void AVahagnWorld::BuildMasis(UMaterialInterface* Mat)
{
	// height fog would swallow a mountain 25 km away entirely; beyond 15 km only the atmosphere's
	// aerial perspective hazes it, so Masis stands as a pale silhouette against the sunset
	if (Fog) Fog->SetFogCutoffDistance(1500000.f);
	// the real twin-peaked Masis (Greater + Little Ararat), ~18 km wide, ~3.6 km tall, ~26 km away behind the cliffs
	const float Half = 900000.f;                   // cm
	const float HeightScale = 360000.f / (MasisMaxM - MasisMinM);
	auto Sample = [](float U, float V) -> float
	{
		const float X = FMath::Clamp(U, 0.f, 1.f) * (MasisRes - 1), Y = FMath::Clamp(V, 0.f, 1.f) * (MasisRes - 1);
		const int32 X0 = FMath::Min((int32)X, MasisRes - 2), Y0 = FMath::Min((int32)Y, MasisRes - 2);
		const float FX = X - X0, FY = Y - Y0;
		auto H = [](int32 x, int32 y) { return (float)MasisHeight[y * MasisRes + x] / 65535.f; };
		return FMath::Lerp(FMath::Lerp(H(X0, Y0), H(X0 + 1, Y0), FX), FMath::Lerp(H(X0, Y0 + 1), H(X0 + 1, Y0 + 1), FX), FY);
	};
	const float Range = MasisMaxM - MasisMinM;
	BuildTerrain(FVector(-1900000.f, 1500000.f, -2000.f), Half, Half, 240, 240, [&](float X, float Y)
	{
		// row 0 of the data is north; our -Y is north here
		const float U = (X + Half) / (2.f * Half), V = (Y + Half) / (2.f * Half);
		const float Hm = Sample(U, V) * Range;                     // metres above the lowest point
		const float R = FMath::Sqrt(FMath::Square(U - 0.5f) + FMath::Square(V - 0.5f)) * 2.f;
		const float Window = 1.f - FMath::SmoothStep(0.62f, 0.98f, R); // edges sink under the sea
		return Hm * HeightScale * Window - (1.f - Window) * 60000.f;
	}, Mat, false, 400000.f);
	if (Heightfields.Num() > 0 && Heightfields.Last())
		UE_LOG(LogTwilight, Display, TEXT("[TwMasis] bounds origin=%s extent=%s"), *Heightfields.Last()->Bounds.Origin.ToCompactString(), *Heightfields.Last()->Bounds.BoxExtent.ToCompactString());
}

// island from real relief: crop Index (0..7), Radius/Height in cm; returns the peak height
static float IslandZ(int32 Index, float X, float Y, float Radius, float Height)
{
	const float U = FMath::Clamp((X / Radius + 1.f) * 0.5f, 0.f, 1.f) * (IslandRes - 1);
	const float V = FMath::Clamp((Y / Radius + 1.f) * 0.5f, 0.f, 1.f) * (IslandRes - 1);
	const int32 X0 = FMath::Min((int32)U, IslandRes - 2), Y0 = FMath::Min((int32)V, IslandRes - 2);
	const float FX = U - X0, FY = V - Y0;
	const uint16* D = IslandHeight + (Index % IslandCount) * IslandRes * IslandRes;
	auto H = [D](int32 x, int32 y) { return (float)D[y * IslandRes + x] / 65535.f * 1.3f - 0.3f; };
	const float Base = FMath::Lerp(FMath::Lerp(H(X0, Y0), H(X0 + 1, Y0), FX), FMath::Lerp(H(X0, Y0 + 1), H(X0 + 1, Y0 + 1), FX), FY);
	// fine rocky detail the 29 m/px data cannot carry at this scale
	const float Detail = FMath::PerlinNoise2D(FVector2D(X, Y) / (Radius * 0.12f)) * 0.05f + FMath::PerlinNoise2D(FVector2D(X, Y) / (Radius * 0.035f)) * 0.018f;
	return (Base + (Base > 0.f ? Detail : 0.f)) * Height;
}

void AVahagnWorld::BuildIslands()
{
	// volcanic rock (Poly Haven dark_rock, CC0), triplanar; falls back to the procedural rock
	UMaterialInterface* RockBase = TwAssets::Material(TEXT("M_RockPBR"));
	const bool bPBR = RockBase != nullptr;
	UMaterialInstanceDynamic* Rock = UMaterialInstanceDynamic::Create(bPBR ? RockBase : TwAssets::Material(TEXT("M_Rock")), this);
	if (Rock && !bPBR) Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.42f, 0.3f, 0.34f));
	if (Rock && bPBR) { Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(2.1f, 1.75f, 1.9f)); Rock->SetScalarParameterValue(TEXT("Tiling"), 1500.f); } // dark_rock albedo is near black
	UMaterialInstanceDynamic* Snow = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Snow) { Snow->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.5f, 0.38f, 0.45f)); Snow->SetScalarParameterValue(TEXT("TopAmount"), 1.f); }

	// ring of cliffs around the arena (visual boundary, collidable)
	FRandomStream Rs(4242);
	const int32 Ring = 11;
	for (int32 i = 0; i < Ring; ++i)
	{
		const float A = 2.f * PI * i / Ring + Rs.FRandRange(-0.12f, 0.12f);
		const float Dist = Rs.FRandRange(60000.f, 72000.f);
		const float Rad = Rs.FRandRange(11000.f, 17000.f);
		const float Hgt = Rs.FRandRange(7000.f, 16000.f);
		const int32 Idx = 2 + i % 6;
		BuildTerrain(FVector(FMath::Cos(A) * Dist, FMath::Sin(A) * Dist, 0.f), Rad, Rad, 80, 80, [=](float X, float Y) { return IslandZ(Idx, X, Y, Rad, Hgt); }, Rock, true);
	}
	// three inner islands with vishapakar stones (Aragats-like plateaus)
	const FVector Inner[3] = { FVector(16000, -9000, 0), FVector(-21000, -14000, 0), FVector(-6000, 25000, 0) };
	for (int32 i = 0; i < 3; ++i)
	{
		const float Rad = 7000.f + i * 900.f;
		const float Hgt = 4200.f + i * 900.f;
		const int32 Idx = i == 0 ? 0 : (i == 1 ? 1 : 3); // Little Ararat, the Masis summit ridge, a crater
		BuildTerrain(Inner[i], Rad, Rad, 96, 96, [=](float X, float Y) { return IslandZ(Idx, X, Y, Rad, Hgt); }, Rock, true);
		const float Top = IslandZ(Idx, 0.f, 0.f, Rad, Hgt);
		BuildVishapakar(Inner[i] + FVector(0, 0, Top - 150.f), 30.f + i * 70.f, 1.2f);
	}
	// Masis on the horizon from real elevation data
	UMaterialInstanceDynamic* MasisMat = UMaterialInstanceDynamic::Create(bPBR ? RockBase : TwAssets::Material(TEXT("M_Rock")), this);
	if (MasisMat && bPBR)
	{
		// 25 km of air: mostly sky-coloured haze, the snowfields catching a little warm light
		MasisMat->SetScalarParameterValue(TEXT("Tiling"), 60000.f);
		MasisMat->SetVectorParameterValue(TEXT("Tint"), FLinearColor(1.4f, 1.2f, 1.35f));
		MasisMat->SetScalarParameterValue(TEXT("TopAmount"), 0.6f);
		MasisMat->SetVectorParameterValue(TEXT("TopTint"), FLinearColor(2.f, 1.8f, 2.f));
		MasisMat->SetScalarParameterValue(TEXT("HazeAmount"), 0.5f);
		MasisMat->SetVectorParameterValue(TEXT("HazeColor"), FLinearColor(0.34f, 0.27f, 0.42f));
	}
	if (!FParse::Param(FCommandLine::Get(), TEXT("TwNoMasis"))) BuildMasis(MasisMat ? MasisMat : (Snow ? Snow : Rock));
	(void)Snow;
}

