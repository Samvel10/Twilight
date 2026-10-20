#include "Vishap.h"
#include "SerpentBodyComponent.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "Fireball.h"
#include "FireOrb.h"
#include "VahagnCharacter.h"
#include "VahagnGameMode.h"

#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "ReferenceSkeleton.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraComponent.h"

namespace
{
	const FLinearColor SkinNormal(0.035f, 0.028f, 0.05f);
	const FLinearColor SkinElite(0.25f, 0.01f, 0.01f);
	const FLinearColor SkinBoss(0.02f, 0.03f, 0.035f);
	const FLinearColor VeinNormal(1.f, 0.14f, 0.03f);
	const FLinearColor VeinBoss(1.f, 0.06f, 0.02f);
}

AVishap::AVishap()
{
	PrimaryActorTick.bCanEverTick = true;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Root->SetMobility(EComponentMobility::Movable);
	RootComponent = Root;
}

void AVishap::Setup(bool bInBoss, int32 InTier, float HealthMult)
{
	bBoss = bInBoss;
	Tier = InTier;
	if (bBoss)
	{
		NumSeg = 44; R0 = 190.f; Spacing = 250.f; BaseSpeed = 2200.f; TurnRate = 55.f;
		MaxHealth = 460.f * HealthMult;
	}
	else
	{
		NumSeg = 21; R0 = Tier ? 100.f : 88.f; Spacing = R0 * 1.35f; BaseSpeed = Tier ? 2900.f : 2400.f; TurnRate = Tier ? 120.f : 95.f;
		MaxHealth = (Tier ? 34.f : 20.f) * HealthMult;
	}
	Health = MaxHealth;
	TrailStep = Spacing / 3.f;
}

void AVishap::BeginPlay()
{
	Super::BeginPlay();
	if (Segments.Num() == 0) Build();
	HeadPos = GetActorLocation();
	HeadVel = FVector(0, 0, BaseSpeed * 0.7f);
	// trail hangs straight down into the sea: the vishap rises from the depths
	const int32 N = FMath::CeilToInt((NumSeg + 2) * Spacing / TrailStep) + 4;
	Trail.Reset();
	for (int32 i = 0; i < N; ++i) Trail.Add(HeadPos - FVector(0, 0, i * TrailStep));
	CircleAxisSeed = FVector(FMath::FRandRange(-1.f, 1.f), FMath::FRandRange(-1.f, 1.f), 0.f).GetSafeNormal();
	AttackCooldown = bBoss ? 4.f : FMath::FRandRange(5.f, 8.f); // let the player see them coming
	Wobble = FMath::FRandRange(0.f, 10.f);
	BeginState(EVishapState::Emerge);
	TwFx::Burst(GetWorld(), TwFx::EFx::Splash, FVector(HeadPos.X, HeadPos.Y, 20.f), bBoss ? 6.f : 2.5f);
	TwFx::Sound(GetWorld(), TEXT("sfx_vishap_roar"), HeadPos, bBoss ? 1.f : 0.6f, bBoss ? 0.75f : FMath::FRandRange(0.95f, 1.2f));
}

