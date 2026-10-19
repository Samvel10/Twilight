#include "VahagnWorld.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/TextureCube.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/StaticMeshActor.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Misc/PackageName.h"
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
#include "DetailDisp.inl"
#include "Components/InstancedStaticMeshComponent.h"

// sea palette under the HDRI sky: deep water is darker than the sky, it only mirrors the lavender at grazing angles
static const FLinearColor SeaDeep(0.006f, 0.02f, 0.032f);
static const FLinearColor SeaHorizon(0.13f, 0.15f, 0.2f);
static const FLinearColor SeaReflect(0.7f, 0.55f, 0.48f);

AVahagnWorld::AVahagnWorld()
{
	Sea = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Sea"));
	Sea->SetupAttachment(RootComponent);
}

bool AVahagnWorld::UseHighlands()
{
	static const bool b = !FParse::Param(FCommandLine::Get(), TEXT("TwSea")) && FPackageName::DoesPackageExist(TEXT("/Game/Test/L_Highlands"));
	return b;
}

void AVahagnWorld::StreamHighlands()
{
	bool bOk = false;
	EnvLevel = ULevelStreamingDynamic::LoadLevelInstance(GetWorld(), TEXT("/Game/Test/L_Highlands"), HighlandsOffset(), FRotator::ZeroRotator, bOk);
	UE_LOG(LogTwilight, Display, TEXT("[TwEnv] stream L_Highlands ok=%d"), bOk ? 1 : 0);
	if (EnvLevel) { EnvLevel->SetShouldBeVisible(true); EnvLevel->bShouldBlockOnLoad = true; }
	GetWorld()->FlushLevelStreaming();
	AdoptStreamedEnv();
}

void AVahagnWorld::AdoptStreamedEnv()
{
	if (bEnvAdopted || !EnvLevel) return;
	ULevel* L = EnvLevel->GetLoadedLevel();
	if (!L) return;
	bEnvAdopted = true;
	// the game's own sun/sky/fog/grading stay in charge; keep only terrain, lake, plants and the HDRI dome
	int32 Removed = 0;
	for (AActor* A : L->Actors)
	{
		if (!A) continue;
		const bool bLight = A->IsA<ADirectionalLight>() || A->IsA<ASkyLight>() || A->IsA<AExponentialHeightFog>() || A->IsA<APostProcessVolume>() || A->IsA<ACameraActor>()
			|| A->FindComponentByClass<USkyAtmosphereComponent>() != nullptr;
		if (bLight) { A->Destroy(); ++Removed; continue; }
		if (AStaticMeshActor* SM = Cast<AStaticMeshActor>(A))
		{
			UStaticMeshComponent* C = SM->GetStaticMeshComponent();
			UMaterialInterface* M = C ? C->GetMaterial(0) : nullptr;
			if (M && M->GetName().Contains(TEXT("HLSky"))) { A->Destroy(); ++Removed; } // our own HDRI dome (storm-tintable) replaces it
		}
	}
	UE_LOG(LogTwilight, Display, TEXT("[TwEnv] adopted %d actors, removed %d lights/fog/cams, sky=%d"), L->Actors.Num(), Removed, SkyMat ? 1 : 0);
	if (SkyLight) SkyLight->RecaptureSky();
}

