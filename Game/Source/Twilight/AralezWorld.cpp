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
	const FLinearColor ZoneFog[3] = { FLinearColor(0.02f, 0.05f, 0.11f), FLinearColor(0.01f, 0.09f, 0.08f), FLinearColor(0.09f, 0.012f, 0.02f) };
	const FLinearColor ZoneGlow[3] = { FLinearColor(0.35f, 0.75f, 1.f), FLinearColor(0.3f, 1.f, 0.7f), FLinearColor(1.f, 0.3f, 0.12f) };
}

AAralezWorld::AAralezWorld() {}

FVector AAralezWorld::PathPoint(float T)
{
	T = FMath::Clamp(T, 0.f, 1.f);
	const float Turns = 3.4f;
	const float A = T * Turns * 2.f * PI;
	const float R = 6500.f + 1500.f * FMath::Sin(T * 7.f);
	const float Z = 2000.f - T * 80000.f + 900.f * FMath::Sin(T * 31.f);
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

float AAralezWorld::WallRadius(float T, float A)
{
	const float S = A / (2.f * PI) * 26.f;
	const float Noise = FMath::PerlinNoise2D(FVector2D(T * 180.f, S * 0.7f)) * 0.22f + FMath::PerlinNoise2D(FVector2D(T * 600.f, S * 2.1f)) * 0.08f;
	const float Floor = FMath::Sin(A) < -0.6f ? 0.85f : 1.f;
	return TunnelRadius(T) * (1.f + Noise) * Floor;
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
	P.Exposure = 2.2f;
	P.SkyLightIntensity = 0.45f;
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
	BuildRiver();
}

void AAralezWorld::BuildRiver()
{
	// a dark teal water strip along the floor of the underground-river zone (edges run into the rock walls)
	UProceduralMeshComponent* PM = NewObject<UProceduralMeshComponent>(this);
	PM->SetupAttachment(RootComponent);
	PM->RegisterComponent();
	PM->SetWorldTransform(FTransform::Identity);
	TArray<FVector> V; TArray<int32> Tr; TArray<FVector> N; TArray<FVector2D> UV; TArray<FLinearColor> C; TArray<FProcMeshTangent> Tg;
	const int32 Rings = 160, Across = 8;
	for (int32 r = 0; r <= Rings; ++r)
	{
		const float T = FMath::Lerp(RiverT0, RiverT1, r / float(Rings));
		const FVector P = PathPoint(T);
		const FVector Fwd = PathTangent(T);
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
		const FVector Up = FVector::CrossProduct(Fwd, Right).GetSafeNormal();
		const float Rad = TunnelRadius(T);
		for (int32 k = 0; k <= Across; ++k)
		{
			V.Add(P - Up * (RiverDepth * Rad) + Right * ((k / float(Across) - 0.5f) * 1.9f * Rad));
			N.Add(Up);
			UV.Add(FVector2D(k / float(Across), T * 60.f));
			C.Add(FLinearColor::White);
			Tg.Add(FProcMeshTangent(Fwd, false));
		}
	}
	const int32 Row = Across + 1;
	for (int32 r = 0; r < Rings; ++r)
		for (int32 k = 0; k < Across; ++k)
		{
			const int32 a = r * Row + k, b = a + 1, c = a + Row, d = c + 1;
			Tr.Append({ a, b, c, b, d, c }); // same winding as the tunnel floor: faces up, seen from inside
		}
	PM->CreateMeshSection_LinearColor(0, V, Tr, N, UV, C, Tg, false);
	PM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PM->SetCastShadow(false);
	if (UMaterialInstanceDynamic* W = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Water_Purple")), this))
	{
		W->SetVectorParameterValue(TEXT("DeepColor"), FLinearColor(0.0f, 0.012f, 0.018f));
		W->SetVectorParameterValue(TEXT("HorizonColor"), FLinearColor(0.01f, 0.11f, 0.13f));
		W->SetVectorParameterValue(TEXT("CrestColor"), FLinearColor(0.08f, 0.35f, 0.32f));
		W->SetVectorParameterValue(TEXT("SkyReflectColor"), FLinearColor(0.04f, 0.26f, 0.28f));
		W->SetScalarParameterValue(TEXT("SunGlintIntensity"), 0.f);
		W->SetScalarParameterValue(TEXT("WaveHeight"), 0.f);
		W->SetScalarParameterValue(TEXT("NormalTile"), 900.f);
		W->SetScalarParameterValue(TEXT("RippleSpeed"), 0.5f); // flowing
		PM->SetMaterial(0, W);
	}
}

void AAralezWorld::BuildTunnel()
{
	UMaterialInstanceDynamic* Rock = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Rock) { Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.22f, 0.24f, 0.3f)); Rock->SetScalarParameterValue(TEXT("TopAmount"), 0.f); }

	// split into a few sections so culling works
	const int32 Sections = 8;
	const int32 RingsPerSection = 52;
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
			M->SetScalarParameterValue(TEXT("Intensity"), 2.5f);
			Ism->SetMaterial(0, M);
		}
		CrystalSets.Add(Ism);
	}
	// crystals grow from the walls, pointing inward
	for (int32 i = 0; i < 420; ++i)
	{
		const float T = R.FRand();
		const int32 Z = ZoneAt(T);
		const FVector P = PathPoint(T);
		const FVector Fwd = PathTangent(T);
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
		const FVector Up = FVector::CrossProduct(Fwd, Right).GetSafeNormal();
		const float A = R.FRandRange(0.f, 2.f * PI);
		const FVector Dir = Right * FMath::Cos(A) + Up * FMath::Sin(A);
		// clusters embedded in the rock
		const FVector Base = P + Dir * WallRadius(T, A) * 1.04f;
		const float S = R.FRandRange(0.6f, 2.2f);
		for (int32 k = 0; k < 3; ++k)
		{
			const FRotator Rot = FRotationMatrix::MakeFromZ((-Dir + FMath::VRand() * 0.2f).GetSafeNormal()).Rotator();
			const float Ks = k == 0 ? 1.f : (k == 1 ? 0.6f : 0.4f);
			CrystalSets[Z]->AddInstance(FTransform(Rot, Base + FMath::VRand() * 60.f * S, FVector(0.35f, 0.35f, 1.6f) * S * Ks), true);
		}
	}
	// a few real lights per zone so the walls catch colour
	for (int32 i = 0; i < 28; ++i)
	{
		const float T = (i + 0.5f) / 28.f;
		UPointLightComponent* L = NewObject<UPointLightComponent>(this);
		L->SetupAttachment(RootComponent);
		L->RegisterComponent();
		L->SetWorldLocation(PathPoint(T));
		L->SetIntensityUnits(ELightUnits::Unitless);
		L->SetIntensity(90000.f);
		L->SetAttenuationRadius(TunnelRadius(T) * 1.8f);
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
	GateCore->SetWorldScale3D(FVector(4.f));
	// a slowly turning ring of golden crystals around the soul of Ara
	GateRing = NewObject<USceneComponent>(this);
	GateRing->SetupAttachment(RootComponent);
	GateRing->RegisterComponent();
	GateRing->SetWorldLocationAndRotation(PathPoint(1.f), PathTangent(1.f).Rotation());
	UMaterialInstanceDynamic* GoldM = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (GoldM) { GoldM->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.8f, 0.4f)); GoldM->SetScalarParameterValue(TEXT("GlowMode"), 1.f); GoldM->SetScalarParameterValue(TEXT("Intensity"), 4.f); }
	for (int32 k = 0; k < 20; ++k)
	{
		const float A = 2.f * PI * k / 20.f;
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(TwAssets::Cone());
		C->SetupAttachment(GateRing);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->RegisterComponent();
		const FVector Rad(0.f, FMath::Cos(A), FMath::Sin(A));
		C->SetRelativeLocation(Rad * 1600.f);
		C->SetRelativeRotation(FRotationMatrix::MakeFromZ(-Rad).Rotator());
		C->SetRelativeScale3D(FVector(0.5f, 0.5f, 3.f));
		if (GoldM) C->SetMaterial(0, GoldM);
	}
	if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
	{
		// saturated golden shell (intensity 12 tonemapped to a flat grey-white disc)
		M->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.62f, 0.22f));
		M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		M->SetScalarParameterValue(TEXT("Intensity"), 5.5f);
		M->SetScalarParameterValue(TEXT("Falloff"), 2.5f);
		GateCore->SetMaterial(0, M);
	}
	// white-hot heart of Ara's soul inside the shell
	UStaticMeshComponent* Heart = NewObject<UStaticMeshComponent>(this);
	Heart->SetStaticMesh(TwAssets::Sphere());
	Heart->SetupAttachment(GateCore);
	Heart->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Heart->SetCastShadow(false);
	Heart->SetRelativeScale3D(FVector(0.45f));
	Heart->RegisterComponent();
	if (UMaterialInstanceDynamic* HM = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
	{
		HM->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.88f, 0.65f));
		HM->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		HM->SetScalarParameterValue(TEXT("Intensity"), 9.f);
		Heart->SetMaterial(0, HM);
	}
	GateCore->SetCastShadow(false);
	// the tunnel ends at the gate: close it with a rock wall so the void never shows behind Ara
	{
		UStaticMeshComponent* Cap = NewObject<UStaticMeshComponent>(this);
		Cap->SetStaticMesh(TwAssets::Sphere());
		Cap->SetupAttachment(RootComponent);
		Cap->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Cap->SetCastShadow(false);
		Cap->RegisterComponent();
		const FVector Tan = PathTangent(1.f);
		const float R = TunnelRadius(1.f) * 1.6f;
		Cap->SetWorldLocationAndRotation(PathPoint(1.f) + Tan * 2600.f, FRotationMatrix::MakeFromX(Tan).Rotator());
		Cap->SetWorldScale3D(FVector(30.f, R / 50.f, R / 50.f));
		if (UMaterialInstanceDynamic* CapM = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this))
		{
			CapM->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.3f, 0.22f, 0.16f));
			CapM->SetScalarParameterValue(TEXT("TopAmount"), 0.f);
			Cap->SetMaterial(0, CapM);
		}
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
	const float T = NearestT(Cam->GetCameraLocation(), FMath::Clamp((2000.f - Cam->GetCameraLocation().Z) / 80000.f, 0.f, 1.f));
	const float Zf = FMath::Clamp(T / 0.36f, 0.f, 1.f);
	FLinearColor Col = ZoneFog[0];
	if (T >= 0.36f && T < 0.7f) Col = FMath::Lerp(ZoneFog[0], ZoneFog[1], FMath::Clamp((T - 0.33f) / 0.06f, 0.f, 1.f));
	else if (T >= 0.7f) Col = FMath::Lerp(ZoneFog[1], ZoneFog[2], FMath::Clamp((T - 0.67f) / 0.06f, 0.f, 1.f));
	// the last stretch before Ara's gate: the red abyss gives way to a thin golden haze so the gate reads
	const float GateK = FMath::SmoothStep(0.9f, 0.985f, T);
	Col = FMath::Lerp(Col, FLinearColor(0.07f, 0.045f, 0.015f), GateK);
	Fog->SetFogInscatteringColor(Col);
	Fog->SetFogDensity(FMath::Lerp(FMath::Lerp(0.035f, 0.025f, FMath::Clamp(T / 0.7f, 0.f, 1.f)), 0.004f, GateK));
	if (GateRing) GateRing->AddLocalRotation(FRotator(0.f, 0.f, Dt * 20.f));
	if (GateCore) GateCore->SetWorldScale3D(FVector(4.f + FMath::Sin(GetWorld()->GetTimeSeconds() * 2.f) * 0.4f));
	(void)Zf;
}