void AVishap::Build()
{
	UStaticMesh* SphereMesh = TwAssets::Sphere();
	UStaticMesh* ConeMesh = TwAssets::Cone();

	SkinMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	const FLinearColor Skin = bBoss ? SkinBoss : (Tier ? SkinElite : SkinNormal);
	const FLinearColor Vein = bBoss ? VeinBoss : (Tier ? FLinearColor(1.f, 0.03f, 0.02f) : VeinNormal);
	if (SkinMat)
	{
		SkinMat->SetVectorParameterValue(TEXT("SkinColor"), Skin);
		SkinMat->SetVectorParameterValue(TEXT("VeinColor"), Vein);
		// wet obsidian scales with a few thick lava veins; cool rim separates them from the golden hero
		SkinMat->SetScalarParameterValue(TEXT("VeinIntensity"), bBoss ? 3.5f : 2.6f);
		SkinMat->SetScalarParameterValue(TEXT("VeinTiling"), 1.6f);
		SkinMat->SetScalarParameterValue(TEXT("VeinSharpness"), 45.f); // dark obsidian with a few veins, not lava speckle like the hero
		SkinMat->SetScalarParameterValue(TEXT("ScaleTiling"), 4.f);
		SkinMat->SetScalarParameterValue(TEXT("Roughness"), 0.22f);
		SkinMat->SetScalarParameterValue(TEXT("Metallic"), 0.5f);
		SkinMat->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(0.3f, 0.5f, 1.f)); // cool rim: separates them from the gold hero without turning them silver
		SkinMat->SetScalarParameterValue(TEXT("RimIntensity"), 0.45f);
		SkinMat->SetVectorParameterValue(TEXT("SkinColor2"), Skin * 2.2f);
	}
	BoneMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (BoneMat)
	{
		BoneMat->SetVectorParameterValue(TEXT("SkinColor"), FLinearColor(0.09f, 0.07f, 0.06f));
		BoneMat->SetVectorParameterValue(TEXT("VeinColor"), Vein);
		BoneMat->SetScalarParameterValue(TEXT("VeinIntensity"), 0.8f);
		BoneMat->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(1.f, 0.3f, 0.08f));
		BoneMat->SetScalarParameterValue(TEXT("RimIntensity"), 0.4f);
	}
	EyeMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (EyeMat)
	{
		EyeMat->SetVectorParameterValue(TEXT("Color"), bBoss ? FLinearColor(1.f, 0.1f, 0.02f) : FLinearColor(1.f, 0.35f, 0.05f));
		EyeMat->SetScalarParameterValue(TEXT("GlowMode"), 1.f); EyeMat->SetScalarParameterValue(TEXT("Intensity"), 40.f);
	}

	auto MakePart = [this](UStaticMesh* Mesh, USceneComponent* Parent, UMaterialInterface* Mat, bool bCollide) -> UStaticMeshComponent*
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Mesh);
		C->SetMobility(EComponentMobility::Movable);
		C->SetCastShadow(false);
		if (bCollide)
		{
			C->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
			// fireballs sweep into these (block -> OnHit); no overlap bookkeeping while the body teleports every frame
			C->SetCollisionObjectType(ECC_PhysicsBody);
			C->SetCollisionResponseToAllChannels(ECR_Ignore);
			C->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
			C->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Block);
			C->SetGenerateOverlapEvents(false);
		}
		else
		{
			C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		}
		if (Mat) C->SetMaterial(0, Mat);
		if (Parent) C->SetupAttachment(Parent); else C->SetupAttachment(RootComponent);
		C->RegisterComponent();
		return C;
	};

	// body
	SegRadius.SetNum(NumSeg);
	for (int32 i = 0; i < NumSeg; ++i)
	{
		const float T = float(i) / float(NumSeg - 1);
		float R = R0 * FMath::Lerp(1.0f, 0.18f, FMath::Pow(T, 1.15f));
		if (i == 1) R *= 0.8f; // neck
		R *= 1.f + 0.12f * FMath::Sin(T * PI * 2.f); // slight belly swell
		SegRadius[i] = R;
		UStaticMeshComponent* S = MakePart(SphereMesh, nullptr, SkinMat, true);
		S->SetAbsolute(true, true, true);
		S->SetWorldScale3D(FVector(R / 50.f * 1.7f, R / 50.f, R / 50.f * 0.92f));
		Segments.Add(S);

		// dorsal spikes, longer near the head
		if (i >= 2 && i % 3 == 0 && i < NumSeg - 3)
		{
			UStaticMeshComponent* Sp = MakePart(ConeMesh, S, BoneMat, false);
			const float L = FMath::Lerp(1.4f, 0.5f, T);
			Sp->SetRelativeLocation(FVector(-10.f, 0.f, 42.f));
			Sp->SetRelativeRotation(FRotator(-35.f, 0.f, 0.f));
			Sp->SetRelativeScale3D(FVector(0.32f, 0.32f, 0.7f * L));
		}
		// side fins on a few segments
		if (bBoss && (i == 4 || i == 9))
		{
			for (int32 s = -1; s <= 1; s += 2)
			{
				UStaticMeshComponent* Fin = MakePart(ConeMesh, S, BoneMat, false);
				Fin->SetRelativeLocation(FVector(-20.f, 45.f * s, 10.f));
				Fin->SetRelativeRotation(FRotator(-60.f, 0.f, 70.f * s));
				Fin->SetRelativeScale3D(FVector(0.5f, 0.15f, 1.6f));
			}
		}
	}

	SegDist.SetNum(NumSeg);
	SegDist[0] = 0.f;
	for (int32 i = 1; i < NumSeg; ++i) SegDist[i] = SegDist[i - 1] + (SegRadius[i - 1] + SegRadius[i]) * 0.5f;

	// head: skull, snout, jaw, horns, eyes (attached to segment 0)
	USceneComponent* H = Segments[0];
	Skull = MakePart(SphereMesh, H, SkinMat, true);
	Skull->SetRelativeLocation(FVector(45.f, 0.f, 6.f));
	Skull->SetRelativeScale3D(FVector(1.25f, 0.85f, 0.62f));
	UStaticMeshComponent* Snout = MakePart(SphereMesh, H, SkinMat, false);
	Snout->SetRelativeLocation(FVector(95.f, 0.f, 4.f));
	Snout->SetRelativeScale3D(FVector(0.95f, 0.55f, 0.38f));
	Jaw = MakePart(SphereMesh, H, SkinMat, false);
	Jaw->SetRelativeLocation(FVector(60.f, 0.f, -22.f));
	Jaw->SetRelativeScale3D(FVector(1.2f, 0.62f, 0.26f));
	HeadParts = { Skull, Snout, Jaw };
	for (int32 s = -1; s <= 1; s += 2)
	{
		UStaticMeshComponent* Horn = MakePart(ConeMesh, H, BoneMat, false);
		Horn->SetRelativeLocation(FVector(10.f, 26.f * s, 38.f));
		Horn->SetRelativeRotation(FRotator(-110.f, 0.f, 18.f * s));
		Horn->SetRelativeScale3D(FVector(0.24f, 0.24f, bBoss ? 2.3f : 1.6f));
		UStaticMeshComponent* Eye = MakePart(SphereMesh, H, EyeMat, false);
		Eye->SetRelativeLocation(FVector(88.f, 20.f * s, 20.f));
		Eye->SetRelativeScale3D(FVector(0.3f, 0.2f, 0.16f)); // readable head: big glowing eyes
		// brow spikes
		UStaticMeshComponent* Brow = MakePart(ConeMesh, H, BoneMat, false);
		Brow->SetRelativeLocation(FVector(70.f, 22.f * s, 30.f));
		Brow->SetRelativeRotation(FRotator(-75.f, 0.f, 25.f * s));
		Brow->SetRelativeScale3D(FVector(0.12f, 0.12f, 0.45f));
	}

	// visible fire-breath cone: the player must see what hurts him
	BreathMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (BreathMat) { BreathMat->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.28f, 0.05f)); BreathMat->SetScalarParameterValue(TEXT("GlowMode"), 1.f); BreathMat->SetScalarParameterValue(TEXT("Intensity"), 0.4f); }
	BreathCone = MakePart(ConeMesh, nullptr, BreathMat, false);
	BreathCone->SetAbsolute(true, true, true);
	BreathCone->SetVisibility(false);

	EyeLight = NewObject<UPointLightComponent>(this);
	EyeLight->SetupAttachment(H);
	EyeLight->SetRelativeLocation(FVector(110.f, 0.f, 20.f));
	EyeLight->SetIntensityUnits(ELightUnits::Unitless);
	EyeLight->SetIntensity(bBoss ? 12000.f : 3500.f);
	EyeLight->SetAttenuationRadius(bBoss ? 2500.f : 900.f);
	EyeLight->SetLightColor(FLinearColor(1.f, 0.25f, 0.05f));
	EyeLight->SetCastShadows(false);
	EyeLight->RegisterComponent();

	BreathAudio = NewObject<UAudioComponent>(this);
	BreathAudio->SetupAttachment(H);
	BreathAudio->bAutoActivate = false;
	BreathAudio->SetSound(TwAssets::Sound(TEXT("sfx_fire_breath")));
	BreathAudio->RegisterComponent();
	BuildDragon();
}

// ------------------------------------------------------------------ dragon body
namespace
{
	const TCHAR* DragonMeshPath = TEXT("/Game/Twilight/Vishap/Dragon/european_dragon.european_dragon");
	const TCHAR* DragonFlyPath = TEXT("/Game/Twilight/Vishap/Dragon/european_dragonFly.european_dragonFly");
	const FName DragonHeadBone(TEXT("DEF-neck_004_012")); // UE turns the glTF "." into "_"
	const FName DragonJawBone(TEXT("DEF-Teeth_Top_013"));
	const FName DragonTailBone(TEXT("DEF-tail_010_0161"));
}

