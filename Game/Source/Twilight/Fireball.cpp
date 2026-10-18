#include "Fireball.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "Vishap.h"
#include "VahagnCharacter.h"

#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "GameFramework/ProjectileMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "EngineUtils.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraComponent.h"

AFireball::AFireball()
{
	PrimaryActorTick.bCanEverTick = true;

	Sphere = CreateDefaultSubobject<USphereComponent>(TEXT("Sphere"));
	Sphere->InitSphereRadius(38.f);
	Sphere->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Sphere->SetCollisionObjectType(ECC_WorldDynamic);
	Sphere->SetCollisionResponseToAllChannels(ECR_Ignore);
	Sphere->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);
	Sphere->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Overlap);
	Sphere->SetCollisionResponseToChannel(ECC_PhysicsBody, ECR_Block);
	Sphere->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Sphere->SetGenerateOverlapEvents(true);
	Sphere->bReturnMaterialOnMove = false;
	RootComponent = Sphere;

	Core = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Core"));
	Core->SetupAttachment(Sphere);
	Core->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Core->SetCastShadow(false);
	Core->SetRelativeScale3D(FVector(0.45f));

	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Sphere);
	Light->SetIntensityUnits(ELightUnits::Unitless);
	Light->SetIntensity(5000.f);
	Light->SetAttenuationRadius(900.f);
	Light->SetLightColor(FLinearColor(1.f, 0.45f, 0.12f));
	Light->SetCastShadows(false);

	Move = CreateDefaultSubobject<UProjectileMovementComponent>(TEXT("Move"));
	Move->UpdatedComponent = Sphere;
	Move->InitialSpeed = Speed;
	Move->MaxSpeed = Speed * 1.5f;
	Move->ProjectileGravityScale = 0.f;
	Move->bRotationFollowsVelocity = true;
	Move->bSweepCollision = true;
	Move->bAutoActivate = false;

	InitialLifeSpan = 2.4f;
}

void AFireball::Launch(const FVector& Dir, float InDamage, float InAoe, float Scale, bool bInHostile, float SpeedOverride)
{
	Damage = InDamage;
	Aoe = InAoe;
	VisualScale = Scale;
	bHostile = bInHostile;

	if (AActor* O = GetOwner())
	{
		Sphere->IgnoreActorWhenMoving(O, true);
	}
	Sphere->SetSphereRadius(38.f * FMath::Max(1.f, Scale * 0.8f));
	Sphere->OnComponentBeginOverlap.AddDynamic(this, &AFireball::OnOverlap);
	Sphere->OnComponentHit.AddDynamic(this, &AFireball::OnHit);

	if (UStaticMesh* S = TwAssets::Sphere()) Core->SetStaticMesh(S);
	const FLinearColor Col = bHostile ? FLinearColor(1.f, 0.11f, 0.03f) : FLinearColor(1.f, 0.62f, 0.2f);
	const bool bBigShot = Scale > 1.2f || bHostile;
	CoreMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (CoreMat)
	{
		CoreMat->SetVectorParameterValue(TEXT("Color"), Col);
		// big shots: a saturated shell with soft edges (high intensity tonemaps to a flat cream disc)
		CoreMat->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		CoreMat->SetScalarParameterValue(TEXT("Intensity"), bBigShot ? (bHostile ? 5.f : 7.f) : 12.f);
		if (bBigShot) CoreMat->SetScalarParameterValue(TEXT("Falloff"), 3.f);
		Core->SetMaterial(0, CoreMat);
	}
	Core->SetRelativeScale3D(FVector(0.42f * Scale));
	if (bBigShot)
	{
		// small white-hot heart inside the shell
		InnerCore = NewObject<UStaticMeshComponent>(this);
		InnerCore->SetStaticMesh(TwAssets::Sphere());
		InnerCore->SetupAttachment(Core);
		InnerCore->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		InnerCore->SetCastShadow(false);
		InnerCore->SetRelativeScale3D(FVector(0.42f));
		if (UMaterialInstanceDynamic* HM = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
		{
			HM->SetVectorParameterValue(TEXT("Color"), bHostile ? FLinearColor(1.f, 0.55f, 0.25f) : FLinearColor(1.f, 0.85f, 0.55f));
			HM->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
			HM->SetScalarParameterValue(TEXT("Intensity"), 14.f);
			InnerCore->SetMaterial(0, HM);
		}
		InnerCore->RegisterComponent();
	}
	Light->SetLightColor(Col);
	Light->SetIntensity(4500.f * Scale);
	Light->SetAttenuationRadius(800.f * FMath::Sqrt(Scale));

	// heavy particle systems only on big/hostile shots; normal shots use the glowing core + comet tail (cheap on an iGPU)
	const bool bBig = Scale > 1.2f || bHostile;
	if (bBig)
	{
		Flame = TwFx::AttachFlame(Sphere, NAME_None, FVector::ZeroVector, 0.35f * Scale);
		Trail = TwFx::AttachSparks(Sphere, NAME_None, FVector::ZeroVector, 0.45f * Scale);
	}
	else
	{
		Light->SetVisibility(false);
	}
	for (int32 i = 0; i < 3; ++i)
	{
		UStaticMeshComponent* T = NewObject<UStaticMeshComponent>(this);
		T->SetStaticMesh(TwAssets::Sphere());
		T->SetupAttachment(Sphere);
		T->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		T->SetCastShadow(false);
		T->SetMaterial(0, CoreMat);
		const float K = 1.f - (i + 1) / 4.f;
		T->SetRelativeLocation(FVector(-(i + 1) * 46.f * Scale, 0.f, 0.f));
		T->SetRelativeScale3D(FVector(0.62f * K, 0.34f * K, 0.34f * K) * Scale);
		T->RegisterComponent();
		Tail.Add(T);
	}

	const float Spd = SpeedOverride > 0.f ? SpeedOverride : Speed;
	Move->InitialSpeed = Spd;
	Move->MaxSpeed = Spd;
	Move->Velocity = Dir.GetSafeNormal() * Spd;
	Move->Activate(true);

	// overlaps that already existed at spawn time fired before the delegate was bound
	TArray<UPrimitiveComponent*> Already;
	Sphere->GetOverlappingComponents(Already);
	for (UPrimitiveComponent* C : Already)
	{
		if (bDone) break;
		if (C) OnOverlap(Sphere, C->GetOwner(), C, INDEX_NONE, false, FHitResult());
	}
}

void AFireball::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt;
	if (bDone) return;
	// pulse
	const float P = 1.f + 0.12f * FMath::Sin(Age * 40.f);
	Core->SetRelativeScale3D(FVector(0.42f * VisualScale * P));
	// into the sea -> hiss + splash
	if (GetActorLocation().Z < 30.f)
	{
		TwFx::Burst(GetWorld(), TwFx::EFx::Splash, FVector(GetActorLocation().X, GetActorLocation().Y, 10.f), 0.8f * VisualScale);
		Explode(GetActorLocation(), nullptr, nullptr);
	}
}

