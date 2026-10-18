#include "AralezWorld.h"
#include "Twilight.h"
#include "TwAssets.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"

namespace
{
	const FLinearColor ZoneFog[3] = { FLinearColor(0.04f, 0.10f, 0.20f), FLinearColor(0.02f, 0.16f, 0.14f), FLinearColor(0.22f, 0.03f, 0.04f) };
	const FLinearColor ZoneGlow[3] = { FLinearColor(0.35f, 0.75f, 1.f), FLinearColor(0.3f, 1.f, 0.7f), FLinearColor(1.f, 0.3f, 0.12f) };
}

AAralezWorld::AAralezWorld() {}

FVector AAralezWorld::PathPoint(float T)
{
	T = FMath::Clamp(T, 0.f, 1.f);
	const float Turns = 2.4f;
	const float A = T * Turns * 2.f * PI;
	const float R = 6500.f + 1500.f * FMath::Sin(T * 7.f);
	const float Z = 2000.f - T * 58000.f + 900.f * FMath::Sin(T * 23.f);
	return FVector(FMath::Cos(A) * R, FMath::Sin(A) * R, Z);
}

FVector AAralezWorld::PathTangent(float T)
{
	const float E = 0.0015f;
	return (PathPoint(FMath::Min(1.f, T + E)) - PathPoint(FMath::Max(0.f, T - E))).GetSafeNormal();
}

float AAralezWorld::TunnelRadius(float T)
{
	// wider caverns around the zone changes and at the very bottom
	const float Base = 1700.f + 300.f * FMath::Sin(T * 41.f) + 250.f * FMath::Sin(T * 13.f + 1.f);
	const float Cav = 1500.f * (FMath::Exp(-FMath::Square((T - 0.36f) / 0.03f)) + FMath::Exp(-FMath::Square((T - 0.7f) / 0.03f))) + 2600.f * FMath::Exp(-FMath::Square((T - 1.f) / 0.04f));
	return Base + Cav;
}

float AAralezWorld::NearestT(const FVector& P, float Hint)
{
	float Best = Hint, BestD = FVector::DistSquared(P, PathPoint(Hint));
	float Step = 0.004f;
	for (int32 Pass = 0; Pass < 3; ++Pass)
	{
		const float C = Best;
		for (int32 i = -8; i <= 8; ++i)
		{
			const float T = FMath::Clamp(C + i * Step, 0.f, 1.f);
			const float D = FVector::DistSquared(P, PathPoint(T));
			if (D < BestD) { BestD = D; Best = T; }
		}
		Step *= 0.2f;
	}
	return Best;
}

FTwSkyPreset AAralezWorld::GetSkyPreset() const
{
	FTwSkyPreset P;
	P.SunIntensity = 0.f;
	P.MoonIntensity = 0.f;
	P.FogColor = ZoneFog[0];
	P.FogSunColor = FLinearColor::Black;
	P.FogDensity = 0.06f;
	P.FogFalloff = 0.0001f;
	P.FogStart = 600.f;
	P.Exposure = 13.2f;
	P.SkyLightIntensity = 0.25f;
	P.SkyLightColor = FLinearColor(0.4f, 0.6f, 1.f);
	P.EmberColor = FLinearColor(0.5f, 0.85f, 1.f);
	P.GainShadows = FVector4(0.85f, 0.95f, 1.2f, 1.f);
	P.GainHighlights = FVector4(1.f, 1.f, 1.05f, 1.f);
	P.ShadowDistance = 3000.f;
	return P;
}

void AAralezWorld::BuildLevel()
{
	BuildTunnel();
	BuildCrystals();
	BuildGate();
}

void AAralezWorld::BuildTunnel()
{
	UMaterialInstanceDynamic* Rock = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Rock) { Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.22f, 0.24f, 0.3f)); Rock->SetScalarParameterValue(TEXT("TopAmount"), 0.f); }

	// split into a few sections so culling works
	const int32 Sections = 6;
	const int32 RingsPerSection = 46;
	const int32 Sides = 26;
	for (int32 Sec = 0; Sec < Sections; ++Sec)
	{
		UProceduralMeshComponent* PM = NewObject<UProceduralMeshComponent>(this);
		PM->SetupAttachment(RootComponent);
		PM->RegisterComponent();
		PM->SetWorldTransform(FTransform::Identity);
		TArray<FVector> V; TArray<int32> Tr; TArray<FVector> N; TArray<FVector2D> UV; TArray<FLinearColor> C; TArray<FProcMeshTangent> Tg;
		for (int32 r = 0; r <= RingsPerSection; ++r)
		{
			const float T = (Sec * RingsPerSection + r) / float(Sections * RingsPerSection);
			const FVector P = PathPoint(T);
			const FVector Fwd = PathTangent(T);
			const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
			const FVector Up = FVector::CrossProduct(Fwd, Right).GetSafeNormal();
			const float Rad = TunnelRadius(T);
			for (int32 s = 0; s <= Sides; ++s)
			{
				const float A = 2.f * PI * s / Sides;
				const FVector Dir = Right * FMath::Cos(A) + Up * FMath::Sin(A);
				// rough rock: noise on the radius
				const float Noise = FMath::PerlinNoise2D(FVector2D(T * 180.f, s * 0.7f)) * 0.22f + FMath::PerlinNoise2D(FVector2D(T * 600.f, s * 2.1f)) * 0.08f;
				const float Floor = FMath::Sin(A) < -0.6f ? 0.85f : 1.f; // flatter floor
				V.Add(P + Dir * Rad * (1.f + Noise) * Floor);
				N.Add(-Dir);
				UV.Add(FVector2D(s / float(Sides) * 4.f, T * 120.f));
				C.Add(FLinearColor::White);
				Tg.Add(FProcMeshTangent(Fwd, false));
			}
		}
		const int32 Row = Sides + 1;
		for (int32 r = 0; r < RingsPerSection; ++r)
			for (int32 s = 0; s < Sides; ++s)
			{
				const int32 a = r * Row + s, b = a + 1, c = a + Row, d = c + 1;
				Tr.Append({ a, b, c, b, d, c }); // inward facing
			}
		PM->CreateMeshSection_LinearColor(0, V, Tr, N, UV, C, Tg, false);
		if (Rock) PM->SetMaterial(0, Rock);
		PM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		PM->SetCastShadow(false);
	}
}