bool AVishap::BuildSerpent()
{
	// the Armenian vishap is a serpent of lakes and clouds: a real giant-viper scan, straightened and rigged (CC0/CC-BY)
	static const TCHAR* SerpentMeshPath = TEXT("/Game/Twilight/Vishap/Mesh/SK_VishapSerpent/SkeletalMeshes/SK_VishapSerpent.SK_VishapSerpent");
	static const TCHAR* SerpentHornsPath = TEXT("/Game/Twilight/Vishap/Mesh/Horns/SM_VishapHorns/StaticMeshes/SM_VishapHorns.SM_VishapHorns");
	if (FParse::Param(FCommandLine::Get(), TEXT("TwWingedDragon"))) return false;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, SerpentMeshPath);
	if (!Mesh) return false;
	Serpent = NewObject<USerpentBodyComponent>(this);
	Serpent->SetupAttachment(RootComponent);
	Serpent->SetAbsolute(true, true, true);
	Serpent->SetSkinnedAssetAndUpdate(Mesh);
	Serpent->HeadAttachment = LoadObject<UStaticMesh>(nullptr, SerpentHornsPath);
	Serpent->HeadScale = bBoss ? 1.5f : 1.35f;
	const float WantLen = bBoss ? 9000.f : (Tier ? 3200.f : 2600.f);
	Serpent->SetWorldScale3D(FVector(WantLen / 1000.f));
	Serpent->RegisterComponent();
	const TCHAR* MI = bBoss ? TEXT("/Game/Twilight/Vishap/Materials/MI_Vishap_Storm.MI_Vishap_Storm")
		: (Tier ? TEXT("/Game/Twilight/Vishap/Materials/MI_Vishap_Bronze.MI_Vishap_Bronze") : TEXT("/Game/Twilight/Vishap/Materials/MI_Vishap_Default.MI_Vishap_Default"));
	SerpentMat = Serpent->CreateDynamicMaterialInstance(0, LoadObject<UMaterialInterface>(nullptr, MI));
	if (SerpentMat) SerpentMat->SetVectorParameterValue(TEXT("FlashColor"), FLinearColor(1.f, 0.32f, 0.08f));
	for (UStaticMeshComponent* Sg : Segments) if (Sg) Sg->SetVisibility(false, true);
	if (Skull) Skull->SetVisibility(false, true);
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
	bSerpent = true;
	return true;
}

void AVishap::UpdateSerpent(float Dt)
{
	if (!Serpent) return;
	SerpentPath.Reset(Trail.Num() + 1);
	SerpentPath.Add(HeadPos);
	SerpentPath.Append(Trail);
	SerpentJaw = FMath::FInterpTo(SerpentJaw, FMath::Lerp(-0.8f, 1.f, JawOpen), Dt, 8.f);
	Serpent->JawOpen = SerpentJaw;
	Serpent->ApplyPath(SerpentPath, FVector::UpVector, LifeTime);
	if (SerpentMat)
	{
		const bool bFiring = State == EVishapState::Breath || State == EVishapState::BreathWindup;
		SerpentMat->SetScalarParameterValue(TEXT("MouthGlow"), bFiring ? 20.f : 3.f + 1.f * FMath::Sin(LifeTime * 3.f));
		// the scan material adds FlashColor * HitFlash as emission: keep it a brief red-hot glint, not a white wash
		SerpentMat->SetScalarParameterValue(TEXT("HitFlash"), FMath::Min(HitFlash, 1.f) * 0.22f);
	}
	// a body the camera flies through would fill the screen: hide it for that instant
	if (APlayerController* CPC = GetWorld()->GetFirstPlayerController())
		if (CPC->PlayerCameraManager)
		{
			const FVector C = CPC->PlayerCameraManager->GetCameraLocation();
			bool bNear = false;
			for (int32 i = 0; i < SegDist.Num() && i < Segments.Num(); i += 2)
				if (FVector::DistSquared(Segments[i]->GetComponentLocation(), C) < FMath::Square(SegRadius[i] * 1.6f + 120.f)) { bNear = true; break; }
			if (Serpent->IsVisible() == bNear) Serpent->SetVisibility(!bNear, true);
		}
}

void AVishap::BuildDragon()
{
	if (BuildSerpent()) return;
	USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, DragonMeshPath);
	UAnimSequence* Fly = LoadObject<UAnimSequence>(nullptr, DragonFlyPath);
	if (!Mesh || !Fly) return;
	Dragon = NewObject<USkeletalMeshComponent>(this);
	Dragon->SetupAttachment(RootComponent);
	Dragon->SetAbsolute(true, true, true);
	Dragon->SetSkeletalMesh(Mesh);
	Dragon->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dragon->SetCastShadow(true);
	Dragon->bCastDynamicShadow = true;
	Dragon->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Dragon->RegisterComponent();
	DragonMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Dragon")), this);
	if (DragonMat)
	{
		// realistic reptile skin (lifted albedo, wet scale tops, translucent wings); the boss is a rusty red
		const FLinearColor Tint = bBoss ? FLinearColor(0.95f, 0.8f, 0.74f) : (Tier ? FLinearColor(1.f, 0.88f, 0.82f) : FLinearColor(1.f, 0.95f, 0.92f));
		DragonMat->SetVectorParameterValue(TEXT("Tint"), Tint);
		// lava only in the deepest ~10% of the painted crevices (linear albedo luminance < ~0.009)
		DragonMat->SetScalarParameterValue(TEXT("VeinThreshold"), 0.0045f);
		DragonMat->SetScalarParameterValue(TEXT("VeinGain"), 260.f);
		DragonMat->SetScalarParameterValue(TEXT("VeinIntensity"), bBoss ? 0.4f : 0.f);
		Dragon->SetMaterial(0, DragonMat);
	}
	if (UMaterialInterface* Teeth = TwAssets::Material(TEXT("M_DragonTeeth"))) { Dragon->SetMaterial(1, Teeth); Dragon->SetMaterial(2, Teeth); }
	if (EyeMat) Dragon->SetMaterial(3, EyeMat);
	Dragon->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Dragon->PlayAnimation(Fly, true);
	Dragon->SetPlayRate(FMath::FRandRange(0.72f, 0.82f) * (bBoss ? 0.75f : 1.f));
	Dragon->SetPosition(FMath::FRandRange(0.f, Fly->GetPlayLength()), false);
	bDragon = true;
	CalibrateDragon();

	// the sphere chain becomes invisible hit volumes along the flight path, sized to the dragon
	for (UStaticMeshComponent* Sg : Segments) if (Sg) Sg->SetVisibility(false, true);
	if (EyeMat) EyeMat->SetScalarParameterValue(TEXT("Intensity"), 6.f);
}

