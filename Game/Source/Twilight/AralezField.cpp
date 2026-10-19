#include "AralezField.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "AralezSpirit.h"

#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Animation/AnimSequence.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/TextureCube.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"

// real relief of Mount Ararat (Masis) on the horizon of the Ararat plain
#include "MasisHeight.inl"
#include "DetailDisp.inl"

namespace
{
	const TCHAR* WarriorMesh = TEXT("/Game/Twilight/Hero/Mesh/spartan_vahagn/SkeletalMeshes/spartan_vahagn.spartan_vahagn");
	UAnimSequence* HeroAnim(const TCHAR* Name)
	{
		return TwAssets::Anim(*FString::Printf(TEXT("/Game/Twilight/Hero/Anims/%s.%s"), Name, Name));
	}
	float DetailAt(float X, float Y, float Tile)
	{
		const float U = FMath::Fmod(FMath::Fmod(X / Tile, 1.f) + 1.f, 1.f) * DetailRes, V = FMath::Fmod(FMath::Fmod(Y / Tile, 1.f) + 1.f, 1.f) * DetailRes;
		const int32 I0 = (int32)U % DetailRes, J0 = (int32)V % DetailRes, I1 = (I0 + 1) % DetailRes, J1 = (J0 + 1) % DetailRes;
		const float FU = U - (int32)U, FV = V - (int32)V;
		auto D = [](int32 i, int32 j) { return DetailDisp[j * DetailRes + i] / 255.f - DetailMean; };
		return FMath::Lerp(FMath::Lerp(D(I0, J0), D(I1, J0), FU), FMath::Lerp(D(I0, J1), D(I1, J1), FU), FV);
	}
}

// ================================================================== field
AAralezField::AAralezField() { PrimaryActorTick.bCanEverTick = true; }

static float PlainZ(float X, float Y, bool bDetail)
{
	// the Ararat plain: broad gentle swells, low rolling hills far out
	const FVector2D P(X, Y);
	float Z = FMath::PerlinNoise2D(P / 90000.f) * 900.f + FMath::PerlinNoise2D(P / 26000.f + FVector2D(3.1f, 7.7f)) * 320.f;
	// micro relief only where the grid is fine enough to carry it (coarse samples of it read as spikes)
	if (bDetail) Z += DetailAt(X, Y, 5000.f) * 90.f + DetailAt(X + 1300.f, Y, 1700.f) * 35.f;
	const float R = P.Size();
	const float Hill = 0.55f + 0.45f * FMath::PerlinNoise2D(P / 160000.f + FVector2D(9.3f, 1.1f));
	Z += FMath::Square(FMath::Max(0.f, R - 240000.f) / 180000.f) * 4000.f * Hill;
	return Z;
}

float AAralezField::GroundZ(float X, float Y) { return PlainZ(X, Y, true); }

FTwSkyPreset AAralezField::GetSkyPreset() const
{
	// dusk after the battle: the sun is going down behind smoke, warm light, blue-grey shadows
	FTwSkyPreset P;
	P.SunRot = FRotator(-9.f, 265.f, 0.f); // matches the sun of the qwantani dusk HDRI
	P.SunColor = FLinearColor(1.f, 0.5f, 0.27f);
	P.SunIntensity = 7.f;
	P.MoonColor = FLinearColor(0.45f, 0.55f, 0.85f);
	P.MoonIntensity = 0.4f;
	P.FogColor = FLinearColor(0.3f, 0.26f, 0.27f);
	P.FogSunColor = FLinearColor(1.f, 0.46f, 0.2f);
	P.FogDensity = 0.02f;
	P.FogFalloff = 0.12f;
	P.FogStart = 2000.f;
	P.FogMaxOpacity = 0.8f;
	P.Exposure = 0.2f;
	P.SkyLightIntensity = 1.4f;
	P.SkyLightColor = FLinearColor(1.f, 0.9f, 0.85f);
	P.LowerHemisphere = FLinearColor(0.03f, 0.03f, 0.035f);
	P.SkyLuminance = FLinearColor(1.f, 1.f, 1.f);
	P.GainShadows = FVector4(0.97f, 0.99f, 1.05f, 1.f);
	P.GainHighlights = FVector4(1.04f, 1.f, 0.96f, 1.f);
	P.Saturation = FVector4(1.f, 1.f, 1.f, 1.f);
	P.EmberColor = FLinearColor(1.f, 0.45f, 0.15f);
	P.ShadowDistance = 15000.f;
	P.AerialPerspectiveScale = 1.5f;
	return P;
}