void AVahagnWorld::BuildLevel()
{
	if (UseHighlands())
	{
		BuildSkyDome();
		StreamHighlands();
		if (Fog) Fog->SetFogCutoffDistance(0.f);
		Sea->SetVisibility(false);
		Sea->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
	else
	{
		BuildSkyDome();
		BuildSea();
		BuildIslands();
	}
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
		M->SetVectorParameterValue(TEXT("SunDir"), FLinearColor(-0.087f, -0.996f, 0.1f)); // glint path toward the HDRI sun (azimuth 265)
		M->SetVectorParameterValue(TEXT("SunColor"), FLinearColor(1.f, 0.55f, 0.28f));
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
				FRotator R = (FVector(-1900000.f, 1500000.f, 120000.f) - From).Rotation();
				float DbgYaw = 0.f;
				if (FParse::Value(FCommandLine::Get(), TEXT("TwViewYaw="), DbgYaw)) R = FRotator(4.f, DbgYaw, 0.f);
				DebugCam = GetWorld()->SpawnActor<ACameraActor>(From, R);
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
		Atmosphere->SetSkyLuminanceFactor(L(B.SkyLuminance, FLinearColor(1.4f, 0.45f, 0.4f)));
		Atmosphere->SetMieScatteringScale(FMath::Lerp(0.006f, 0.018f, E));
	}
	if (Fog)
	{
		Fog->SetFogInscatteringColor(L(B.FogColor, FLinearColor(0.30f, 0.035f, 0.07f)));
		Fog->SetDirectionalInscatteringColor(L(B.FogSunColor, FLinearColor(1.f, 0.18f, 0.06f)));
		Fog->SetFogDensity(FMath::Lerp(B.FogDensity, UseHighlands() ? B.FogDensity * 6.f : 0.018f, E));
	}
	if (SkyLight) { SkyLight->SetIntensity(FMath::Lerp(B.SkyLightIntensity, 0.8f, E)); SkyLight->SetLightColor(L(B.SkyLightColor, FLinearColor(1.f, 0.5f, 0.55f))); }
	if (Post)
	{
		Post->Settings.ColorGainHighlights = FMath::Lerp(B.GainHighlights, FVector4(1.14f, 0.9f, 0.85f, 1.f), E);
	}
	if (SkyMat)
	{
		// the HDRI dome carries the visible sky: it must turn crimson with the storm
		SkyMat->SetVectorParameterValue(TEXT("ZenithTint"), L(FLinearColor(1.f, 1.f, 1.f), FLinearColor(0.7f, 0.32f, 0.3f)));
		SkyMat->SetVectorParameterValue(TEXT("HorizonTint"), L(FLinearColor(1.05f, 0.95f, 0.9f), FLinearColor(1.2f, 0.4f, 0.22f)));
		SkyMat->SetScalarParameterValue(TEXT("Exposure"), FMath::Lerp(SkyExposure, SkyExposure * 0.75f, E));
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
	// carved basalt (same scanned rock as the islands, a little lighter: worked stone)
	UMaterialInterface* StoneBase = TwAssets::Material(TEXT("M_RockPBR"));
	UMaterialInstanceDynamic* Stone = UMaterialInstanceDynamic::Create(StoneBase ? StoneBase : TwAssets::Material(TEXT("M_Rock")), this);
	if (Stone) { Stone->SetVectorParameterValue(TEXT("Tint"), StoneBase ? FLinearColor(2.6f, 2.4f, 2.2f) : FLinearColor(0.48f, 0.44f, 0.4f)); if (StoneBase) Stone->SetScalarParameterValue(TEXT("Tiling"), 300.f); }
	UMaterialInstanceDynamic* Glyph = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Glyph) { Glyph->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.3f, 0.06f)); Glyph->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Glyph->SetScalarParameterValue(TEXT("Intensity"), 1.6f); }

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