bool AVishap::CalibrateDragon()
{
	if (!Dragon || !Dragon->GetSkeletalMeshAsset()) return false;
	const FReferenceSkeleton& Ref = Dragon->GetSkeletalMeshAsset()->GetRefSkeleton();
	auto RefCS = [&Ref](FName Bone) -> FVector
	{
		int32 I = Ref.FindBoneIndex(Bone);
		if (I == INDEX_NONE) return FVector::ZeroVector;
		FTransform T = FTransform::Identity;
		while (I != INDEX_NONE) { T = T * Ref.GetRefBonePose()[I]; I = Ref.GetParentIndex(I); }
		return T.GetLocation();
	};
	const FVector Head = RefCS(DragonHeadBone);
	const FVector Tail = RefCS(DragonTailBone);
	if (Head.IsNearlyZero() && Tail.IsNearlyZero()) return false;
	DragonHeadCS = Head;
	const FVector Fwd = (Head - Tail).GetSafeNormal();
	FVector Up = FVector::UpVector - Fwd * FVector::DotProduct(FVector::UpVector, Fwd);
	if (Up.SizeSquared() < 0.05f) Up = FVector::ForwardVector - Fwd * FVector::DotProduct(FVector::ForwardVector, Fwd);
	DragonMeshFrame = FRotationMatrix::MakeFromXZ(Fwd, Up.GetSafeNormal()).ToQuat();
	const float RefLen = FMath::Max(50.f, FVector::Dist(Head, Tail));
	const float WantLen = bBoss ? 3800.f : (Tier ? 1500.f : 1350.f); // head-to-tail (~22 m wingspan, boss ~60 m)
	DragonScale = WantLen / RefLen;
	Dragon->SetWorldScale3D(FVector(DragonScale));
	UE_LOG(LogTwilight, Display, TEXT("[TwDragon] head=%s tail=%s reflen=%.0f scale=%.2f bones=%d"), *Head.ToCompactString(), *Tail.ToCompactString(), RefLen, DragonScale, Ref.GetNum());
	// hit volumes: spread the chain over the dragon's real length, a little fatter (wings)
	if (NumSeg > 1)
	{
		const float Step = WantLen * 1.1f / (NumSeg - 1);
		for (int32 i = 0; i < NumSeg && i < Segments.Num(); ++i)
		{
			SegDist[i] = i * Step;
			SegRadius[i] *= bBoss ? 1.9f : 1.35f; // the boss is a bigger target (wings, neck)
			const float R = SegRadius[i];
			Segments[i]->SetWorldScale3D(FVector(R / 50.f * 1.7f, R / 50.f, R / 50.f * 0.92f));
		}
	}
	bDragonCalibrated = true;
	return true;
}

void AVishap::UpdateDragon(float Dt)
{
	if (bSerpent) { UpdateSerpent(Dt); return; }
	if (!bDragon || !Dragon) return;
	// the reference pose stands upright; the Fly clip lays the body out: take the frame from the animated pose
	if (!bDragonAnimFrame && LifeTime > 0.2f)
	{
		const FVector H = Dragon->GetBoneLocation(DragonHeadBone, EBoneSpaces::ComponentSpace);
		const FVector T = Dragon->GetBoneLocation(DragonTailBone, EBoneSpaces::ComponentSpace);
		if (!(H - T).IsNearlyZero())
		{
			const FVector Fwd = (H - T).GetSafeNormal();
			FVector Up = FVector::UpVector - Fwd * FVector::DotProduct(FVector::UpVector, Fwd);
			if (Up.SizeSquared() < 0.05f) Up = FVector::RightVector - Fwd * FVector::DotProduct(FVector::RightVector, Fwd);
			DragonMeshFrame = FRotationMatrix::MakeFromXZ(Fwd, Up.GetSafeNormal()).ToQuat();
			DragonHeadCS = H;
			bDragonAnimFrame = true;
			UE_LOG(LogTwilight, Display, TEXT("[TwDragon] anim frame head=%s tail=%s"), *H.ToCompactString(), *T.ToCompactString());
		}
	}
	// heading follows the flight with a short lag; bank into turns
	const FVector V = (HeadVel + KnockVel);
	const FVector Want = V.GetSafeNormal().IsNearlyZero() ? DragonFwd : V.GetSafeNormal();
	const FVector Prev = DragonFwd;
	DragonFwd = FMath::VInterpNormalRotationTo(DragonFwd, Want, Dt, 160.f);
	const float Yaw = FMath::FindDeltaAngleDegrees(Prev.Rotation().Yaw, DragonFwd.Rotation().Yaw) / FMath::Max(Dt, 1e-3f);
	DragonBank = FMath::FInterpTo(DragonBank, FMath::Clamp(-Yaw * 0.6f, -50.f, 50.f), Dt, 3.f);
	FVector Up = FVector::UpVector - DragonFwd * FVector::DotProduct(FVector::UpVector, DragonFwd);
	if (Up.SizeSquared() < 0.02f) Up = FVector::ForwardVector;
	const FQuat World = FRotationMatrix::MakeFromXZ(DragonFwd, Up.GetSafeNormal()).ToQuat() * FQuat(FVector::ForwardVector, FMath::DegreesToRadians(DragonBank));
	const FQuat Rot = World * DragonMeshFrame.Inverse();
	Dragon->SetWorldLocationAndRotation(HeadPos - Rot.RotateVector(DragonHeadCS * DragonScale), Rot);
	// wings beat faster when climbing / dashing
	Dragon->SetPlayRate((bBoss ? 0.55f : 0.78f) * FMath::Clamp(0.8f + V.Size() / 6000.f + FMath::Max(0.f, V.Z) / 4000.f, 0.8f, 1.5f));
	if (DragonMat)
	{
		DragonMat->SetScalarParameterValue(TEXT("HitFlash"), HitFlash * 1.5f); // (the material keeps it to the cracks)
		const bool bFiring = State == EVishapState::Breath || State == EVishapState::BreathWindup;
		DragonMat->SetScalarParameterValue(TEXT("VeinIntensity"), (bBoss ? 0.4f : 0.f) + (bFiring ? 1.2f : 0.f)); // the throat glows only when it breathes fire
	}
	// never fill the lens with a wing
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		if (PC->PlayerCameraManager)
		{
			const bool bNear = FVector::DistSquared(Dragon->Bounds.Origin, PC->PlayerCameraManager->GetCameraLocation()) < FMath::Square(Dragon->Bounds.SphereRadius * 0.55f);
			if (Dragon->IsVisible() == bNear) Dragon->SetVisibility(!bNear);
		}
}

AVahagnCharacter* AVishap::Player() const
{
	return Cast<AVahagnCharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
}

FVector AVishap::MouthLocation() const
{
	if (bSerpent && Serpent) return Serpent->GetSocketTransform(TEXT("Head")).TransformPosition(FVector(45.f, 0.f, -3.f));
	if (bDragon && Dragon) return Dragon->GetBoneLocation(DragonJawBone) + DragonFwd * 60.f * DragonScale;
	if (Segments.Num() == 0) return HeadPos;
	const FTransform T = Segments[0]->GetComponentTransform();
	return T.TransformPosition(FVector(150.f, 0.f, -5.f));
}

void AVishap::GetAimPoints(TArray<FVector>& Out) const
{
	if (Segments.Num() == 0) { Out.Add(HeadPos); return; }
	Out.Add(Skull ? Skull->GetComponentLocation() : HeadPos);
	for (int32 i = 2; i < Segments.Num() - 3; i += 3) Out.Add(Segments[i]->GetComponentLocation());
}

float AVishap::DistanceToPoint(const FVector& P) const
{
	float Best = FVector::Dist(P, HeadPos);
	for (int32 i = 0; i < Segments.Num(); i += 2)
	{
		Best = FMath::Min(Best, FVector::Dist(P, Segments[i]->GetComponentLocation()) - SegRadius[i]);
	}
	return FMath::Max(0.f, Best);
}

