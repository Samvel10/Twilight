#include "HaykArcher.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "TwPoseAnimInstance.h"

#include "Components/SkeletalMeshComponent.h"
#include "Components/SphereComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Animation/AnimSequence.h"

static void SetupZone(UPrimitiveComponent* C)
{
	C->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	C->SetCollisionObjectType(ECC_WorldDynamic);
	C->SetCollisionResponseToAllChannels(ECR_Ignore);
	C->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
	C->SetHiddenInGame(true);
}

AHaykArcher::AHaykArcher()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	Body = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(Root);
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;

	HeadZone = CreateDefaultSubobject<USphereComponent>(TEXT("HeadZone"));
	HeadZone->SetupAttachment(Root);
	HeadZone->SetAbsolute(true, true, true);
	SetupZone(HeadZone);
	TorsoZone = CreateDefaultSubobject<UCapsuleComponent>(TEXT("TorsoZone"));
	TorsoZone->SetupAttachment(Root);
	TorsoZone->SetAbsolute(true, true, true);
	SetupZone(TorsoZone);
	LegsZone = CreateDefaultSubobject<UCapsuleComponent>(TEXT("LegsZone"));
	LegsZone->SetupAttachment(Root);
	LegsZone->SetAbsolute(true, true, true);
	SetupZone(LegsZone);

	Bow = CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("Bow"));
	Bow->SetupAttachment(Root);
	Bow->SetAbsolute(true, true, true);
	Bow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	StringTop = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StringTop"));
	StringTop->SetupAttachment(Root);
	StringTop->SetAbsolute(true, true, true);
	StringTop->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	StringTop->SetCastShadow(false);
	StringBottom = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("StringBottom"));
	StringBottom->SetupAttachment(Root);
	StringBottom->SetAbsolute(true, true, true);
	StringBottom->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	StringBottom->SetCastShadow(false);
	NockedArrow = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("NockedArrow"));
	NockedArrow->SetupAttachment(Root);
	NockedArrow->SetAbsolute(true, true, true);
	NockedArrow->SetCollisionEnabled(ECollisionEnabled::NoCollision);

	Rim = CreateDefaultSubobject<UPointLightComponent>(TEXT("Rim"));
	Rim->SetupAttachment(Root);
	Rim->SetIntensityUnits(ELightUnits::Unitless);
	Rim->SetCastShadows(false);
}

void AHaykArcher::Setup(bool bInBel, float InMaxHealth, bool bInSoldier)
{
	bBel = bInBel;
	bSoldier = bInSoldier;
	MaxHealth = Health = InMaxHealth;
	Scale = bBel ? 1.9f : (bSoldier ? 1.05f : 1.f);
}