void AFireball::OnOverlap(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Sweep)
{
	if (bDone || !Other || Other == GetOwner()) return;
	if (bHostile)
	{
		if (Other->IsA<AVahagnCharacter>()) Explode(GetActorLocation(), Other, OtherComp);
	}
	else
	{
		if (Other->IsA<AVishap>()) Explode(bFromSweep ? FVector(Sweep.ImpactPoint) : GetActorLocation(), Other, OtherComp);
	}
}

void AFireball::OnHit(UPrimitiveComponent* Comp, AActor* Other, UPrimitiveComponent* OtherComp, FVector Impulse, const FHitResult& Hit)
{
	if (bDone) return;
	if (!bHostile && Other && Other->IsA<AVishap>()) { Explode(Hit.ImpactPoint, Other, OtherComp); return; }
	if (bHostile && Other && Other->IsA<AVishap>()) return; // vishap spit never collides with its own kind
	Explode(Hit.ImpactPoint, nullptr, nullptr);
}

void AFireball::Explode(const FVector& Where, AActor* DirectActor, UPrimitiveComponent* DirectComp)
{
	if (bDone) return;
	bDone = true;
	AActor* Inst = GetOwner();

	if (bHostile)
	{
		if (DirectActor) UGameplayStatics::ApplyDamage(DirectActor, Damage, Inst ? Inst->GetInstigatorController() : nullptr, this, nullptr);
		TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, Where, 0.9f * VisualScale);
		TwFx::Sound(GetWorld(), TEXT("sfx_fireball_impact"), Where, 0.7f, 0.8f);
	}
	else
	{
		AVahagnCharacter* Hero = Cast<AVahagnCharacter>(Inst);
		if (AVishap* V = Cast<AVishap>(DirectActor))
		{
			V->ApplyHitAtComponent(Damage, Where, DirectComp, Hero);
		}
		if (Aoe > 0.f)
		{
			for (TActorIterator<AVishap> It(GetWorld()); It; ++It)
			{
				if (*It == DirectActor || !It->IsAlive()) continue;
				const float D = It->DistanceToPoint(Where);
				if (D < Aoe) It->ApplyHit(Damage * (1.f - 0.6f * D / Aoe), Where, Hero, true);
			}
			TwFx::Burst(GetWorld(), TwFx::EFx::BigExplosion, Where, 0.8f + Aoe / 900.f);
			TwFx::LightFlash(GetWorld(), Where, FLinearColor(1.f, 0.5f, 0.15f), 60000.f, Aoe * 3.f, 0.4f);
			TwFx::Sound(GetWorld(), TEXT("sfx_big_explosion"), Where, 1.f);
			if (Hero) Hero->AddShake(FMath::Clamp(1.f - FVector::Dist(Hero->GetActorLocation(), Where) / 5000.f, 0.f, 0.6f));
		}
		else
		{
			TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, Where, 0.7f * VisualScale);
			TwFx::LightFlash(GetWorld(), Where, FLinearColor(1.f, 0.5f, 0.15f), 15000.f, 1200.f, 0.2f);
			TwFx::Sound(GetWorld(), TEXT("sfx_fireball_impact"), Where, 0.6f, FMath::FRandRange(0.9f, 1.15f));
		}
	}

	// stop, hide the core, let trailing particles die out naturally
	Move->StopMovementImmediately();
	Move->Deactivate();
	Sphere->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Core->SetVisibility(false, true);
	Light->SetVisibility(false);
	for (UStaticMeshComponent* T : Tail) if (T) T->SetVisibility(false);
	if (Flame) Flame->Deactivate();
	if (Trail) Trail->Deactivate();
	SetLifeSpan(1.5f);
}