FTwSkyPreset AVahagnWorld::GetSkyPreset() const
{
	if (UseHighlands())
	{
		// values of the highlands kit (env_params.json): sun 8 deg up at azimuth 255, matching its baked terrain shadow
		FTwSkyPreset H;
		H.SunRot = FRotator(-8.f, -15.f, 0.f);
		H.SunColor = FLinearColor(1.f, 0.56f, 0.32f);
		H.SunIntensity = 11.f;
		H.MoonColor = FLinearColor(0.45f, 0.55f, 0.85f);
		H.MoonIntensity = 0.f;
		H.FogColor = FLinearColor(0.36f, 0.42f, 0.55f);
		H.FogSunColor = FLinearColor(1.f, 0.5f, 0.25f);
		H.FogDensity = 0.00019f;
		H.FogFalloff = 0.0067f;
		H.FogStart = 0.f;
		H.FogMaxOpacity = 1.f;
		H.Exposure = 0.f;
		H.SkyLightIntensity = 0.65f;
		H.SkyLightColor = FLinearColor(1.f, 1.f, 1.f);
		H.LowerHemisphere = FLinearColor(0.03f, 0.035f, 0.04f);
		H.SkyLuminance = FLinearColor(1.f, 1.f, 1.f);
		H.GainShadows = FVector4(1.f, 1.f, 1.f, 1.f);
		H.GainHighlights = FVector4(1.f, 1.f, 1.f, 1.f);
		H.Saturation = FVector4(1.08f, 1.08f, 1.08f, 1.08f);
		H.ShadowDistance = 20000.f;
		H.AerialPerspectiveScale = 1.f;
		H.EmberColor = FLinearColor(1.f, 0.42f, 0.12f);
		H.EmberFloorZ = 60.f;
		return H;
	}
	// natural sunset over open sea: warm low sun, blue-grey water, neutral-cool shadows (no purple stylisation)
	FTwSkyPreset P;
	P.EmberFloorZ = 60.f;
	P.AerialPerspectiveScale = 1.5f;
	P.ShadowDistance = 20000.f;
	P.FogMaxOpacity = 0.75f;
	P.FogFalloff = 0.22f;
	P.FogDensity = 0.014f;
	P.SunRot = FRotator(-6.f, 265.f, 0.f); // matches the sun in the HDRI dome (azimuth ~265)
	P.SunColor = FLinearColor(1.f, 0.56f, 0.3f);
	P.SunIntensity = 8.f;
	P.MoonColor = FLinearColor(0.45f, 0.55f, 0.85f);
	P.MoonIntensity = 0.5f;
	P.FogColor = FLinearColor(0.28f, 0.26f, 0.3f);
	P.FogSunColor = FLinearColor(1.f, 0.5f, 0.22f);
	P.SkyLightIntensity = 1.f;
	P.SkyLightColor = FLinearColor(1.f, 0.9f, 0.85f);
	P.LowerHemisphere = FLinearColor(0.02f, 0.03f, 0.045f);
	P.SkyLuminance = FLinearColor(1.f, 1.f, 1.f);
	P.GainShadows = FVector4(0.97f, 0.99f, 1.05f, 1.f);
	P.GainHighlights = FVector4(1.04f, 1.f, 0.96f, 1.f);
	P.Saturation = FVector4(1.f, 1.f, 1.f, 1.02f);
	P.EmberColor = FLinearColor(1.f, 0.42f, 0.12f);
	return P;
}