void AHaykArcher::BeginPlay()
{
	Super::BeginPlay();
	// realistic CC-BY people: Hayk the bearded giant archer, Bel in gold armour, Bel's Babylonian guards in bronze and lapis
	const TCHAR* Char = bBel ? TEXT("Bel") : (bSoldier ? TEXT("Babsoldc") : TEXT("Hayk"));
	USkeletalMesh* HumanMesh = FParse::Param(FCommandLine::Get(), TEXT("TwManny")) ? nullptr : TwAssets::Human(Char);
	bRealHuman = HumanMesh != nullptr;
	Body->SetSkeletalMesh(bRealHuman ? HumanMesh : TwAssets::Manny());
	Body->SetRelativeLocation(FVector(0, 0, 0));
	Body->SetRelativeRotation(FRotator(0, -90.f, 0));
	// the Spartan base is 2.09 m: Hayk stays a head taller than everyone; the Roman base (Bel, guards) is 1.75 m
	Body->SetRelativeScale3D(FVector(Scale * (bRealHuman ? (bBel || bSoldier ? 1.03f : 0.92f) : 1.f)));
	Body->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	Body->SetAnimInstanceClass(UTwPoseAnimInstance::StaticClass());
	Poser = Cast<UTwPoseAnimInstance>(Body->GetAnimInstance());

	if (bRealHuman)
	{
		AnimIdle = TwAssets::HumanAnim(Char, TEXT("MM_Idle"));
		AnimAim = TwAssets::HumanAnim(Char, TEXT("MF_Rifle_Idle_ADS"));
		AnimShoot = TwAssets::HumanAnim(Char, TEXT("MM_Rifle_Fire"));
		AnimHit = TwAssets::HumanAnim(Char, TEXT("MM_HitReact_Front_Hvy_01"));
		AnimHitHeavy = AnimHit;
		AnimDeath = TwAssets::HumanAnim(Char, TEXT("MM_Death_Back_01"));
		AnimCheer = TwAssets::HumanAnim(Char, TEXT("MM_ChargedAttack"));
	}
	if (!AnimIdle)
	AnimIdle = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle"));
	if (!bRealHuman || !AnimAim)
	{
	AnimAim = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Rifle/MF_Rifle_Idle_ADS.MF_Rifle_Idle_ADS"));
	AnimShoot = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Rifle/MM_Rifle_Fire.MM_Rifle_Fire"));
	AnimHit = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Lgt_01.MM_HitReact_Front_Lgt_01"));
	AnimHitHeavy = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Hvy_01.MM_HitReact_Front_Hvy_01"));
	AnimDeath = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Death/MM_Death_Back_01.MM_Death_Back_01"));
	AnimCheer = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_ChargedAttack.MM_ChargedAttack"));
	}
	if (Poser) Poser->SetLoop(AnimIdle, 0.01f);

	// armour look: engraved bronze for Hayk, black iron with blood-red veins for Bel
	BodyMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (BodyMat)
	{
		BodyMat->SetVectorParameterValue(TEXT("SkinColor"), (bBel || bSoldier) ? FLinearColor(0.025f, 0.02f, 0.02f) : FLinearColor(0.32f, 0.17f, 0.07f));
		BodyMat->SetVectorParameterValue(TEXT("VeinColor"), (bBel || bSoldier) ? FLinearColor(1.f, 0.08f, 0.02f) : FLinearColor(1.f, 0.7f, 0.25f));
		BodyMat->SetScalarParameterValue(TEXT("VeinIntensity"), bBel ? 4.f : 1.2f); BodyMat->SetScalarParameterValue(TEXT("RimIntensity"), 0.35f); BodyMat->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(1.f, 0.55f, 0.25f));
		BodyMat->SetScalarParameterValue(TEXT("Metallic"), 0.6f);
		BodyMat->SetVectorParameterValue(TEXT("FlashColor"), FLinearColor(1.f, 0.22f, 0.04f)); // a red-hot hit, not a cream wash
		if (!bRealHuman) for (int32 i = 0; i < Body->GetNumMaterials(); ++i) Body->SetMaterial(i, BodyMat);
	}
	if (bRealHuman)
	{
		// keep the people's own look-dev materials; MIDs only for the hit flash and per-soldier variation
		for (int32 i = 0; i < Body->GetNumMaterials(); ++i)
			if (UMaterialInstanceDynamic* D = Body->CreateDynamicMaterialInstance(i))
			{
				D->SetVectorParameterValue(TEXT("FlashColor"), FLinearColor(1.f, 0.22f, 0.04f));
				D->SetScalarParameterValue(TEXT("DustAmount"), 0.5f);
				HumanMats.Add(D);
			}
		for (int32 i = 0; i < 3; ++i) Body->SetCustomPrimitiveDataFloat(i, FMath::FRand());
		Body->SetCastShadow(true);
	}

	// regalia, placed in world space every frame from the head bone (bone axes differ from the actor's)
	UMaterialInstanceDynamic* Gold = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Gold) { Gold->SetVectorParameterValue(TEXT("Color"), bBel ? FLinearColor(1.f, 0.6f, 0.15f) : FLinearColor(1.f, 0.85f, 0.4f)); Gold->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Gold->SetScalarParameterValue(TEXT("Intensity"), 1.5f); }
	UMaterialInstanceDynamic* Bronze = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (Bronze) { Bronze->SetVectorParameterValue(TEXT("SkinColor"), FLinearColor(0.35f, 0.2f, 0.08f)); Bronze->SetScalarParameterValue(TEXT("Metallic"), 0.8f); Bronze->SetScalarParameterValue(TEXT("VeinIntensity"), 1.2f); Bronze->SetVectorParameterValue(TEXT("VeinColor"), FLinearColor(1.f, 0.7f, 0.3f)); Bronze->SetScalarParameterValue(TEXT("RimIntensity"), 0.3f); }
	auto AddPart = [this](UStaticMesh* Mesh, const FVector& Off, const FRotator& Rot, const FVector& Scl, UMaterialInterface* Mat)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Mesh);
		C->SetupAttachment(Root);
		C->SetAbsolute(true, true, true);
		C->SetWorldScale3D(Scl * Scale);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		if (Mat) C->SetMaterial(0, Mat);
		C->RegisterComponent();
		Regalia.Add(C);
		RegaliaOffset.Add(Off);
		RegaliaRot.Add(Rot);
	};
	if (bRealHuman) {} // the models carry their own helmets, crowns and armour
	else if (bBel)
	{
		for (int32 i = 0; i < 6; ++i)
		{
			const float A = i * 60.f;
			AddPart(TwAssets::Cone(), FVector(0, 0, 16.f) + FRotator(0, A, 0).RotateVector(FVector(10.f, 0, 0)), FRotator(-15.f, A, 0.f), FVector(0.06f, 0.06f, 0.16f), Gold);
		}
	}
	else
	{
		// conical bronze helmet with a small gold finial
		AddPart(TwAssets::Cone(), FVector(0.f, 0, 14.f), FRotator::ZeroRotator, FVector(0.26f, 0.26f, 0.28f), Bronze);
		AddPart(TwAssets::Sphere(), FVector(0.f, 0, 30.f), FRotator::ZeroRotator, FVector(0.035f), Gold);
	}

	// tunic and cape
	{
		UMaterialInstanceDynamic* Tunic = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
		UMaterialInstanceDynamic* Cape = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
		if (Tunic)
		{
			Tunic->SetVectorParameterValue(TEXT("SkinColor"), bBel ? FLinearColor(0.03f, 0.02f, 0.02f) : FLinearColor(0.3f, 0.17f, 0.07f));
			Tunic->SetVectorParameterValue(TEXT("VeinColor"), bBel ? FLinearColor(1.f, 0.08f, 0.02f) : FLinearColor(1.f, 0.65f, 0.25f));
			Tunic->SetScalarParameterValue(TEXT("VeinIntensity"), bBel ? 1.6f : 0.8f);
			Tunic->SetScalarParameterValue(TEXT("Metallic"), 0.7f);
			Tunic->SetScalarParameterValue(TEXT("RimIntensity"), 0.25f);
		}
		if (Cape)
		{
			Cape->SetVectorParameterValue(TEXT("SkinColor"), bBel ? FLinearColor(0.012f, 0.008f, 0.01f) : FLinearColor(0.28f, 0.025f, 0.02f));
			Cape->SetVectorParameterValue(TEXT("VeinColor"), bBel ? FLinearColor(0.6f, 0.04f, 0.02f) : FLinearColor(0.9f, 0.3f, 0.1f));
			Cape->SetScalarParameterValue(TEXT("VeinIntensity"), 0.25f);
			Cape->SetScalarParameterValue(TEXT("Metallic"), 0.f);
			Cape->SetScalarParameterValue(TEXT("Roughness"), 0.9f);
			Cape->SetScalarParameterValue(TEXT("RimIntensity"), 0.2f);
		}
		auto AddGarment = [this](UStaticMesh* Mesh, FName Bone, const FVector& Off, const FRotator& Rot, const FVector& Scl, UMaterialInterface* Mat)
		{
			UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
			C->SetStaticMesh(Mesh);
			C->SetupAttachment(Root);
			C->SetAbsolute(true, true, true);
			C->SetWorldScale3D(Scl * Scale);
			C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			if (Mat) C->SetMaterial(0, Mat);
			C->RegisterComponent();
			Garments.Add(C);
			GarmentBone.Add(Bone);
			GarmentOffset.Add(Off);
			GarmentRot.Add(Rot);
		};
		if (!bRealHuman) AddGarment(TwAssets::Cone(), TEXT("pelvis"), FVector(0.f, 0.f, -18.f), FRotator::ZeroRotator, FVector(0.52f, 0.48f, 0.8f), Tunic);
		(void)Cape; // a rigid cape read as a flat board over the shoulder camera: tunic only
	}

	BuildBow();
	if (UStaticMesh* Cyl = TwAssets::Cylinder())
	{
		StringTop->SetStaticMesh(Cyl);
		StringBottom->SetStaticMesh(Cyl);
		NockedArrow->SetStaticMesh(Cyl);
	}
	UMaterialInstanceDynamic* StringMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (StringMat) { StringMat->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.9f, 0.7f)); StringMat->SetScalarParameterValue(TEXT("GlowMode"), 1.f); StringMat->SetScalarParameterValue(TEXT("Intensity"), 2.f); }
	StringTop->SetMaterial(0, StringMat);
	StringBottom->SetMaterial(0, StringMat);
	NockedArrow->SetMaterial(0, BodyMat);
	NockedArrow->SetVisibility(false);

	Rim->SetRelativeLocation(FVector(0, 0, 150.f * Scale));
	Rim->SetIntensity(bBel ? 4000.f : 2500.f);
	Rim->SetAttenuationRadius(600.f * Scale);
	Rim->SetLightColor(bBel ? FLinearColor(1.f, 0.2f, 0.05f) : FLinearColor(1.f, 0.7f, 0.35f));

	HeadZone->SetSphereRadius(15.f * Scale);
	TorsoZone->SetCapsuleSize(26.f * Scale, 42.f * Scale);
	LegsZone->SetCapsuleSize(22.f * Scale, 48.f * Scale);
}

