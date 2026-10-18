#include "HaykArrow.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "HaykArcher.h"
#include "HaykShield.h"

#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"

static constexpr int32 TrailCount = 48;

AHaykArrow::AHaykArrow()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	Shaft = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Shaft"));
	Shaft->SetupAttachment(Root);
	Shaft->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Tip = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Tip"));
	Tip->SetupAttachment(Root);
	Tip->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	TrailDots = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Trail"));
	TrailDots->SetupAttachment(Root);
	TrailDots->SetAbsolute(true, true, true);
	TrailDots->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	TrailDots->SetCastShadow(false);
	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Root);
	Light->SetIntensityUnits(ELightUnits::Unitless);
	Light->SetCastShadows(false);
	InitialLifeSpan = 30.f;
}

void AHaykArrow::Launch(AHaykArcher* InShooter, const FVector& Dir, float Power01, const FVector& InWind, bool bInSpecial)
{
	Shooter = InShooter;
	bSpecial = bInSpecial;
	Wind = InWind;
	Vel = Dir.GetSafeNormal() * MaxSpeed * FMath::Clamp(Power01, 0.2f, 1.f);

	UStaticMesh* Cyl = TwAssets::Cylinder();
	UStaticMesh* Cone = TwAssets::Cone();
	UStaticMesh* Cube = TwAssets::Cube();
	const float S = InShooter && InShooter->IsBel() ? 1.45f : 1.f;

	UMaterialInstanceDynamic* Wood = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (Wood) { Wood->SetVectorParameterValue(TEXT("SkinColor"), FLinearColor(0.25f, 0.12f, 0.05f)); Wood->SetScalarParameterValue(TEXT("VeinIntensity"), 0.5f); Wood->SetScalarParameterValue(TEXT("RimIntensity"), 0.35f); Wood->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(1.f, 0.55f, 0.25f)); }
	UMaterialInstanceDynamic* Glow = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	const FLinearColor GlowCol = bSpecial ? FLinearColor(1.f, 0.82f, 0.35f) : (InShooter && InShooter->IsBel() ? FLinearColor(1.f, 0.2f, 0.05f) : FLinearColor(1.f, 0.55f, 0.2f));
	if (Glow) { Glow->SetVectorParameterValue(TEXT("Color"), GlowCol); Glow->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Glow->SetScalarParameterValue(TEXT("Intensity"), bSpecial ? 30.f : 10.f); }

	// shaft along local X: cylinder is 100 cm along Z, so pitch it 90°
	Shaft->SetStaticMesh(Cyl);
	Shaft->SetRelativeRotation(FRotator(-90.f, 0.f, 0.f));
	Shaft->SetRelativeLocation(FVector(-45.f * S, 0, 0));
	Shaft->SetRelativeScale3D(FVector(0.025f * S, 0.025f * S, 1.0f * S));
	Shaft->SetMaterial(0, Wood);
	Tip->SetStaticMesh(Cone);
	Tip->SetRelativeRotation(FRotator(-90.f, 0.f, 0.f));
	Tip->SetRelativeLocation(FVector(8.f * S, 0, 0));
	Tip->SetRelativeScale3D(FVector(0.06f * S, 0.06f * S, 0.16f * S));
	Tip->SetMaterial(0, Glow);
	// the three feathers
	for (int32 i = 0; i < 3; ++i)
	{
		UStaticMeshComponent* F = NewObject<UStaticMeshComponent>(this);
		F->SetStaticMesh(Cube);
		F->SetupAttachment(Root);
		F->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		F->SetRelativeLocation(FVector(-88.f * S, 0, 0) + FRotator(0, 0, i * 120.f).RotateVector(FVector(0, 0, 3.5f * S)));
		F->SetRelativeRotation(FRotator(0, 0, i * 120.f));
		F->SetRelativeScale3D(FVector(0.16f * S, 0.004f * S, 0.05f * S));
		F->SetMaterial(0, Glow);
		F->RegisterComponent();
		Feathers.Add(F);
	}

	TrailDots->SetStaticMesh(TwAssets::Sphere());
	UMaterialInstanceDynamic* TM = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (TM) { TM->SetVectorParameterValue(TEXT("Color"), GlowCol); TM->SetScalarParameterValue(TEXT("GlowMode"), 1.f); TM->SetScalarParameterValue(TEXT("Intensity"), bSpecial ? 14.f : 5.f); }
	TrailDots->SetMaterial(0, TM);
	TArray<FTransform> Init;
	for (int32 i = 0; i < TrailCount; ++i) Init.Add(FTransform(FRotator::ZeroRotator, GetActorLocation(), FVector(0.001f)));
	TrailDots->AddInstances(Init, false, true);
	TrailBirth.Init(-100.f, TrailCount);

	Light->SetLightColor(GlowCol);
	Light->SetIntensity(bSpecial ? 9000.f : 2500.f);
	Light->SetAttenuationRadius(bSpecial ? 1200.f : 500.f);
	SetActorRotation(Vel.Rotation());
}

float AHaykArrow::TimeToReach(const FVector& Point) const
{
	const float D = FVector::Dist(GetActorLocation(), Point);
	return D / FMath::Max(Vel.Size(), 1.f);
}