// ------------------------------------------------------------------ trail
FVector AVishap::SampleTrail(float Distance, FVector* OutTangent) const
{
	const float F = Distance / TrailStep;
	const int32 I = FMath::Clamp(FMath::FloorToInt(F), 0, Trail.Num() - 2);
	const float A = FMath::Clamp(F - I, 0.f, 1.f);
	const FVector P = FMath::Lerp(Trail[I], Trail[I + 1], A);
	if (OutTangent) *OutTangent = (Trail[I] - Trail[I + 1]).GetSafeNormal();
	return P;
}

// ------------------------------------------------------------------ AI
void AVishap::BeginState(EVishapState S)
{
	State = S;
	StateTime = 0.f;
	switch (S)
	{
	case EVishapState::Emerge: StateDur = bBoss ? 3.2f : 1.8f; break;
	case EVishapState::Approach: StateDur = 9.f; break;
	case EVishapState::Circle: StateDur = FMath::FRandRange(1.8f, 3.4f); break;
	case EVishapState::BreathWindup:
		StateDur = bBoss ? 0.9f : 0.75f;
		TwFx::Sound(GetWorld(), TEXT("sfx_vishap_roar"), HeadPos, bBoss ? 1.f : 0.7f, bBoss ? 0.7f : FMath::FRandRange(1.f, 1.25f));
		break;
	case EVishapState::Breath:
		StateDur = bBoss ? 2.6f : 1.7f;
		BreathTick = 0.f;
		if (!BreathFx) BreathFx = TwFx::AttachFlame(Segments[0], NAME_None, FVector(160.f, 0.f, -5.f), bBoss ? 2.4f : 1.2f);
		if (BreathFx) BreathFx->Activate(true);
		if (BreathAudio && BreathAudio->Sound) BreathAudio->Play();
		break;
	case EVishapState::DashWindup: StateDur = 0.55f; break;
	case EVishapState::Dash:
		StateDur = 1.5f;
		bDashHit = false;
		if (AVahagnCharacter* P = Player()) DashDir = (P->GetActorLocation() + P->GetVelocity() * 0.35f - HeadPos).GetSafeNormal();
		break;
	case EVishapState::Spit: StateDur = bBoss ? 1.2f : 0.6f; SpitsLeft = bBoss ? 3 : 1; break;
	case EVishapState::Retreat: StateDur = FMath::FRandRange(1.2f, 2.2f); break;
	case EVishapState::Dying: StateDur = bBoss ? 2.6f : 1.8f; break;
	}
	if (S != EVishapState::Breath)
	{
		if (BreathFx) BreathFx->Deactivate();
		if (BreathAudio) BreathAudio->FadeOut(0.3f, 0.f);
	}
}

void AVishap::Steer(const FVector& Target, float DesiredSpeed, float TurnDegPerSec, float Dt)
{
	FVector ToT = Target - HeadPos;
	// separation from other heads
	for (TActorIterator<AVishap> It(GetWorld()); It; ++It)
	{
		if (*It == this || !It->IsAlive()) continue;
		const FVector D = HeadPos - It->GetHeadLocation();
		const float L = D.Size();
		const float Min = bBoss || It->IsBoss() ? 3200.f : 1600.f;
		if (L < Min && L > 1.f) ToT += D / L * (Min - L) * 3.f;
	}
	// keep above the sea and inside the arena
	if (State != EVishapState::Emerge && HeadPos.Z < 900.f) ToT.Z += (900.f - HeadPos.Z) * 6.f;
	const float R = FVector2D(HeadPos.X, HeadPos.Y).Size();
	if (R > AVahagnCharacter::ArenaRadius * 0.95f) ToT += FVector(-HeadPos.X, -HeadPos.Y, 0.f).GetSafeNormal() * 8000.f;
	// look ahead for islands
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(VishapAvoid), false, this);
	const FVector Fwd = HeadVel.GetSafeNormal();
	if (GetWorld()->LineTraceSingleByObjectType(Hit, HeadPos, HeadPos + Fwd * 2500.f, FCollisionObjectQueryParams(ECC_WorldStatic), Q))
	{
		ToT += (Hit.ImpactNormal + FVector::UpVector) * 6000.f;
	}

	const FVector Want = ToT.GetSafeNormal();
	FVector Dir = HeadVel.GetSafeNormal();
	if (Dir.IsNearlyZero()) Dir = Want;
	const float MaxAng = FMath::DegreesToRadians(TurnDegPerSec) * Dt;
	const float Ang = FMath::Acos(FMath::Clamp(FVector::DotProduct(Dir, Want), -1.f, 1.f));
	if (Ang > KINDA_SMALL_NUMBER)
	{
		const float A = FMath::Min(1.f, MaxAng / Ang);
		Dir = FMath::Lerp(Dir, Want, A).GetSafeNormal();
	}
	const float Spd = FMath::FInterpTo(HeadVel.Size(), DesiredSpeed, Dt, 2.5f);
	HeadVel = Dir * Spd;
}