void AHaykArcher::BuildBow()
{
	// recurve bow: a tube swept along a curve in the local X(forward)/Z(up) plane
	const float L = 82.f * Scale;  // half length
	const int32 Seg = 24, Sides = 6;
	TArray<FVector> V; TArray<int32> T; TArray<FVector> N; TArray<FVector2D> UV; TArray<FLinearColor> C; TArray<FProcMeshTangent> Tg;
	auto Curve = [L](float t) // t in [-1,1]
	{
		const float Z = t * L;
		const float X = 18.f * (1.f - t * t) - 6.f * FMath::Pow(FMath::Abs(t), 6.f); // belly forward, recurved tips
		return FVector(X, 0.f, Z);
	};
	for (int32 i = 0; i <= Seg; ++i)
	{
		const float t = -1.f + 2.f * i / Seg;
		const FVector P = Curve(t);
		const FVector D = (Curve(FMath::Min(1.f, t + 0.01f)) - Curve(FMath::Max(-1.f, t - 0.01f))).GetSafeNormal();
		const FVector Side = FVector::CrossProduct(D, FVector::YAxisVector).GetSafeNormal();
		const float R = (1.6f + 1.4f * (1.f - FMath::Abs(t))) * Scale;
		for (int32 s = 0; s < Sides; ++s)
		{
			const float A = 2.f * PI * s / Sides;
			const FVector Nrm = Side * FMath::Cos(A) + FVector::YAxisVector * FMath::Sin(A);
			V.Add(P + Nrm * R);
			N.Add(Nrm);
			UV.Add(FVector2D(s / float(Sides), i / float(Seg)));
			C.Add(FLinearColor::White);
			Tg.Add(FProcMeshTangent(D, false));
		}
	}
	for (int32 i = 0; i < Seg; ++i)
		for (int32 s = 0; s < Sides; ++s)
		{
			const int32 a = i * Sides + s, b = i * Sides + (s + 1) % Sides, c = a + Sides, d = b + Sides;
			T.Append({ a, c, b, b, c, d });
		}
	Bow->CreateMeshSection_LinearColor(0, V, T, N, UV, C, Tg, false);
	UMaterialInstanceDynamic* Wood = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (Wood)
	{
		Wood->SetVectorParameterValue(TEXT("SkinColor"), bBel ? FLinearColor(0.05f, 0.03f, 0.02f) : FLinearColor(0.22f, 0.1f, 0.04f));
		Wood->SetVectorParameterValue(TEXT("VeinColor"), bBel ? FLinearColor(1.f, 0.1f, 0.02f) : FLinearColor(1.f, 0.75f, 0.3f));
		Wood->SetScalarParameterValue(TEXT("VeinIntensity"), 1.5f); Wood->SetScalarParameterValue(TEXT("RimIntensity"), 0.35f); Wood->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(1.f, 0.55f, 0.25f));
		Bow->SetMaterial(0, Wood);
	}
}