float AHaykArrow::SimulateMiss(UWorld* World, const FVector& Start, const FVector& Vel0, const FVector& InWind, const FVector& Target, float& OutT, const AActor* Ignore)
{
	FVector P = Start, V = Vel0;
	float Best = TNumericLimits<float>::Max();
	OutT = 0.f;
	const float Dt = 1.f / 60.f;
	for (int32 i = 0; i < 60 * 5; ++i)
	{
		V += (FVector(0, 0, -Gravity) + InWind * WindK) * Dt;
		const FVector N = P + V * Dt;
		// closest point of the segment to the target
		const FVector Cp = FMath::ClosestPointOnSegment(Target, P, N);
		const float D = FVector::Dist(Cp, Target);
		if (D < Best) { Best = D; OutT = i * Dt; }
		P = N;
		if (P.Z < -2000.f) break;
		if (D > Best + 3000.f) break; // moving away
	}
	return Best;
}

void AHaykArrow::Tick(float Dt)
{
	Super::Tick(Dt);
	const float Now = GetWorld()->GetTimeSeconds();

	if (Result == EArrowResult::Flying)
	{
		Age += Dt;
		FVector Acc(0, 0, -Gravity);
		Acc += Wind * WindK;
		if (bSpecial && !SteerInput.IsNearlyZero())
		{
			const FVector Fwd = Vel.GetSafeNormal();
			const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
			const FVector Up = FVector::CrossProduct(Fwd, Right).GetSafeNormal();
			Acc += (Right * SteerInput.X + Up * SteerInput.Y) * 2600.f;
		}
		SteerInput = FVector2D::ZeroVector; // one frame of input; held input re-sends every frame
		Vel += Acc * Dt;
		const FVector P0 = GetActorLocation();
		const FVector P1 = P0 + Vel * Dt;

		FCollisionQueryParams Q(SCENE_QUERY_STAT(HaykArrow), true, this);
		if (Shooter.IsValid() && Age < 0.25f) Q.AddIgnoredActor(Shooter.Get());
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, P0, P1 + Vel.GetSafeNormal() * 40.f, ECC_Visibility, Q))
		{
			SetActorLocation(Hit.ImpactPoint - Vel.GetSafeNormal() * 30.f);
			Resolve(Hit);
		}
		else
		{
			SetActorLocationAndRotation(P1, Vel.Rotation());
			if (P1.Z < -3000.f || Age > 12.f) { Result = EArrowResult::Lost; Impact = P1; }
		}

		// trail
		TrailTimer -= Dt;
		if (TrailTimer <= 0.f)
		{
			TrailTimer = 0.016f;
			TrailBirth[TrailNext] = Now;
			TrailDots->UpdateInstanceTransform(TrailNext, FTransform(FRotator::ZeroRotator, P0, FVector(bSpecial ? 0.09f : 0.05f)), true, false, true);
			TrailNext = (TrailNext + 1) % TrailCount;
		}
	}
	// fade the trail
	for (int32 i = 0; i < TrailCount; ++i)
	{
		const float A = Now - TrailBirth[i];
		if (A < 0.f || A > 1.2f) continue;
		FTransform T;
		TrailDots->GetInstanceTransform(i, T, true);
		T.SetScale3D(FVector((bSpecial ? 0.09f : 0.05f) * (1.f - A / 1.2f) + 0.001f));
		TrailDots->UpdateInstanceTransform(i, T, true, false, true);
	}
	TrailDots->MarkRenderStateDirty();
}

void AHaykArrow::Resolve(const FHitResult& Hit)
{
	Impact = Hit.ImpactPoint;
	AActor* Other = Hit.GetActor();
	if (AHaykArcher* A = Cast<AHaykArcher>(Other))
	{
		const EArcherZone Z = A->ZoneOf(Hit.GetComponent());
		DamageDealt = A->ApplyHit(Z, bSpecial, Impact);
		bHeadshot = Z == EArcherZone::Head;
		HitArcher = A;
		Result = EArrowResult::HitArcher;
		// stick into the body
		{
			USkeletalMeshComponent* BodyMesh = A->GetBody();
			const FName Bones[6] = { TEXT("head"), TEXT("spine_03"), TEXT("spine_01"), TEXT("pelvis"), TEXT("thigh_l"), TEXT("thigh_r") };
			FName Best = NAME_None; float BestD = TNumericLimits<float>::Max();
			for (const FName& B : Bones)
			{
				const float D = FVector::DistSquared(BodyMesh->GetBoneLocation(B), Impact);
				if (D < BestD) { BestD = D; Best = B; }
			}
			AttachToComponent(BodyMesh, FAttachmentTransformRules::KeepWorldTransform, Best);
		}
		TwFx::Sound(GetWorld(), TEXT("sfx_arrow_hit_flesh"), Impact, 1.f);
		TwFx::LightFlash(GetWorld(), Impact, FLinearColor(1.f, 0.4f, 0.1f), bSpecial ? 80000.f : 25000.f, 900.f, 0.4f);
	}
	else if (AHaykShield* S = Cast<AHaykShield>(Other))
	{
		S->TakeArrow(Impact, bSpecial);
		Result = EArrowResult::HitShield;
		AttachToActor(S, FAttachmentTransformRules::KeepWorldTransform);
		TwFx::Sound(GetWorld(), TEXT("sfx_arrow_hit_wood"), Impact, 1.f);
	}
	else
	{
		Result = EArrowResult::HitGround;
		TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, Impact, 0.6f);
		TwFx::Sound(GetWorld(), TEXT("sfx_arrow_hit_ground"), Impact, 0.9f);
	}
	if (bSpecial) TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, Impact, 1.2f);
	Light->SetIntensity(Light->Intensity * 0.3f);
	SetLifeSpan(25.f);
}