void AVishap::Think(float Dt)
{
	AVahagnCharacter* P = Player();
	const FVector PL = P ? P->GetActorLocation() : FVector(0, 0, 3000.f);
	const FVector ToP = PL - HeadPos;
	const float Dist = ToP.Size();
	StateTime += Dt;
	AttackCooldown -= Dt;
	Wobble += Dt;
	const float Enrage = (bBoss && Phase >= 2) ? 1.25f : 1.f;
	const FVector Side = FVector::CrossProduct(ToP.GetSafeNormal(), FVector::UpVector).GetSafeNormal();
	const FVector WobbleOff = Side * FMath::Sin(Wobble * 1.7f) * (bBoss ? 2200.f : 1300.f) + FVector(0, 0, FMath::Sin(Wobble * 1.1f) * 600.f);

	switch (State)
	{
	case EVishapState::Emerge:
	{
		const FVector Up = HeadPos + FVector(0, 0, 4000.f) + (ToP.GetSafeNormal2D() * 1500.f);
		Steer(Up, BaseSpeed * 0.9f, TurnRate * 1.3f, Dt);
		if (StateTime > StateDur) BeginState(EVishapState::Approach);
		break;
	}
	case EVishapState::Approach:
	{
		Steer(PL + WobbleOff + FVector(0, 0, 400.f), BaseSpeed * Enrage, TurnRate, Dt);
		const float Range = bBoss ? 6500.f : 4200.f;
		// attack tokens: never more than a couple of vishaps attack at the same time
		int32 Attackers = 0;
		for (TActorIterator<AVishap> It(GetWorld()); It; ++It) if (*It != this && It->IsAttacking()) ++Attackers;
		int32 MaxAttackers = 2;
		if (const AVahagnGameMode* GM = GetWorld()->GetAuthGameMode<AVahagnGameMode>()) MaxAttackers = GM->GetWave() <= 1 ? 1 : 2;
		if (P && !P->IsDead() && Dist < Range && AttackCooldown <= 0.f && (bBoss || Attackers < MaxAttackers))
		{
			const float R = FMath::FRand();
			if (Dist > 2600.f && R < 0.3f) BeginState(EVishapState::Spit);
			else if (R < 0.68f) BeginState(EVishapState::BreathWindup);
			else BeginState(EVishapState::DashWindup);
		}
		else if (StateTime > StateDur) BeginState(EVishapState::Circle);
		break;
	}
	case EVishapState::Circle:
	{
		const float Rad = bBoss ? 6000.f : 3400.f;
		const float Ang = Wobble * (bBoss ? 0.35f : 0.6f) + CircleAxisSeed.X * PI;
		const FVector Orbit = PL + FVector(FMath::Cos(Ang), FMath::Sin(Ang), 0.f) * Rad + FVector(0, 0, 600.f + 400.f * FMath::Sin(Ang * 2.f));
		Steer(Orbit, BaseSpeed * 0.95f * Enrage, TurnRate, Dt);
		if (StateTime > StateDur) BeginState(EVishapState::Approach);
		break;
	}
	case EVishapState::BreathWindup:
	{
		Steer(PL, BaseSpeed * 0.35f, TurnRate * 2.2f, Dt);
		JawOpen = FMath::FInterpTo(JawOpen, 0.6f, Dt, 6.f);
		if (StateTime > StateDur) BeginState(EVishapState::Breath);
		break;
	}
	case EVishapState::Breath:
	{
		// slow tracking: dodge by strafing
		Steer(PL + (P ? P->GetVelocity() * 0.2f : FVector::ZeroVector), BaseSpeed * 0.3f, TurnRate * (bBoss ? 0.55f : 0.7f), Dt);
		JawOpen = FMath::FInterpTo(JawOpen, 1.f, Dt, 10.f);
		BreathTick -= Dt;
		if (BreathTick <= 0.f) { BreathTick = 0.12f; DoBreathTick(); }
		BreathFxTick -= Dt;
		if (StateTime > StateDur) { AttackCooldown = (bBoss ? 2.2f : 3.2f) / Enrage; BeginState(EVishapState::Retreat); }
		break;
	}
	case EVishapState::DashWindup:
	{
		// rear back
		Steer(HeadPos - ToP.GetSafeNormal() * 1000.f + FVector(0, 0, 500.f), BaseSpeed * 0.4f, TurnRate * 1.5f, Dt);
		JawOpen = FMath::FInterpTo(JawOpen, 0.8f, Dt, 8.f);
		if (StateTime > StateDur) BeginState(EVishapState::Dash);
		break;
	}
	case EVishapState::Dash:
	{
		Steer(HeadPos + DashDir * 5000.f, BaseSpeed * 2.4f * Enrage, TurnRate * 0.6f, Dt);
		if (P && !bDashHit && !P->IsDead())
		{
			const float HitR = bBoss ? 800.f : 420.f;
			if (FVector::Dist(HeadPos, PL) < HitR)
			{
				bDashHit = true;
				UGameplayStatics::ApplyDamage(P, bBoss ? 24.f : 15.f, nullptr, this, nullptr);
				TwFx::Sound(GetWorld(), TEXT("sfx_vishap_hit"), PL, 1.f, 0.7f);
			}
		}
		if (StateTime > StateDur) { AttackCooldown = 2.6f / Enrage; JawOpen = 0.f; BeginState(EVishapState::Retreat); }
		break;
	}
	case EVishapState::Spit:
	{
		Steer(PL, BaseSpeed * 0.5f, TurnRate * 1.8f, Dt);
		JawOpen = FMath::FInterpTo(JawOpen, 0.7f, Dt, 8.f);
		const float Interval = StateDur / FMath::Max(1, bBoss ? 3 : 1);
		if (SpitsLeft > 0 && StateTime > Interval * ((bBoss ? 3 : 1) - SpitsLeft + 0.6f)) { DoSpit(); --SpitsLeft; }
		if (StateTime > StateDur) { AttackCooldown = 2.f / Enrage; BeginState(EVishapState::Circle); }
		break;
	}
	case EVishapState::Retreat:
	{
		Steer(HeadPos - ToP.GetSafeNormal() * 3000.f + Side * 2000.f + FVector(0, 0, 800.f), BaseSpeed * 1.05f, TurnRate, Dt);
		JawOpen = FMath::FInterpTo(JawOpen, 0.f, Dt, 5.f);
		if (StateTime > StateDur) BeginState(EVishapState::Circle);
		break;
	}
	default: break;
	}
	if (State != EVishapState::Breath && State != EVishapState::BreathWindup && State != EVishapState::DashWindup && State != EVishapState::Dash && State != EVishapState::Spit)
	{
		JawOpen = FMath::FInterpTo(JawOpen, 0.08f + 0.06f * FMath::Sin(Wobble * 3.f), Dt, 3.f);
	}
}

void AVishap::DoBreathTick()
{
	AVahagnCharacter* P = Player();
	if (!P || P->IsDead()) return;
	const FVector M = MouthLocation();
	const FVector Fwd = Segments[0]->GetForwardVector();
	const FVector To = P->GetActorLocation() - M;
	const float D = To.Size();
	const float Range = bBoss ? 5200.f : 3300.f;
	const float Cone = bBoss ? 20.f : 15.f;
	const float Ang = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(To / FMath::Max(D, 1.f), Fwd), -1.f, 1.f)));
	if (D < Range && Ang < Cone)
	{
		UGameplayStatics::ApplyDamage(P, bBoss ? 2.6f : 1.6f, nullptr, this, nullptr);
	}
	// visible fire puffs along the cone (throttled: particles are expensive)
	if (BreathFxTick <= 0.f)
	{
		BreathFxTick = 0.3f;
		TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, M + Fwd * FMath::FRandRange(0.3f, 0.9f) * Range * 0.8f, bBoss ? 1.3f : 1.f);
	}
}

void AVishap::DoSpit()
{
	AVahagnCharacter* P = Player();
	if (!P) return;
	const FVector M = MouthLocation();
	const FVector Aim = P->GetActorLocation() + P->GetVelocity() * (FVector::Dist(M, P->GetActorLocation()) / 6500.f) * 0.85f;
	const FVector Dir = (Aim - M).GetSafeNormal();
	const int32 Count = bBoss ? 3 : 1;
	for (int32 i = 0; i < Count; ++i)
	{
		const float Yaw = (i - (Count - 1) * 0.5f) * 7.f;
		const FVector D = FRotator(0.f, Yaw, 0.f).RotateVector(Dir);
		FActorSpawnParameters Sp;
		Sp.Owner = this;
		Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (AFireball* F = GetWorld()->SpawnActor<AFireball>(M, D.Rotation(), Sp))
		{
			F->Launch(D, bBoss ? 11.f : 8.f, 0.f, bBoss ? 2.2f : 1.5f, true, 6500.f);
		}
	}
	TwFx::Sound(GetWorld(), TEXT("sfx_fireball_cast"), M, 1.f, 0.6f);
}