void AAralezField::BuildLevel()
{
	BuildSkyDome();
	BuildGround();
	BuildMasis();
	BuildDressing();
}

void AAralezField::BuildSkyDome()
{
	UMaterialInterface* M = TwAssets::Material(TEXT("M_SkyHDRI"));
	if (!M) return;
	UMaterialInstanceDynamic* Sky = UMaterialInstanceDynamic::Create(M, this);
	if (!Sky) return;
	if (UTextureCube* Dusk = LoadObject<UTextureCube>(nullptr, TEXT("/Game/Twilight/Env/HDRI/qwantani_dusk_2_puresky_2k.qwantani_dusk_2_puresky_2k")))
		Sky->SetTextureParameterValue(TEXT("SkyCube"), Dusk);
	Sky->SetVectorParameterValue(TEXT("ZenithTint"), FLinearColor(1.f, 1.f, 1.f));
	Sky->SetVectorParameterValue(TEXT("HorizonTint"), FLinearColor(1.1f, 0.9f, 0.82f));
	UStaticMeshComponent* Dome = NewObject<UStaticMeshComponent>(this);
	Dome->SetStaticMesh(TwAssets::Sphere());
	Dome->SetupAttachment(RootComponent);
	Dome->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dome->SetCastShadow(false);
	Dome->SetWorldScale3D(FVector(400000.f));
	Dome->SetMaterial(0, Sky);
	Dome->RegisterComponent();
}

void AAralezField::BuildGround()
{
	UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Twilight/Materials/MI_IslandTerrain.MI_IslandTerrain"));
	UMaterialInstanceDynamic* G = UMaterialInstanceDynamic::Create(Base ? Base : TwAssets::Material(TEXT("M_RockPBR")), this);
	if (G)
	{
		// trampled dusty plain: no sea line here
		G->SetScalarParameterValue(TEXT("SeaZ"), -1000000.f);
		G->SetScalarParameterValue(TEXT("AlgaeAmount"), 0.f);
		G->SetScalarParameterValue(TEXT("TopStart"), 0.5f);
		G->SetScalarParameterValue(TEXT("TopBright"), 0.7f);
		G->SetVectorParameterValue(TEXT("BasaltTint"), FLinearColor(0.62f, 0.56f, 0.5f));
		G->SetScalarParameterValue(TEXT("OxideAmount"), 0.35f);
	}
	// three nested grids: fine over the battlefield, medium around it, coarse rolling hills out to the horizon.
	// each outer grid sinks under the finer one so their interpolation never pokes through
	BuildTerrain(FVector::ZeroVector, 60000.f, 60000.f, 300, 300, [](float X, float Y) { return GroundZ(X, Y); }, G, true, 2500.f);
	BuildTerrain(FVector::ZeroVector, 250000.f, 250000.f, 200, 200, [](float X, float Y)
	{
		const float R = FVector2D(X, Y).Size();
		return PlainZ(X, Y, false) - 150.f - 2000.f * (1.f - FMath::SmoothStep(52000.f, 62000.f, R));
	}, G, false, 2500.f);
	BuildTerrain(FVector::ZeroVector, 450000.f, 450000.f, 160, 160, [](float X, float Y)
	{
		const float R = FVector2D(X, Y).Size();
		return PlainZ(X, Y, false) - 300.f - 6000.f * (1.f - FMath::SmoothStep(220000.f, 260000.f, R));
	}, G, false, 2500.f);
	if (Fog) Fog->SetFogCutoffDistance(1800000.f);
}