FVector AHaykArcher::BowTip(bool bTop) const
{
	const float L = 82.f * Scale;
	const float t = bTop ? 1.f : -1.f;
	const FVector Local(18.f * (1.f - t * t) - 6.f, 0.f, t * L);
	return Bow->GetComponentTransform().TransformPosition(Local);
}

void AHaykArcher::SetAim(float Yaw, float Pitch)
{
	AimYaw = Yaw;
	AimPitch = FMath::Clamp(Pitch, -20.f, 70.f);
	SetActorRotation(FRotator(0.f, AimYaw, 0.f));
	if (!bAiming && Poser && !IsDead())
	{
		bAiming = true;
		Poser->SetLoop(AnimAim, 0.3f, 1.f);
	}
}

void AHaykArcher::SetDraw(float Power01)
{
	Draw = FMath::Clamp(Power01, 0.f, 1.f);
	NockedArrow->SetVisibility(Draw > 0.01f && !IsDead());
}

void AHaykArcher::Release()
{
	Draw = 0.f;
	NockedArrow->SetVisibility(false);
	if (Poser && AnimShoot) Poser->PlayOneShot(AnimShoot, 1.f, 0.05f, 0.25f, 0.7f);
	TwFx::Sound(GetWorld(), TEXT("sfx_bow_release"), GetArrowSpawn(), 1.f, bBel ? 0.8f : 1.f);
	TwFx::Sound(GetWorld(), TEXT("sfx_arrow_whoosh"), GetArrowSpawn(), 0.7f);
}