// ------------------------------------------------------------------ damage
void AVishap::ApplyHitAtComponent(float Damage, const FVector& Where, UPrimitiveComponent* Comp, AVahagnCharacter* Hero)
{
	const bool bHead = Comp && (Comp == Skull || (Segments.Num() > 0 && Comp == Segments[0]));
	ApplyHit(Damage * (bHead ? 2.f : 1.f), Where, Hero, true);
}

void AVishap::ApplyHit(float Damage, const FVector& Where, AVahagnCharacter* Hero, bool bNotify)
{
	if (!IsAlive() || Damage <= 0.f) return;
	if (State == EVishapState::Emerge && StateTime < 0.6f) Damage *= 0.5f;
	Health -= Damage;
	HitFlash = 1.f;
	TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, Where, bBoss ? 0.75f : 0.6f);
	TwFx::Sound(GetWorld(), TEXT("sfx_vishap_hit"), Where, 0.6f, FMath::FRandRange(0.85f, 1.15f) * (bBoss ? 0.7f : 1.f));

	if (bBoss)
	{
		const float F = Health / MaxHealth;
		const int32 NewPhase = F < 0.3f ? 2 : (F < 0.62f ? 1 : 0);
		if (NewPhase > Phase)
		{
			Phase = NewPhase;
			TwFx::Sound2D(GetWorld(), TEXT("sfx_vishap_roar"), 1.f, 0.6f);
			if (AVahagnGameMode* GM = GetWorld()->GetAuthGameMode<AVahagnGameMode>()) GM->OnBossPhase(this, Phase);
			AttackCooldown = 0.5f;
			BeginState(EVishapState::Retreat);
		}
	}

	const bool bKill = Health <= 0.f;
	if (Hero && bNotify) Hero->RegisterHit(bKill);
	if (bKill) StartDying(Hero);
}

void AVishap::Knockback(const FVector& From, float Strength)
{
	KnockVel += (HeadPos - From).GetSafeNormal() * Strength * (bBoss ? 0.3f : 1.f);
}

void AVishap::StartDying(AVahagnCharacter* Killer)
{
	if (State == EVishapState::Dying) return;
	BeginState(EVishapState::Dying);
	DyingTime = 0.f;
	NextPop = 0;
	DebrisVel.SetNum(Segments.Num());
	for (int32 i = 0; i < Segments.Num(); ++i)
	{
		Segments[i]->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		DebrisVel[i] = HeadVel * 0.25f + FMath::VRand() * 150.f;
	}
	if (Skull) Skull->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (BreathCone) BreathCone->SetVisibility(false);
	TwFx::Burst(GetWorld(), TwFx::EFx::VishapDeath, HeadPos, bBoss ? 6.f : 2.5f);
	TwFx::LightFlash(GetWorld(), HeadPos, FLinearColor(1.f, 0.4f, 0.1f), bBoss ? 400000.f : 80000.f, bBoss ? 12000.f : 4000.f, bBoss ? 1.5f : 0.6f);
	TwFx::Sound(GetWorld(), TEXT("sfx_vishap_death"), HeadPos, 1.f, bBoss ? 0.7f : 1.f);
	if (Killer) Killer->AddShake(bBoss ? 1.4f : FMath::Clamp(1.f - FVector::Dist(Killer->GetActorLocation(), HeadPos) / 6000.f, 0.f, 0.5f));
	if (EyeMat) EyeMat->SetScalarParameterValue(TEXT("Intensity"), 0.f);

	// fire orbs: heal + Nova charge
	const int32 Orbs = bBoss ? 8 : 2;
	for (int32 i = 0; i < Orbs; ++i)
	{
		FActorSpawnParameters Sp;
		Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		GetWorld()->SpawnActor<AFireOrb>(HeadPos + FMath::VRand() * 300.f, FRotator::ZeroRotator, Sp);
	}
	if (AVahagnGameMode* GM = GetWorld()->GetAuthGameMode<AVahagnGameMode>()) GM->OnVishapKilled(this);
}

// ------------------------------------------------------------------ tick
void AVishap::Tick(float Dt)
{
	Super::Tick(Dt);
	LifeTime += Dt;
	if (State == EVishapState::Dying) { UpdateDying(Dt); return; }

	Think(Dt);
	HeadPos += (HeadVel + KnockVel) * Dt;
	KnockVel = FMath::VInterpTo(KnockVel, FVector::ZeroVector, Dt, 3.f);

	// record trail
	if (FVector::Dist(HeadPos, Trail[0]) >= TrailStep)
	{
		const FVector Dir = (HeadPos - Trail[0]).GetSafeNormal();
		while (FVector::Dist(HeadPos, Trail[0]) >= TrailStep)
		{
			Trail.Insert(Trail[0] + Dir * TrailStep, 0);
		}
		const int32 Need = FMath::CeilToInt((SegDist.Num() ? SegDist.Last() + 2.f * Spacing : (NumSeg + 2) * Spacing) / TrailStep) + 4;
		if (Trail.Num() > Need) Trail.SetNum(Need);
	}
	UpdateBody(Dt);
	UpdateDragon(Dt);
	HitFlash = FMath::Max(0.f, HitFlash - Dt * 6.f);
}