void AAralezField::BuildMasis()
{
	UMaterialInterface* RockBase = TwAssets::Material(TEXT("M_RockPBR"));
	UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(RockBase ? RockBase : TwAssets::Material(TEXT("M_Rock")), this);
	if (M && RockBase)
	{
		M->SetScalarParameterValue(TEXT("Tiling"), 60000.f);
		// dark basalt flanks, a snow cap catching the last light, and 40 km of blue-grey air in front
		M->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.8f, 0.76f, 0.78f));
		M->SetScalarParameterValue(TEXT("TopAmount"), 0.7f);
		M->SetVectorParameterValue(TEXT("TopTint"), FLinearColor(1.5f, 1.45f, 1.6f));
		M->SetScalarParameterValue(TEXT("HazeAmount"), 0.78f);
		M->SetVectorParameterValue(TEXT("HazeColor"), FLinearColor(0.36f, 0.34f, 0.42f));
	}
	// seen from the plain, Masis fills the eastern horizon, side-lit by the setting sun in the north-west: ~4.2 km tall, ~22 km wide, ~40 km away
	const float Half = 1100000.f;
	const float HeightScale = 420000.f / (MasisMaxM - MasisMinM);
	const float Range = MasisMaxM - MasisMinM;
	BuildTerrain(FVector(4000000.f, -500000.f, -1500.f), Half, Half, 220, 220, [&](float X, float Y)
	{
		const float U = (X + Half) / (2.f * Half), V = (Y + Half) / (2.f * Half);
		const float XX = FMath::Clamp(U, 0.f, 1.f) * (MasisRes - 1), YY = FMath::Clamp(V, 0.f, 1.f) * (MasisRes - 1);
		const int32 X0 = FMath::Min((int32)XX, MasisRes - 2), Y0 = FMath::Min((int32)YY, MasisRes - 2);
		const float FX = XX - X0, FY = YY - Y0;
		auto H = [](int32 x, int32 y) { return (float)MasisHeight[y * MasisRes + x] / 65535.f; };
		const float S = FMath::Lerp(FMath::Lerp(H(X0, Y0), H(X0 + 1, Y0), FX), FMath::Lerp(H(X0, Y0 + 1), H(X0 + 1, Y0 + 1), FX), FY);
		const float R = FMath::Sqrt(FMath::Square(U - 0.5f) + FMath::Square(V - 0.5f)) * 2.f;
		const float Window = 1.f - FMath::SmoothStep(0.62f, 0.98f, R);
		return S * Range * HeightScale * Window - (1.f - Window) * 60000.f;
	}, M, false, 400000.f);
}