FVector AHaykArcher::GetArrowSpawn() const
{
	const FVector Hand = Body->GetBoneLocation(TEXT("hand_l"));
	return Hand + FRotator(AimPitch, AimYaw, 0.f).Vector() * 40.f * Scale;
}

FVector AHaykArcher::GetChestTarget() const { return TorsoZone->GetComponentLocation() + FVector(0, 0, 10.f * Scale); }
FVector AHaykArcher::GetHeadTarget() const { return HeadZone->GetComponentLocation(); }

void AHaykArcher::UpdateBowAndZones()
{
	const FRotator Aim(AimPitch, AimYaw, 0.f);
	const FVector HandL = Body->GetBoneLocation(TEXT("hand_l"));
	const FVector HandR = Body->GetBoneLocation(TEXT("hand_r"));
	// bow held in the left hand, its plane facing the aim direction
	Bow->SetWorldLocationAndRotation(HandL - Aim.Vector() * 6.f, Aim);
	const FVector Top = BowTip(true), Bot = BowTip(false);
	// the string is pulled back with the draw
	const FVector Nock = (Top + Bot) * 0.5f - Aim.Vector() * (6.f + Draw * 58.f * Scale);
	auto Place = [](UStaticMeshComponent* C, const FVector& A, const FVector& B, float Thick)
	{
		const FVector D = B - A;
		const float Len = D.Size();
		C->SetWorldLocation((A + B) * 0.5f);
		C->SetWorldRotation(FRotationMatrix::MakeFromZ(D / FMath::Max(Len, 1.f)).Rotator());
		C->SetWorldScale3D(FVector(Thick, Thick, Len / 100.f));
	};
	Place(StringTop, Top, Nock, 0.006f * Scale);
	Place(StringBottom, Bot, Nock, 0.006f * Scale);
	if (NockedArrow->IsVisible()) Place(NockedArrow, Nock, Nock + Aim.Vector() * 95.f * Scale, 0.012f * Scale);

	// hit zones follow the animated skeleton
	const FVector Head = Body->GetBoneLocation(TEXT("head"));
	const FVector Neck = Body->GetBoneLocation(TEXT("neck_01"));
	const FVector Pelvis = Body->GetBoneLocation(TEXT("pelvis"));
	const FVector Feet = (Body->GetBoneLocation(TEXT("foot_l")) + Body->GetBoneLocation(TEXT("foot_r"))) * 0.5f;
	HeadZone->SetWorldLocation(Head + FVector(0, 0, 8.f * Scale));
	for (int32 i = 0; i < Garments.Num(); ++i)
	{
		const FRotator Y(0.f, AimYaw, 0.f);
		Garments[i]->SetWorldLocationAndRotation(Body->GetBoneLocation(GarmentBone[i]) + Y.RotateVector(GarmentOffset[i] * Scale), FRotator(GarmentRot[i].Pitch, AimYaw + GarmentRot[i].Yaw, GarmentRot[i].Roll));
	}
	for (int32 i = 0; i < Regalia.Num(); ++i)
	{
		const FRotator Y(0.f, AimYaw, 0.f);
		Regalia[i]->SetWorldLocationAndRotation(Head + Y.RotateVector(RegaliaOffset[i] * Scale), FRotator(RegaliaRot[i].Pitch, AimYaw + RegaliaRot[i].Yaw, RegaliaRot[i].Roll));
	}
	auto PlaceCapsule = [](UCapsuleComponent* C, const FVector& A, const FVector& B)
	{
		const FVector D = B - A;
		C->SetWorldLocation((A + B) * 0.5f);
		C->SetWorldRotation(FRotationMatrix::MakeFromZ(D.GetSafeNormal()).Rotator());
		C->SetCapsuleHalfHeight(FMath::Max(C->GetUnscaledCapsuleRadius() + 1.f, D.Size() * 0.5f + C->GetUnscaledCapsuleRadius()));
	};
	PlaceCapsule(TorsoZone, Pelvis + FVector(0, 0, 8.f * Scale), Neck);
	PlaceCapsule(LegsZone, Feet, Pelvis);

	// lean a bit with the pitch so aiming up/down reads on the body
	Body->SetRelativeRotation(FRotator(0.f, -90.f, FMath::Clamp(AimPitch * 0.25f, -6.f, 14.f)));
}