void AAralezWorld::BuildCrystals()
{
	FRandomStream R(99);
	for (int32 Z = 0; Z < 3; ++Z)
	{
		UInstancedStaticMeshComponent* Ism = NewObject<UInstancedStaticMeshComponent>(this);
		Ism->SetStaticMesh(TwAssets::Cone());
		Ism->SetupAttachment(RootComponent);
		Ism->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Ism->SetCastShadow(false);
		Ism->RegisterComponent();
		Ism->SetWorldTransform(FTransform::Identity);
		if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
		{
			M->SetVectorParameterValue(TEXT("Color"), ZoneGlow[Z]);
			M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
			M->SetScalarParameterValue(TEXT("Intensity"), 6.f);
			Ism->SetMaterial(0, M);
		}
		CrystalSets.Add(Ism);
	}
	// crystals grow from the walls, pointing inward
	for (int32 i = 0; i < 900; ++i)
	{
		const float T = R.FRand();
		const int32 Z = ZoneAt(T);
		const FVector P = PathPoint(T);
		const FVector Fwd = PathTangent(T);
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
		const FVector Up = FVector::CrossProduct(Fwd, Right).GetSafeNormal();
		const float A = R.FRandRange(0.f, 2.f * PI);
		const FVector Dir = Right * FMath::Cos(A) + Up * FMath::Sin(A);
		const FVector Base = P + Dir * TunnelRadius(T) * 0.95f;
		const FRotator Rot = FRotationMatrix::MakeFromZ((-Dir + FMath::VRand() * 0.35f).GetSafeNormal()).Rotator();
		const float S = R.FRandRange(0.6f, 2.4f);
		CrystalSets[Z]->AddInstance(FTransform(Rot, Base, FVector(0.35f * S, 0.35f * S, 1.6f * S)), true);
	}
	// a few real lights per zone so the walls catch colour
	for (int32 i = 0; i < 14; ++i)
	{
		const float T = (i + 0.5f) / 14.f;
		UPointLightComponent* L = NewObject<UPointLightComponent>(this);
		L->SetupAttachment(RootComponent);
		L->RegisterComponent();
		L->SetWorldLocation(PathPoint(T));
		L->SetIntensityUnits(ELightUnits::Unitless);
		L->SetIntensity(60000.f);
		L->SetAttenuationRadius(TunnelRadius(T) * 2.6f);
		L->SetLightColor(ZoneGlow[ZoneAt(T)]);
		L->SetCastShadows(false);
	}
}

void AAralezWorld::BuildGate()
{
	GateCore = NewObject<UStaticMeshComponent>(this);
	GateCore->SetStaticMesh(TwAssets::Sphere());
	GateCore->SetupAttachment(RootComponent);
	GateCore->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GateCore->RegisterComponent();
	GateCore->SetWorldLocation(PathPoint(1.f));
	GateCore->SetWorldScale3D(FVector(9.f));
	if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
	{
		M->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.85f, 0.5f));
		M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		M->SetScalarParameterValue(TEXT("Intensity"), 12.f);
		GateCore->SetMaterial(0, M);
	}
	GateLight = NewObject<UPointLightComponent>(this);
	GateLight->SetupAttachment(GateCore);
	GateLight->RegisterComponent();
	GateLight->SetIntensityUnits(ELightUnits::Unitless);
	GateLight->SetIntensity(300000.f);
	GateLight->SetAttenuationRadius(9000.f);
	GateLight->SetLightColor(FLinearColor(1.f, 0.8f, 0.5f));
	GateLight->SetCastShadows(false);
}

void AAralezWorld::Tick(float Dt)
{
	Super::Tick(Dt);
	// fog colour follows the player's depth
	APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0);
	if (!Cam || !Fog) return;
	const float T = NearestT(Cam->GetCameraLocation(), FMath::Clamp((2000.f - Cam->GetCameraLocation().Z) / 58000.f, 0.f, 1.f));
	const float Zf = FMath::Clamp(T / 0.36f, 0.f, 1.f);
	FLinearColor Col = ZoneFog[0];
	if (T >= 0.36f && T < 0.7f) Col = FMath::Lerp(ZoneFog[0], ZoneFog[1], FMath::Clamp((T - 0.33f) / 0.06f, 0.f, 1.f));
	else if (T >= 0.7f) Col = FMath::Lerp(ZoneFog[1], ZoneFog[2], FMath::Clamp((T - 0.67f) / 0.06f, 0.f, 1.f));
	Fog->SetFogInscatteringColor(Col);
	if (GateCore) GateCore->SetWorldScale3D(FVector(9.f + FMath::Sin(GetWorld()->GetTimeSeconds() * 2.f) * 0.6f));
	(void)Zf;
}
