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

AVahagnWorld::AVahagnWorld()
{
	Sea = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Sea"));
	Sea->SetupAttachment(RootComponent);
}

void AVahagnWorld::BuildLevel()
{
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
		M->SetVectorParameterValue(TEXT("DeepColor"), FLinearColor(0.10f, 0.02f, 0.14f));
		// larger, softer ripples: the hero flies high, small tiles read as a repeating dot pattern
		M->SetScalarParameterValue(TEXT("NormalTile"), 2800.f);
		M->SetScalarParameterValue(TEXT("NormalStrength"), 0.45f);
		Sea->SetMaterial(0, M);
		SeaMat = M;
	}
}

// ---------------------------------------------------------------- storm (boss phase)
void AVahagnWorld::Tick(float Dt)
{
	Super::Tick(Dt);
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
		SeaMat->SetVectorParameterValue(TEXT("DeepColor"), L(FLinearColor(0.10f, 0.02f, 0.14f), FLinearColor(0.09f, 0.01f, 0.03f)));
		SeaMat->SetVectorParameterValue(TEXT("HorizonColor"), L(FLinearColor(0.42f, 0.16f, 0.55f), FLinearColor(0.45f, 0.05f, 0.10f)));
		SeaMat->SetVectorParameterValue(TEXT("SkyReflectColor"), L(FLinearColor(0.9f, 0.38f, 0.55f), FLinearColor(0.9f, 0.12f, 0.18f)));
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

void AVahagnWorld::BuildIslands()
{
	UMaterialInstanceDynamic* Rock = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Rock) Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.42f, 0.3f, 0.34f));
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
		BuildHeightfield(FVector(FMath::Cos(A) * Dist, FMath::Sin(A) * Dist, 0.f), Rad, Hgt, 10 + i, 56, false, Rock, true);
	}
	// three inner islands with vishapakar stones (Aragats-like plateaus)
	const FVector Inner[3] = { FVector(16000, -9000, 0), FVector(-21000, -14000, 0), FVector(-6000, 25000, 0) };
	for (int32 i = 0; i < 3; ++i)
	{
		const float Rad = 7000.f + i * 900.f;
		const float Hgt = 2600.f + i * 700.f;
		BuildHeightfield(Inner[i], Rad, Hgt, 50 + i, 60, false, Rock, true);
		const float Top = HillHeight(0.f, 0.f, Rad, Hgt, 50 + i, false);
		BuildVishapakar(Inner[i] + FVector(0, 0, Top - 150.f), 30.f + i * 70.f, 1.2f);
	}
	// Masis on the horizon, catching the last sun (no collision, far away)
	BuildHeightfield(FVector(-150000.f, -60000.f, 0.f), 60000.f, 52000.f, 7, 96, true, Snow ? Snow : Rock, false);
}