void AVahagnWorld::BuildSkyDome()
{
	UMaterialInterface* M = TwAssets::Material(TEXT("M_SkyHDRI"));
	if (!M) return;
	SkyMat = UMaterialInstanceDynamic::Create(M, this);
	float Yaw = 0.f;
	if (UseHighlands())
	{
		// kloppenheim_06: its sun (u 218 deg, 8 deg up) must sit where the directional light comes from
		if (UTextureCube* Cube = LoadObject<UTextureCube>(nullptr, TEXT("/Game/Env/HDRI/kloppenheim_06_puresky_4k.kloppenheim_06_puresky_4k")))
			if (SkyMat) SkyMat->SetTextureParameterValue(TEXT("SkyCube"), Cube);
		Yaw = 0.352f;
	}
	FParse::Value(FCommandLine::Get(), TEXT("TwSkyYaw="), Yaw);
	if (SkyMat) SkyMat->SetScalarParameterValue(TEXT("Yaw"), Yaw);
	float Exp = UseHighlands() ? 0.8f : 1.f;
	FParse::Value(FCommandLine::Get(), TEXT("TwSkyExp="), Exp);
	SkyExposure = Exp;
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

static float DetailSample(float X, float Y, float Tile)
{
	const float U = FMath::Fmod(FMath::Fmod(X / Tile, 1.f) + 1.f, 1.f) * DetailRes, V = FMath::Fmod(FMath::Fmod(Y / Tile, 1.f) + 1.f, 1.f) * DetailRes;
	const int32 I0 = (int32)U % DetailRes, J0 = (int32)V % DetailRes, I1 = (I0 + 1) % DetailRes, J1 = (J0 + 1) % DetailRes;
	const float FU = U - (int32)U, FV = V - (int32)V;
	auto D = [](int32 i, int32 j) { return DetailDisp[j * DetailRes + i] / 255.f - DetailMean; };
	return FMath::Lerp(FMath::Lerp(D(I0, J0), D(I1, J0), FU), FMath::Lerp(D(I0, J1), D(I1, J1), FU), FV);
}
static float Fbm(float X, float Y, float S, int32 Oct)
{
	float A = 1.f, T = 0.f, F = 1.f;
	for (int32 o = 0; o < Oct; ++o) { T += A * FMath::PerlinNoise2D(FVector2D(X, Y) * (F / S) + FVector2D(o * 17.3f, o * 5.1f)); A *= 0.5f; F *= 2.03f; }
	return T;
}

// CliffH: wave-cut sea cliff height (inner islands 1800, ring islands 3500 cm)
static float IslandZ(int32 Index, float X, float Y, float Radius, float Height, float CliffH = 1800.f)
{
	// --- today's real relief (unchanged)
	const float U = FMath::Clamp((X / Radius + 1.f) * 0.5f, 0.f, 1.f) * (IslandRes - 1);
	const float V = FMath::Clamp((Y / Radius + 1.f) * 0.5f, 0.f, 1.f) * (IslandRes - 1);
	const int32 X0 = FMath::Min((int32)U, IslandRes - 2), Y0 = FMath::Min((int32)V, IslandRes - 2);
	const float FX = U - X0, FY = V - Y0;
	const uint16* D = IslandHeight + (Index % IslandCount) * IslandRes * IslandRes;
	auto H = [D](int32 x, int32 y) { return (float)D[y * IslandRes + x] / 65535.f * 1.3f - 0.3f; };
	const float Base = FMath::Lerp(FMath::Lerp(H(X0, Y0), H(X0 + 1, Y0), FX), FMath::Lerp(H(X0, Y0 + 1), H(X0 + 1, Y0 + 1), FX), FY);
	const float Detail = FMath::PerlinNoise2D(FVector2D(X, Y) / (Radius * 0.12f)) * 0.05f + FMath::PerlinNoise2D(FVector2D(X, Y) / (Radius * 0.035f)) * 0.018f;
	float Z = (Base + (Base > 0.f ? Detail : 0.f)) * Height;
	// --- v2: irregular coastline (bays/headlands)
	Z += Fbm(X, Y, Radius * 0.35f, 3) * Height * 0.12f * FMath::Clamp((Z + Height * 0.2f) / (Height * 0.4f), 0.f, 1.f);
	if (Z <= 0.f) return Z;
	// --- v2: vertical wave-cut cliff at the coastline (everything above 2.5 m of old relief is lifted by ~CliffH)
	const float Up = FMath::SmoothStep(0.f, 250.f, Z);
	const float CliffVar = CliffH * (0.75f + 0.5f * (Fbm(X, Y, 2500.f, 2) * 0.5f + 0.5f));
	Z = Z * (1.f - CliffH / Height * 0.8f) + CliffVar * Up;
	// --- v2: ridged gullies + photogrammetry displacement (aerial_rocks_02, 50 m and 17 m tiles)
	const float Ridge = 1.f - FMath::Abs(Fbm(X, Y, 1800.f, 3));
	Z -= 600.f * Ridge * Ridge * Ridge * Up;
	Z += Up * (DetailSample(X, Y, 5000.f) * 450.f + DetailSample(X + 1700.f, Y - 900.f, 1700.f) * 160.f);
	return Z;
}

// sea stack: a ribbed, layered basalt pillar (~32 m footprint, ~50 m tall), cm
static float StackZ(float X, float Y, float Seed)
{
	const float A = FMath::Atan2(Y, X);
	const float R = FMath::Sqrt(X * X + Y * Y);
	const float R0 = 1600.f * (1.f + 0.22f * FMath::Sin(3.f * A + Seed) + 0.12f * FMath::Sin(5.f * A + Seed * 2.f) + 0.07f * FMath::Sin(9.f * A) + 0.05f * FMath::Sin(14.f * A) + 0.08f * Fbm(X + Seed * 900.f, Y, 700.f, 2));
	if (R >= R0) return -2000.f;
	float Z = 5200.f * FMath::Pow(1.f - R / R0, 0.1f) * (0.78f + 0.22f * (Fbm(X, Y + Seed * 500.f, 600.f, 2) * 0.5f + 0.5f));
	Z -= 140.f * FMath::Frac(Z / 650.f); // strata
	Z += DetailSample(X, Y, 2500.f) * 300.f;
	return Z;
}

void AVahagnWorld::BuildIslands()
{
	// volcanic rock (Poly Haven dark_rock, CC0), triplanar; falls back to the procedural rock
	UMaterialInterface* RockBase = TwAssets::Material(TEXT("M_RockPBR"));
	const bool bPBR = RockBase != nullptr;
	// islands: basalt cliffs (triplanar dark_rock) + aerial photogrammetry on the flats, wet band, algae line
	UMaterialInterface* IslandMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Twilight/Materials/MI_IslandTerrain.MI_IslandTerrain"));
	UMaterialInstanceDynamic* Rock = UMaterialInstanceDynamic::Create(bPBR ? RockBase : TwAssets::Material(TEXT("M_Rock")), this);
	if (Rock && !bPBR) Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.42f, 0.3f, 0.34f));
	if (Rock && bPBR) { Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(1.9f, 1.8f, 1.75f)); Rock->SetScalarParameterValue(TEXT("Tiling"), 1500.f); } // dark_rock albedo is near black
	UMaterialInterface* IslandSurf = IslandMat ? IslandMat : (UMaterialInterface*)Rock;
	// scanned boulders (Poly Haven boulder_01, CC0, 4 LODs) around every coastline
	UStaticMesh* BoulderMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Twilight/Env/Scan/boulder_01/boulder_01_2k/StaticMeshes/boulder_01_2k.boulder_01_2k"));
	UMaterialInterface* BoulderMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Twilight/Materials/MI_Scan_boulder_01.MI_Scan_boulder_01"));
	UInstancedStaticMeshComponent* Boulders = nullptr;
	if (BoulderMesh)
	{
		Boulders = NewObject<UInstancedStaticMeshComponent>(this);
		Boulders->SetStaticMesh(BoulderMesh);
		if (BoulderMat) Boulders->SetMaterial(0, BoulderMat);
		Boulders->SetupAttachment(RootComponent);
		Boulders->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Boulders->SetCastShadow(true);
		Boulders->RegisterComponent();
		Boulders->SetWorldTransform(FTransform::Identity);
	}
	FRandomStream Br(808);
	// boulders at the foot of a coast: walk rays out from the centre to the waterline
	auto ScatterBoulders = [&](const FVector& C, TFunctionRef<float(float, float)> Hf, float MaxR, int32 Count, float SMin, float SMax)
	{
		if (!Boulders) return;
		for (int32 k = 0; k < Count; ++k)
		{
			const float Ang = Br.FRandRange(0.f, 2.f * PI);
			const FVector2D D(FMath::Cos(Ang), FMath::Sin(Ang));
			float Coast = -1.f;
			for (float R = 0.f; R < MaxR; R += 150.f) if (Hf(D.X * R, D.Y * R) <= 0.f) { Coast = R; break; }
			if (Coast < 0.f) continue;
			const float Rr = Coast + Br.FRandRange(100.f, 900.f);
			const float S = Br.FRandRange(SMin, SMax);
			const FRotator Rot(Br.FRandRange(-25.f, 25.f), Br.FRandRange(0.f, 360.f), Br.FRandRange(-25.f, 25.f));
			Boulders->AddInstance(FTransform(Rot, C + FVector(D.X * Rr, D.Y * Rr, -S * Br.FRandRange(25.f, 50.f)), FVector(S)), true);
		}
	};
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
		const FVector C(FMath::Cos(A) * Dist, FMath::Sin(A) * Dist, 0.f);
		auto Hf = [=](float X, float Y) { return IslandZ(Idx, X, Y, Rad, Hgt, 3500.f); };
		BuildTerrain(C, Rad, Rad, 128, 128, Hf, IslandSurf, true);
		ScatterBoulders(C, Hf, Rad, 6, 6.f, 12.f);
	}
	// three inner islands with vishapakar stones (Aragats-like plateaus)
	const FVector Inner[3] = { FVector(16000, -9000, 0), FVector(-21000, -14000, 0), FVector(-6000, 25000, 0) };
	for (int32 i = 0; i < 3; ++i)
	{
		const float Rad = 7000.f + i * 900.f;
		const float Hgt = 4200.f + i * 900.f;
		const int32 Idx = i == 0 ? 0 : (i == 1 ? 1 : 3); // Little Ararat, the Masis summit ridge, a crater
		auto Hf = [=](float X, float Y) { return IslandZ(Idx, X, Y, Rad, Hgt, 1800.f); };
		BuildTerrain(Inner[i], Rad, Rad, 160, 160, Hf, IslandSurf, true);
		ScatterBoulders(Inner[i], Hf, Rad, 10, 5.f, 12.f);
		// a sea stack off each inner island, with boulders leaning on it
		const float SA = 0.8f + i * 2.1f;
		const FVector SC = Inner[i] + FVector(FMath::Cos(SA), FMath::Sin(SA), 0.f) * (Rad + 2600.f);
		const float Seed = 1.7f + i * 3.3f;
		BuildTerrain(SC, 3200.f, 3200.f, 112, 112, [=](float X, float Y) { return StackZ(X, Y, Seed); }, IslandSurf, true);
		ScatterBoulders(SC, [=](float X, float Y) { return StackZ(X, Y, Seed); }, 3200.f, 6, 8.f, 16.f);
		const float Top = IslandZ(Idx, 0.f, 0.f, Rad, Hgt, 1800.f);
		BuildVishapakar(Inner[i] + FVector(0, 0, Top - 150.f), 30.f + i * 70.f, 1.2f);
	}
	// Masis on the horizon from real elevation data
	UMaterialInstanceDynamic* MasisMat = UMaterialInstanceDynamic::Create(bPBR ? RockBase : TwAssets::Material(TEXT("M_Rock")), this);
	if (MasisMat && bPBR)
	{
		// 25 km of air: mostly sky-coloured haze, the snowfields catching a little warm light
		MasisMat->SetScalarParameterValue(TEXT("Tiling"), 60000.f);
		MasisMat->SetVectorParameterValue(TEXT("Tint"), FLinearColor(1.3f, 1.25f, 1.25f));
		MasisMat->SetScalarParameterValue(TEXT("TopAmount"), 0.6f);
		MasisMat->SetVectorParameterValue(TEXT("TopTint"), FLinearColor(2.f, 1.8f, 2.f));
		MasisMat->SetScalarParameterValue(TEXT("HazeAmount"), 0.5f);
		MasisMat->SetVectorParameterValue(TEXT("HazeColor"), FLinearColor(0.32f, 0.3f, 0.34f));
	}
	if (!FParse::Param(FCommandLine::Get(), TEXT("TwNoMasis"))) BuildMasis(MasisMat ? MasisMat : (Snow ? Snow : Rock));
	(void)Snow;
}