void AAralezField::BuildDressing()
{
	// scanned boulders strewn over the plain
	UStaticMesh* BoulderMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Twilight/Env/Scan/boulder_01/boulder_01_2k/StaticMeshes/boulder_01_2k.boulder_01_2k"));
	UMaterialInterface* BoulderMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Twilight/Materials/MI_Scan_boulder_01.MI_Scan_boulder_01"));
	if (BoulderMesh)
	{
		UInstancedStaticMeshComponent* B = NewObject<UInstancedStaticMeshComponent>(this);
		B->SetStaticMesh(BoulderMesh);
		if (BoulderMat) B->SetMaterial(0, BoulderMat);
		B->SetupAttachment(RootComponent);
		B->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		B->RegisterComponent();
		B->SetWorldTransform(FTransform::Identity);
		B->SetCullDistances(60000, 140000);
		FRandomStream R(77);
		for (int32 i = 0; i < 160; ++i)
		{
			const float A = R.FRandRange(0.f, 2.f * PI);
			const float D = FMath::Sqrt(R.FRand()) * 60000.f;
			const float X = FMath::Cos(A) * D, Y = FMath::Sin(A) * D;
			const float S = R.FRandRange(0.6f, 3.2f) * (R.FRand() < 0.1f ? 2.5f : 1.f);
			B->AddInstance(FTransform(FRotator(R.FRandRange(-20.f, 20.f), R.FRandRange(0.f, 360.f), R.FRandRange(-20.f, 20.f)), FVector(X, Y, GroundZ(X, Y) - S * 30.f), FVector(S)), true);
		}
	}
	// smoke still rising from the battle: a few spots, re-puffed in Tick
	FRandomStream Rs(31);
	for (int32 i = 0; i < 7; ++i)
	{
		const float A = Rs.FRandRange(0.f, 2.f * PI), D = Rs.FRandRange(9000.f, 40000.f);
		const FVector P(FMath::Cos(A) * D, FMath::Sin(A) * D, 0.f);
		SmokeSpots.Add(FVector(P.X, P.Y, GroundZ(P.X, P.Y)));
		// a low fire at its foot
		USceneComponent* Anchor = NewObject<USceneComponent>(this);
		Anchor->SetupAttachment(RootComponent);
		Anchor->RegisterComponent();
		Anchor->SetWorldLocation(SmokeSpots.Last());
		TwFx::AttachFlame(Anchor, NAME_None, FVector::ZeroVector, 2.2f);
		UPointLightComponent* L = NewObject<UPointLightComponent>(this);
		L->SetupAttachment(Anchor);
		L->RegisterComponent();
		L->SetRelativeLocation(FVector(0, 0, 150.f));
		L->SetIntensityUnits(ELightUnits::Unitless);
		L->SetIntensity(9000.f);
		L->SetAttenuationRadius(2600.f);
		L->SetLightColor(FLinearColor(1.f, 0.45f, 0.15f));
		L->SetCastShadows(false);
	}
}

void AAralezField::Tick(float Dt)
{
	Super::Tick(Dt);
	SmokeTimer -= Dt;
	if (SmokeTimer <= 0.f && SmokeSpots.Num() > 0)
	{
		SmokeTimer = 0.9f;
		const FVector P = SmokeSpots[FMath::RandRange(0, SmokeSpots.Num() - 1)];
		TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, P + FVector(0, 0, 300.f + FMath::FRandRange(0.f, 900.f)), 4.f);
	}
}

// ================================================================== fallen warrior
AFallenWarrior::AFallenWarrior()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("Pivot"));
	Pivot->SetupAttachment(Root);
	Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(Pivot);
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	Body->bEnableUpdateRateOptimizations = true;
	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Root);
	Glow->SetRelativeLocation(FVector(-90.f, 0, 90.f));
	Glow->SetIntensityUnits(ELightUnits::Unitless);
	Glow->SetIntensity(0.f);
	Glow->SetAttenuationRadius(900.f);
	Glow->SetLightColor(FLinearColor(1.f, 0.85f, 0.55f));
	Glow->SetCastShadows(false);
}