void AVishap::UpdateBody(float Dt)
{
	const float Lag = FVector::Dist(HeadPos, Trail[0]);
	// segments the camera passes through would fill the screen with a flat red tube: hide them for that instant
	FVector CamLoc(1e9f);
	if (APlayerController* CPC = GetWorld()->GetFirstPlayerController())
		if (CPC->PlayerCameraManager) CamLoc = CPC->PlayerCameraManager->GetCameraLocation();
	const bool bHideNear = State != EVishapState::Dying;
	for (int32 i = 0; i < Segments.Num(); ++i)
	{
		FVector Tan;
		const float DistAlong = FMath::Max(0.f, SegDist[i] - Lag);
		FVector P = i == 0 ? HeadPos : SampleTrail(DistAlong + Lag * 0.f, &Tan);
		if (i == 0) Tan = HeadVel.GetSafeNormal().IsNearlyZero() ? FVector::ForwardVector : HeadVel.GetSafeNormal();
		// gentle undulation travelling down the body
		const float Wave = FMath::Sin(LifeTime * 5.f - i * 0.55f) * SegRadius[i] * 0.25f;
		const FVector Side = FVector::CrossProduct(Tan, FVector::UpVector).GetSafeNormal();
		P += Side * Wave;
		const FRotator Rot = FRotationMatrix::MakeFromXZ(Tan, FVector::UpVector).Rotator();
		Segments[i]->SetWorldLocationAndRotation(P, Rot);
		if (bHideNear && !bDragon && !bSerpent)
		{
			const bool bNear = FVector::DistSquared(P, CamLoc) < FMath::Square(SegRadius[i] * 1.8f + (bBoss ? 600.f : 250.f));
			if (Segments[i]->IsVisible() == bNear) Segments[i]->SetVisibility(!bNear, true);
		}
	}
	if (State == EVishapState::Dying && BreathCone) BreathCone->SetVisibility(false);
	// breath cone follows the mouth
	if (BreathCone)
	{
		const bool bWind = State == EVishapState::BreathWindup, bFire = State == EVishapState::Breath;
		BreathCone->SetVisibility(bWind || bFire);
		if (bWind || bFire)
		{
			const float Range = (bBoss ? 5200.f : 3300.f) * (bFire ? 1.f : 0.35f + 0.65f * FMath::Clamp(StateTime / FMath::Max(StateDur, 0.01f), 0.f, 1.f));
			const float Cone = FMath::DegreesToRadians(bBoss ? 20.f : 15.f);
			const float Jit = bFire ? FMath::FRandRange(0.9f, 1.1f) : 0.3f;
			const FVector Fwd = Segments[0]->GetForwardVector();
			const FVector Mouth = MouthLocation();
			const float Rad = FMath::Tan(Cone) * Range * Jit;
			BreathCone->SetWorldTransform(FTransform(FRotationMatrix::MakeFromZ(-Fwd).Rotator(), Mouth + Fwd * Range * 0.5f, FVector(Rad / 50.f, Rad / 50.f, Range / 100.f)));
			// soft: the cone reads as heat haze; also fade it when the camera is inside or right next to it
			float CamK = 1.f;
			if (APlayerController* PCc = GetWorld()->GetFirstPlayerController())
				if (PCc->PlayerCameraManager) CamK = FMath::Clamp((float)FVector::Dist(PCc->PlayerCameraManager->GetCameraLocation(), Mouth) / (Range * 0.8f), 0.05f, 1.f);
			if (BreathMat) BreathMat->SetScalarParameterValue(TEXT("Intensity"), (bFire ? 0.45f + FMath::FRandRange(-0.08f, 0.08f) : 0.12f) * CamK);
		}
	}
	if (Jaw)
	{
		Jaw->SetRelativeRotation(FRotator(-JawOpen * 32.f, 0.f, 0.f));
		Jaw->SetRelativeLocation(FVector(60.f - JawOpen * 6.f, 0.f, -22.f - JawOpen * 10.f));
	}
	if (SkinMat) SkinMat->SetScalarParameterValue(TEXT("HitFlash"), HitFlash * 0.18f);
	if (EyeLight)
	{
		const bool bAngry = State == EVishapState::BreathWindup || State == EVishapState::Breath || State == EVishapState::DashWindup;
		EyeLight->SetIntensity((bBoss ? 12000.f : 3500.f) * (bAngry ? 2.5f : 1.f));
	}
}

void AVishap::UpdateDying(float Dt)
{
	DyingTime += Dt;
	if (bSerpent && Serpent && Serpent->IsVisible())
	{
		// struck down: the serpent coils and falls into the lake, smoking
		if (SerpentFallVel.IsNearlyZero())
		{
			SerpentFallVel = HeadVel * 0.3f + FVector(0, 0, 300.f);
			TwFx::AttachFlame(Serpent, TEXT("Head"), FVector::ZeroVector, bBoss ? 2.f : 1.f);
		}
		SerpentFallVel.Z -= 2200.f * Dt;
		HeadPos += SerpentFallVel * Dt;
		if (FVector::Dist(HeadPos, Trail[0]) > TrailStep) Trail.Insert(HeadPos, 0);
		JawOpen = 1.f;
		HitFlash = 0.6f + 0.4f * FMath::Sin(DyingTime * 20.f);
		UpdateSerpent(Dt);
		if (HeadPos.Z < -300.f || DyingTime > StateDur - 0.15f)
		{
			TwFx::Burst(GetWorld(), TwFx::EFx::Splash, FVector(HeadPos.X, HeadPos.Y, 10.f), bBoss ? 6.f : 3.f);
			Serpent->SetVisibility(false, true);
		}
	}
	if (bDragon && Dragon && Dragon->IsVisible())
	{
		if (DragonFallVel.IsNearlyZero()) DragonFallVel = HeadVel * 0.4f + FVector(0, 0, 400.f);
		if (!DragonFire)
		{
			// the body catches fire as it falls
			DragonFire = TwFx::AttachFlame(Dragon, TEXT("DEF-Spine_003_05"), FVector::ZeroVector, bBoss ? 2.5f : 1.4f);
			TwFx::AttachFlame(Dragon, DragonHeadBone, FVector::ZeroVector, bBoss ? 1.6f : 0.9f);
		}
		DragonFallVel.Z -= 2600.f * Dt;
		Dragon->SetWorldLocation(Dragon->GetComponentLocation() + DragonFallVel * Dt);
		Dragon->AddWorldRotation(FRotator(-70.f * Dt, 0.f, 140.f * Dt));
		Dragon->SetPlayRate(0.25f);
		if (DragonMat) DragonMat->SetScalarParameterValue(TEXT("Burn"), FMath::Min(DyingTime * 2.5f, 6.f));
		if (Dragon->Bounds.Origin.Z < 0.f || DyingTime > StateDur - 0.15f)
		{
			const FVector P = Dragon->Bounds.Origin;
			TwFx::Burst(GetWorld(), TwFx::EFx::Splash, FVector(P.X, P.Y, 10.f), bBoss ? 6.f : 3.f);
			TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, P, bBoss ? 3.f : 1.8f);
			Dragon->SetVisibility(false);
		}
	}
	for (int32 i = 0; i < Segments.Num(); ++i)
	{
		if (!Segments[i]->IsVisible()) continue;
		DebrisVel[i].Z -= 1800.f * Dt;
		const FVector P = Segments[i]->GetComponentLocation() + DebrisVel[i] * Dt;
		Segments[i]->SetWorldLocation(P);
		Segments[i]->AddWorldRotation(FRotator(90.f * Dt, 120.f * Dt, 0.f));
		if (P.Z < 0.f)
		{
			Segments[i]->SetVisibility(false, true);
			if (i % 3 == 0) TwFx::Burst(GetWorld(), TwFx::EFx::Splash, FVector(P.X, P.Y, 10.f), bBoss ? 2.f : 0.8f);
		}
	}
	// chain explosions down the body
	const float PopInterval = bBoss ? 0.05f : 0.06f;
	if (SkinMat) SkinMat->SetScalarParameterValue(TEXT("VeinIntensity"), (bBoss ? 4.f : 3.f) + DyingTime * 10.f); // burning from inside
	while (NextPop < Segments.Num() && DyingTime > NextPop * PopInterval)
	{
		// head-to-tail chain: every segment bursts and vanishes, nothing is left floating
		const FVector P = Segments[NextPop]->GetComponentLocation();
		const float K = (bBoss ? 2.2f : 1.15f) * (1.f - 0.5f * NextPop / float(Segments.Num()));
		TwFx::Burst(GetWorld(), NextPop % 2 == 0 ? TwFx::EFx::FireballImpact : TwFx::EFx::Sparks, P, NextPop % 2 == 0 ? K : 0.6f);
		Segments[NextPop]->SetVisibility(false, true);
		++NextPop;
	}
	if (DyingTime > StateDur) Destroy();
}