void AHaykArcher::Tick(float Dt)
{
	Super::Tick(Dt);
	UpdateBowAndZones();
	HurtFlash = FMath::Max(0.f, HurtFlash - Dt * 2.f);
	if (BodyMat) BodyMat->SetScalarParameterValue(TEXT("HitFlash"), HurtFlash * 0.45f);
	for (UMaterialInstanceDynamic* D : HumanMats) if (D) D->SetScalarParameterValue(TEXT("HitFlash"), HurtFlash * 0.45f);
}

EArcherZone AHaykArcher::ZoneOf(const UPrimitiveComponent* C) const
{
	if (C == HeadZone) return EArcherZone::Head;
	if (C == TorsoZone) return EArcherZone::Torso;
	if (C == LegsZone) return EArcherZone::Legs;
	return EArcherZone::None;
}

float AHaykArcher::ApplyHit(EArcherZone Zone, bool bSpecial, const FVector& Where)
{
	if (IsDead() || Zone == EArcherZone::None) return 0.f;
	if (bShielded)
	{
		// the shield wall of his bodyguards takes the arrow
		TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, Where, 0.8f);
		TwFx::Sound(GetWorld(), TEXT("sfx_arrow_hit_wood"), Where, 1.f, 0.8f);
		return 0.f;
	}
	float D = Zone == EArcherZone::Head ? 40.f : (Zone == EArcherZone::Torso ? 22.f : 12.f);
	if (bSpecial) D *= 1.8f;
	Health = FMath::Max(0.f, Health - D);
	HurtFlash = 1.f;
	// a full fireball hid the stuck arrow and the hit reaction: sparks for normal hits, fire for the big ones
	if (bSpecial || Health <= 0.f) TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, Where, 1.6f);
	else TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, Where, 1.0f);
	TwFx::LightFlash(GetWorld(), Where, FLinearColor(1.f, 0.45f, 0.1f), 30000.f, 1600.f, 0.35f);
	TwFx::Sound(GetWorld(), TEXT("sfx_vishap_hit"), Where, 1.f, bBel ? 0.7f : 1.1f);
	if (Health <= 0.f)
	{
		if (Poser) Poser->SetLoop(AnimDeath, 0.15f, 1.f, false);
		NockedArrow->SetVisibility(false);
		TwFx::Sound(GetWorld(), TEXT("sfx_vishap_death"), Where, 1.f, bBel ? 0.6f : 1.2f);
	}
	else if (Poser)
	{
		Poser->PlayOneShot(D >= 30.f ? AnimHitHeavy : AnimHit, 1.f, 0.05f, 0.25f, 0.9f);
	}
	return D;
}

void AHaykArcher::Celebrate()
{
	bAiming = false;
	if (Poser) { Poser->SetLoop(AnimIdle, 0.3f); Poser->PlayOneShot(AnimCheer, 0.9f, 0.1f, 0.4f, 1.f); }
}