void AFallenWarrior::BeginPlay()
{
	Super::BeginPlay();
	// Ara's own men: Armenian soldiers in madder red and conical helmets; the king with his gold circlet
	CharName = bAra ? TEXT("Ara") : TEXT("Armsoldc");
	USkeletalMesh* M = TwAssets::Human(CharName);
	bRealHuman = M != nullptr;
	if (!M) M = LoadObject<USkeletalMesh>(nullptr, WarriorMesh);
	if (!M) M = TwAssets::Manny();
	Body->SetSkeletalMesh(M);
	Body->SetCastShadow(true);
	if (bRealHuman)
	{
		// mesh faces +Y: turn it to the actor's +X, then lay him on his back (head toward -X, feet at the origin)
		Body->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));
		Body->SetRelativeScale3D(FVector(bAra ? 0.82f : 0.95f));
		LieRoll = 90.f;
		Pivot->SetRelativeLocation(FVector(0.f, 0.f, 14.f));
		Pivot->SetRelativeRotation(FRotator(LieRoll, 0.f, 0.f));
		for (int32 i = 0; i < 3; ++i) Body->SetCustomPrimitiveDataFloat(i, FMath::FRand());
		AnimIdle = TwAssets::HumanAnim(CharName, TEXT("MM_Idle"));
		AnimRise = TwAssets::HumanAnim(CharName, TEXT("MM_Land"));
		if (AnimIdle)
		{
			Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
			Body->PlayAnimation(AnimIdle, false);
			Body->SetPosition(FMath::FRandRange(0.f, 0.5f), false);
			Body->SetPlayRate(0.f);
		}
	}
	else
	{
		Body->SetRelativeScale3D(FVector(bAra ? 0.95f : 0.86f));
		AnimDeath = HeroAnim(bAra || FMath::RandBool() ? TEXT("MM_Death_Back_01") : TEXT("MM_Death_Front_01"));
		AnimIdle = HeroAnim(TEXT("MM_Idle"));
		if (AnimDeath)
		{
			Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
			Body->PlayAnimation(AnimDeath, false);
			Body->SetPosition(AnimDeath->GetPlayLength() - 0.02f, false);
			Body->SetPlayRate(0.f);
		}
	}
	for (int32 i = 0; i < Body->GetNumMaterials(); ++i)
		if (UMaterialInstanceDynamic* D = Body->CreateDynamicMaterialInstance(i))
		{
			D->SetScalarParameterValue(TEXT("EmissiveIntensity"), 0.f);
			D->SetScalarParameterValue(TEXT("DustAmount"), 0.9f); // dust of the battlefield
			if (bAra) D->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(1.f, 0.75f, 0.4f));
			Mats.Add(D);
		}
}

FVector AFallenWarrior::GetChest() const
{
	return Body ? Body->GetBoneLocation(TEXT("spine_03")) : GetActorLocation();
}

FVector AFallenWarrior::GetHead() const
{
	return Body ? Body->GetBoneLocation(TEXT("head")) : GetActorLocation();
}

bool AFallenWarrior::Heal(float Amount)
{
	if (bRevived || bLocked) return false;
	Progress = FMath::Min(1.f, Progress + Amount);
	LastHeal = GetWorld()->GetTimeSeconds();
	if (Progress < 1.f) return false;
	bRevived = true;
	RiseTime = GetWorld()->GetTimeSeconds();
	if (!bRealHuman && AnimDeath)
	{
		// legacy body: the death clip runs backwards
		Body->SetPlayRate(-1.2f);
		Body->SetPosition(AnimDeath->GetPlayLength() - 0.02f, false);
		Body->Play(false);
	}
	TwFx::Sound(GetWorld(), TEXT("sfx_soul_chime"), GetActorLocation(), 1.f, bAra ? 0.6f : 1.f);
	TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, GetChest(), bAra ? 1.6f : 0.9f);
	return true;
}

void AFallenWarrior::Tick(float Dt)
{
	Super::Tick(Dt);
	const float Now = GetWorld()->GetTimeSeconds();
	const bool bHealing = !bRevived && Now - LastHeal < 0.2f;
	float Want = bHealing ? 2500.f + 6000.f * Progress : 0.f;
	if (bRevived && RiseTime > 0.f) Want = FMath::Max(0.f, 14000.f * (1.f - (Now - RiseTime) / 2.5f));
	if (bAra && !bRevived && !bLocked) Want = FMath::Max(Want, 1200.f + 600.f * FMath::Sin(Now * 2.f));
	Glow->SetIntensity(FMath::FInterpTo(Glow->Intensity, Want, Dt, 6.f));
	for (UMaterialInstanceDynamic* D : Mats) if (D)
	{
		D->SetScalarParameterValue(TEXT("HitFlash"), bHealing ? 0.15f * Progress : 0.f);
		D->SetScalarParameterValue(TEXT("RimIntensity"), (bHealing ? 0.5f * Progress : 0.f) + (bAra ? 0.15f : 0.f));
	}
	if (bRealHuman)
	{
		// while being licked he stirs (a slight lift of the chest); once healed he rises from the ground
		if (!bRevived)
		{
			const float Stir = bHealing ? 4.f * Progress * (0.5f + 0.5f * FMath::Sin(Now * 6.f)) : 0.f;
			Pivot->SetRelativeRotation(FRotator(LieRoll - Stir, 0.f, 0.f));
		}
		else
		{
			const float T = FMath::Clamp((Now - RiseTime) / 1.6f, 0.f, 1.f);
			const float E = T * T * (3.f - 2.f * T);
			Pivot->SetRelativeRotation(FRotator(LieRoll * (1.f - E), 0.f, 0.f));
			Pivot->SetRelativeLocation(FVector(0.f, 0.f, 14.f * (1.f - E)));
			if (T >= 1.f && AnimIdle && Body->GetPlayRate() == 0.f)
			{
				Body->PlayAnimation(AnimIdle, true);
				Body->SetPlayRate(1.f);
			}
		}
		return;
	}
	if (bRevived && AnimDeath && AnimIdle && Body->GetAnimationMode() == EAnimationMode::AnimationSingleNode && !Body->IsPlaying() && Now - RiseTime > 0.3f)
	{
		Body->SetPlayRate(1.f);
		Body->PlayAnimation(AnimIdle, true);
		AnimDeath = nullptr;
	}
}

// ================================================================== Shamiram's soldier
AShamiramSoldier::AShamiramSoldier()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(RootComponent);
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
	Body->bEnableUpdateRateOptimizations = true;
}

void AShamiramSoldier::BeginPlay()
{
	Super::BeginPlay();
	// Assyrian spearmen: bronze armour, lapis tunic, scutum; the queen in gold and crimson
	const TCHAR* C = bQueen ? TEXT("Shamiram") : TEXT("Babsoldc");
	USkeletalMesh* M = TwAssets::Human(C);
	const bool bReal = M != nullptr;
	if (!M) M = LoadObject<USkeletalMesh>(nullptr, WarriorMesh);
	if (!M) M = TwAssets::Manny();
	Body->SetSkeletalMesh(M);
	Body->SetRelativeRotation(FRotator(0.f, MeshYaw, 0.f));
	Body->SetRelativeScale3D(FVector(bReal ? 1.f : 0.86f));
	if (bReal)
	{
		for (int32 i = 0; i < 3; ++i) Body->SetCustomPrimitiveDataFloat(i, FMath::FRand());
		AnimIdle = TwAssets::HumanAnim(C, TEXT("MM_Idle"));
		AnimRun = TwAssets::HumanAnim(C, TEXT("MF_Unarmed_Jog_Fwd"));
		AnimWalk = TwAssets::HumanAnim(C, TEXT("MF_Unarmed_Walk_Fwd"));
		AnimStrike = TwAssets::HumanAnim(C, TEXT("MM_Attack_01"));
		if (!bQueen)
			if (UStaticMesh* SM = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Twilight/Humans/Props/Spear2/spear/StaticMeshes/spear.spear")))
			{
				Spear = NewObject<UStaticMeshComponent>(this);
				Spear->SetStaticMesh(SM);
				Spear->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				Spear->SetupAttachment(Body, TEXT("hand_r"));
				Spear->SetRelativeTransform(FTransform(FRotator(21.03f, -88.92f, 85.09f), FVector(-93.86f, -4.67f, -7.52f), FVector(1.0188f)));
				Spear->RegisterComponent();
			}
	}
	else
	{
		for (int32 i = 0; i < Body->GetNumMaterials(); ++i)
			if (UMaterialInstanceDynamic* D = Body->CreateDynamicMaterialInstance(i))
			{
				D->SetScalarParameterValue(TEXT("EmissiveIntensity"), 0.f);
				D->SetVectorParameterValue(TEXT("Tint"), i == 0 ? FLinearColor(0.62f, 0.5f, 0.42f) : FLinearColor(0.25f, 0.22f, 0.24f));
				if (i == 5) D->SetScalarParameterValue(TEXT("CrestGlow"), 0.f);
			}
		AnimIdle = HeroAnim(TEXT("MM_Idle"));
		AnimRun = HeroAnim(TEXT("MF_Unarmed_Jog_Fwd"));
		AnimWalk = HeroAnim(TEXT("MF_Unarmed_Walk_Fwd"));
		AnimStrike = HeroAnim(TEXT("MM_Attack_03"));
	}
	Body->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	PlayLoop(AnimIdle, FMath::FRandRange(0.85f, 1.1f));
	Body->SetPosition(FMath::FRand() * 2.f, false);
	if (Post.IsNearlyZero()) Post = GetActorLocation();
	WanderGoal = Post;
}

void AShamiramSoldier::PlayLoop(UAnimSequence* A, float Rate)
{
	if (!A || CurrentAnim == A) return;
	CurrentAnim = A;
	Body->PlayAnimation(A, true);
	Body->SetPlayRate(Rate);
}

void AShamiramSoldier::Repel(const FVector& From)
{
	if (bQueen) return;
	Stagger = 2.5f;
	const FVector Away = (GetActorLocation() - From).GetSafeNormal2D();
	FVector P = GetActorLocation() + Away * 500.f;
	P.Z = AAralezField::GroundZ(P.X, P.Y);
	SetActorLocation(P);
	CurrentAnim = nullptr;
	if (UAnimSequence* Hit = TwAssets::HumanAnim(TEXT("Babsoldc"), TEXT("MM_HitReact_Front_Hvy_01"))) Body->PlayAnimation(Hit, false);
	else PlayLoop(AnimIdle, 0.5f);
}

void AShamiramSoldier::Tick(float Dt)
{
	Super::Tick(Dt);
	if (bQueen) return;
	StrikeCd = FMath::Max(0.f, StrikeCd - Dt);
	if (Stagger > 0.f) { Stagger -= Dt; return; }
	const FVector Me = GetActorLocation();
	// the nearest Aralez flying low within reach of a spear
	AAralezSpirit* Prey = nullptr;
	float Best = 2200.f;
	for (TActorIterator<AAralezSpirit> It(GetWorld()); It; ++It)
	{
		const FVector S = It->GetActorLocation();
		const float H = S.Z - AAralezField::GroundZ(S.X, S.Y);
		const float D = FVector::Dist2D(S, Me);
		if (H < 700.f && D < Best && FVector::Dist2D(S, Post) < 4000.f) { Best = D; Prey = *It; }
	}
	FVector Goal = WanderGoal;
	float Spd = 160.f;
	if (Prey)
	{
		Goal = Prey->GetActorLocation();
		Spd = 520.f;
		if (Best < 330.f && StrikeCd <= 0.f)
		{
			StrikeCd = 2.2f;
			CurrentAnim = nullptr;
			Body->PlayAnimation(AnimStrike, false);
			Prey->Stunned(1.6f);
			TwFx::Sound(GetWorld(), TEXT("sfx_wraith_hiss"), Prey->GetActorLocation(), Prey->IsBot() ? 0.4f : 1.f, 0.7f);
			TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, Prey->GetActorLocation(), 0.6f);
			return;
		}
	}
	else
	{
		Wander -= Dt;
		if (Wander <= 0.f || FVector::Dist2D(Me, WanderGoal) < 150.f)
		{
			Wander = FMath::FRandRange(4.f, 9.f);
			WanderGoal = Post + FVector(FMath::FRandRange(-1800.f, 1800.f), FMath::FRandRange(-1800.f, 1800.f), 0.f);
		}
	}
	if (StrikeCd > 1.4f) return; // finishing the strike
	FVector To = Goal - Me; To.Z = 0.f;
	const float D = To.Size();
	if (D > 120.f)
	{
		const FVector Dir = To / D;
		FVector P = Me + Dir * FMath::Min(D, Spd * Dt);
		P.Z = AAralezField::GroundZ(P.X, P.Y);
		SetActorLocationAndRotation(P, FMath::RInterpTo(GetActorRotation(), FRotator(0.f, Dir.Rotation().Yaw, 0.f), Dt, 6.f));
		PlayLoop(Prey ? AnimRun : AnimWalk, 1.f);
	}
	else PlayLoop(AnimIdle, 1.f);
}
