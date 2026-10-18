#include "VahagnCharacter.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "TwPoseAnimInstance.h"
#include "Fireball.h"
#include "Vishap.h"
#include "VahagnGameMode.h"

#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Animation/AnimSequence.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputActionValue.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"

static const FName SockHandR(TEXT("hand_r"));
static const FName SockHandL(TEXT("hand_l"));

AVahagnCharacter::AVahagnCharacter()
{
	PrimaryActorTick.bCanEverTick = true;

	GetCapsuleComponent()->InitCapsuleSize(40.f, 92.f);
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	bUseControllerRotationYaw = false;
	bUseControllerRotationPitch = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* M = GetCharacterMovement();
	M->DefaultLandMovementMode = MOVE_Flying;
	M->DefaultWaterMovementMode = MOVE_Flying;
	M->MaxFlySpeed = 2700.f;
	M->MaxAcceleration = 7000.f;
	M->BrakingDecelerationFlying = 3200.f;
	M->bOrientRotationToMovement = false;
	M->GravityScale = 0.f;
	M->bUseSeparateBrakingFriction = true;
	M->BrakingFriction = 1.5f;

	// Mesh hangs from a pivot at the body centre so we can lean the whole body for "superhero" flight.
	USceneComponent* Pivot = CreateDefaultSubobject<USceneComponent>(TEXT("BodyPivot"));
	Pivot->SetupAttachment(GetCapsuleComponent());
	GetMesh()->SetupAttachment(Pivot);
	GetMesh()->SetRelativeLocationAndRotation(FVector(0, 0, -92.f), FRotator(0, -90.f, 0));
	GetMesh()->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GetMesh()->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;

	Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("Boom"));
	Boom->SetupAttachment(GetCapsuleComponent());
	Boom->TargetArmLength = 560.f;
	Boom->SocketOffset = FVector(0, 85.f, 110.f);
	Boom->bUsePawnControlRotation = true;
	Boom->bEnableCameraLag = true;
	Boom->CameraLagSpeed = 9.f;
	Boom->CameraLagMaxDistance = 320.f;
	Boom->bDoCollisionTest = true;
	Boom->ProbeSize = 16.f;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Boom, USpringArmComponent::SocketName);
	Camera->SetFieldOfView(BaseFov);
	Camera->PostProcessBlendWeight = 1.f;

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Pivot);
	Glow->SetRelativeLocation(FVector(0, 0, 20.f));
	Glow->SetIntensityUnits(ELightUnits::Unitless);
	Glow->SetIntensity(9000.f);
	Glow->SetLightColor(FLinearColor(1.f, 0.42f, 0.12f));
	Glow->SetAttenuationRadius(1500.f);
	Glow->SetCastShadows(false);

	FlameLoop = CreateDefaultSubobject<UAudioComponent>(TEXT("FlameLoop"));
	FlameLoop->SetupAttachment(GetCapsuleComponent());
	FlameLoop->bAutoActivate = false;
	FireTrail = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("FireTrail"));
	FireTrail->SetupAttachment(GetCapsuleComponent());
	FireTrail->SetAbsolute(true, true, true);
	FireTrail->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	FireTrail->SetCastShadow(false);
	WindLoop = CreateDefaultSubobject<UAudioComponent>(TEXT("WindLoop"));
	WindLoop->SetupAttachment(GetCapsuleComponent());
	WindLoop->bAutoActivate = false;
}

void AVahagnCharacter::BeginPlay()
{
	Super::BeginPlay();

	GetCharacterMovement()->SetMovementMode(MOVE_Flying);

	if (USkeletalMesh* Manny = TwAssets::Manny())
	{
		GetMesh()->SetSkeletalMesh(Manny);
	}
	GetMesh()->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	GetMesh()->SetAnimInstanceClass(UTwPoseAnimInstance::StaticClass());
	Poser = Cast<UTwPoseAnimInstance>(GetMesh()->GetAnimInstance());

	AnimHover = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle"));
	AnimFly = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop.MM_Fall_Loop"));
	AnimCastA = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01.MM_Attack_01"));
	AnimCastB = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02.MM_Attack_02"));
	AnimNova = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_ChargedAttack.MM_ChargedAttack"));
	AnimHit = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Lgt_01.MM_HitReact_Front_Lgt_01"));
	AnimDeath = TwAssets::Anim(TEXT("/Game/Characters/Mannequins/Anims/Death/MM_Death_Front_01.MM_Death_Front_01"));
	if (Poser) Poser->SetLoop(AnimHover, 0.01f, 1.f);

	// Molten fire body
	BodyMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_FireBody")), this);
	if (BodyMat)
	{
		BodyMat->SetScalarParameterValue(TEXT("EmissiveIntensity"), 2.6f);
		BodyMat->SetScalarParameterValue(TEXT("RimIntensity"), 1.6f);
		BodyMat->SetScalarParameterValue(TEXT("AmbientFill"), 0.6f);
		for (int32 i = 0; i < GetMesh()->GetNumMaterials(); ++i) GetMesh()->SetMaterial(i, BodyMat);
	}

	// Flames on hands, head and chest; embers trailing from the pelvis
	Auras.Add(TwFx::AttachFlame(GetMesh(), SockHandR, FVector::ZeroVector, 0.35f));
	Auras.Add(TwFx::AttachFlame(GetMesh(), SockHandL, FVector::ZeroVector, 0.35f));
	Auras.Add(TwFx::AttachFlame(GetMesh(), TEXT("head"), FVector(0, 8, 0), 0.55f));
	Auras.Add(TwFx::AttachFlame(GetMesh(), TEXT("spine_03"), FVector::ZeroVector, 0.45f));
	Auras.Add(TwFx::AttachSparks(GetMesh(), TEXT("pelvis"), FVector::ZeroVector, 0.6f));
	Auras.RemoveAll([](const TObjectPtr<UFXSystemComponent>& C) { return C == nullptr; });

	if (USoundBase* S = TwAssets::Sound(TEXT("sfx_flame_aura_loop"))) { FlameLoop->SetSound(S); FlameLoop->SetVolumeMultiplier(0.35f); FlameLoop->Play(); }
	if (USoundBase* S = TwAssets::Sound(TEXT("sfx_wind_loop"))) { WindLoop->SetSound(S); WindLoop->SetVolumeMultiplier(0.f); WindLoop->Play(); }

	// fire trail: recycled glowing embers left behind while flying fast
	FireTrail->SetStaticMesh(TwAssets::Sphere());
	if (UMaterialInstanceDynamic* TM = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
	{
		TM->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.45f, 0.12f));
		TM->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		TM->SetScalarParameterValue(TEXT("Intensity"), 8.f);
		FireTrail->SetMaterial(0, TM);
	}
	{
		TArray<FTransform> Init;
		for (int32 i = 0; i < 48; ++i) Init.Add(FTransform(FRotator::ZeroRotator, GetActorLocation(), FVector(0.001f)));
		FireTrail->AddInstances(Init, false, true);
		TrailBirth.Init(-100.f, 48);
	}
	LastYaw = GetActorRotation().Yaw;
	AimPoint = GetActorLocation() + GetActorForwardVector() * 10000.f;
}

// ---------------------------------------------------------------- input
void AVahagnCharacter::SetupPlayerInputComponent(UInputComponent* Input)
{
	Super::SetupPlayerInputComponent(Input);
	// Bindings are created by AVahagnPlayerController (it owns the runtime-built input actions).
}

void AVahagnCharacter::InMove(const FInputActionValue& V) { MoveInput = bControl ? V.Get<FVector2D>() : FVector2D::ZeroVector; }
void AVahagnCharacter::InUpDown(const FInputActionValue& V) { UpInput = bControl ? V.Get<float>() : 0.f; }
void AVahagnCharacter::InLook(const FInputActionValue& V)
{
	if (!bControl || bAutopilot) return;
	const FVector2D L = V.Get<FVector2D>();
	AddControllerYawInput(L.X);
	AddControllerPitchInput(L.Y);
}
void AVahagnCharacter::InFireStart() { if (bControl) bFireHeld = true; }
void AVahagnCharacter::InFireStop() { bFireHeld = false; }
void AVahagnCharacter::InChargeStart() { if (bControl && !bDead) { bChargeHeld = true; Charge = 0.f; } }
void AVahagnCharacter::InChargeRelease()
{
	if (!bChargeHeld) return;
	bChargeHeld = false;
	if (bControl && !bDead) FireCharged();
	Charge = 0.f;
}
void AVahagnCharacter::InBoostStart() { if (bControl) bBoosting = BoostEnergy > 8.f; }
void AVahagnCharacter::InBoostStop() { bBoosting = false; }

void AVahagnCharacter::SetMenuFraming(bool bMenu)
{
	Boom->SocketOffset = bMenu ? FVector(0.f, -330.f, 60.f) : FVector(0, 85.f, 110.f);
	Boom->TargetArmLength = bMenu ? 640.f : 560.f;
}

void AVahagnCharacter::SetControlEnabled(bool bEnabled)
{
	bControl = bEnabled;
	if (!bEnabled) { MoveInput = FVector2D::ZeroVector; UpInput = 0.f; bFireHeld = false; bChargeHeld = false; bBoosting = false; Charge = 0.f; }
}

// ---------------------------------------------------------------- tick
void AVahagnCharacter::BeginBirth(const FVector& ReedTop, float Duration)
{
	BirthDur = FMath::Max(0.5f, Duration);
	BirthLeft = BirthDur;
	BirthStage = 0;
	BirthFrom = ReedTop - FVector(0, 0, 900.f);
	BirthTo = ReedTop + FVector(0, 0, 2200.f);
	SetActorLocation(BirthFrom);
	GetCharacterMovement()->StopMovementImmediately();
	SetControlEnabled(false);
	if (AController* C = GetController()) C->SetControlRotation(FRotator(-12.f, 205.f, 0.f));
	if (Poser) Poser->SetLoop(AnimFly, 0.1f, 0.4f);
	bFlyPose = true;
}

void AVahagnCharacter::Tick(float Dt)
{
	Super::Tick(Dt);
	if (BirthLeft > 0.f)
	{
		BirthLeft -= Dt;
		const float A = FMath::Clamp(1.f - BirthLeft / BirthDur, 0.f, 1.f);
		const float E = A < 0.35f ? 0.f : FMath::InterpEaseOut(0.f, 1.f, (A - 0.35f) / 0.65f, 2.5f);
		SetActorLocation(FMath::Lerp(BirthFrom, BirthTo, E));
		// smoke from the reed, then flame, then the fire-youth bursts out of the sea
		const FVector Reed = BirthFrom + FVector(0, 0, 900.f);
		if (BirthStage == 0 && A > 0.02f) { BirthStage = 1; TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, Reed, 3.f); TwFx::Sound2D(GetWorld(), TEXT("sfx_fire_breath"), 0.9f, 0.7f); }
		if (BirthStage == 1 && A > 0.22f) { BirthStage = 2; TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, Reed, 2.5f); TwFx::LightFlash(GetWorld(), Reed, FLinearColor(1.f, 0.4f, 0.1f), 120000.f, 6000.f, 1.f); }
		if (BirthStage == 2 && A > 0.36f) { BirthStage = 3; TwFx::Burst(GetWorld(), TwFx::EFx::BigExplosion, Reed, 4.f); TwFx::Burst(GetWorld(), TwFx::EFx::Splash, FVector(Reed.X, Reed.Y, 10.f), 5.f); TwFx::Sound2D(GetWorld(), TEXT("sfx_special_nova"), 1.f, 0.8f); }
		if (BirthLeft <= 0.f) { BirthLeft = 0.f; if (Poser) Poser->SetLoop(AnimHover, 0.5f); bFlyPose = false; }
		UpdateVisuals(Dt);
		return;
	}
	if (bAutopilot && !bDead) UpdateAutopilot(Dt);
	if (!bDead)
	{
		UpdateFlight(Dt);
		UpdateAim(Dt);

		// fire
		FireCooldown -= Dt;
		if (bFireHeld && !bChargeHeld && FireCooldown <= 0.f) FireOnce();
		if (bChargeHeld) Charge = FMath::Min(1.f, Charge + Dt / 0.9f);

		// regen
		const float Now = GetWorld()->GetTimeSeconds();
		if (Now - LastDamageTime > 3.f) Health = FMath::Min(MaxHealth, Health + 6.f * Dt);
	}
	UpdateVisuals(Dt);
	DamageFlash = FMath::Max(0.f, DamageFlash - Dt * 2.2f);
	HitMarker = FMath::Max(0.f, HitMarker - Dt * 5.f);
}

void AVahagnCharacter::UpdateFlight(float Dt)
{
	UCharacterMovementComponent* M = GetCharacterMovement();
	if (M->MovementMode != MOVE_Flying) M->SetMovementMode(MOVE_Flying);

	// boost energy
	if (bBoosting && MoveInput.Size() > 0.1f) BoostEnergy = FMath::Max(0.f, BoostEnergy - 24.f * Dt);
	else BoostEnergy = FMath::Min(100.f, BoostEnergy + 16.f * Dt);
	if (BoostEnergy <= 0.f) bBoosting = false;

	M->MaxFlySpeed = FMath::FInterpTo(M->MaxFlySpeed, bBoosting ? 5600.f : 2700.f, Dt, 4.f);
	M->MaxAcceleration = bBoosting ? 11000.f : 7000.f;

	const FRotator Ctrl = GetControlRotation();
	const FVector Fwd = Ctrl.Vector();
	const FVector Right = FRotationMatrix(FRotator(0, Ctrl.Yaw, 0)).GetUnitAxis(EAxis::Y);
	FVector Wish = Fwd * MoveInput.Y + Right * MoveInput.X + FVector::UpVector * UpInput;

	const FVector Loc = GetActorLocation();
	// soft arena bounds: steer back smoothly, never a hard wall
	const float D = FVector2D(Loc.X, Loc.Y).Size();
	const float Soft = ArenaRadius * 0.88f;
	if (D > Soft)
	{
		const FVector In = FVector(-Loc.X, -Loc.Y, 0.f).GetSafeNormal();
		const float K = FMath::Clamp((D - Soft) / (ArenaRadius - Soft), 0.f, 1.5f);
		Wish += In * K * 2.f;
		FVector V = M->Velocity;
		const float Out = FVector::DotProduct(V, -In);
		if (Out > 0.f) { V += In * Out * FMath::Clamp(K, 0.f, 1.f) * Dt * 4.f; M->Velocity = V; }
		if (D > ArenaRadius)
		{
			const FVector Clamped = FVector(Loc.X / D * ArenaRadius, Loc.Y / D * ArenaRadius, Loc.Z);
			SetActorLocation(Clamped);
			if (Out > 0.f) M->Velocity += In * Out;
		}
	}
	// altitude band
	if (Loc.Z < MinAltitude + 500.f) Wish.Z += FMath::Clamp((MinAltitude + 500.f - Loc.Z) / 500.f, 0.f, 1.5f);
	if (Loc.Z > MaxAltitude - 1500.f) Wish.Z -= FMath::Clamp((Loc.Z - (MaxAltitude - 1500.f)) / 1500.f, 0.f, 1.5f);
	if (Loc.Z < MinAltitude)
	{
		SetActorLocation(FVector(Loc.X, Loc.Y, MinAltitude));
		if (M->Velocity.Z < 0.f) M->Velocity.Z = 0.f;
	}

	if (!Wish.IsNearlyZero()) AddMovementInput(Wish.GetClampedToMaxSize(1.5f), 1.f);

	// face the aim direction (yaw only on the actor; lean is visual)
	const FRotator Cur = GetActorRotation();
	const FRotator Target(0.f, Ctrl.Yaw, 0.f);
	SetActorRotation(FMath::RInterpTo(Cur, Target, Dt, 9.f));
}

void AVahagnCharacter::UpdateAim(float Dt)
{
	if (!Camera) return;
	const FVector CamLoc = Camera->GetComponentLocation();
	const FVector CamFwd = Camera->GetForwardVector();
	const float Range = 32000.f;

	FCollisionQueryParams Q(SCENE_QUERY_STAT(TwAim), false, this);
	FHitResult Hit;
	const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, CamLoc + CamFwd * 200.f, CamLoc + CamFwd * Range, ECC_Visibility, Q);
	FVector Point = bHit ? Hit.ImpactPoint : CamLoc + CamFwd * Range;
	const float HitDist = bHit ? Hit.Distance : Range;

	// aim assist: pick the vishap point closest to the crosshair inside a small cone
	AVishap* Best = nullptr;
	float BestScore = TNumericLimits<float>::Max();
	FVector BestPoint = Point;
	TArray<FVector> Pts;
	for (TActorIterator<AVishap> It(GetWorld()); It; ++It)
	{
		AVishap* V = *It;
		if (!V->IsAlive()) continue;
		Pts.Reset();
		V->GetAimPoints(Pts);
		for (int32 i = 0; i < Pts.Num(); ++i)
		{
			const FVector To = Pts[i] - CamLoc;
			const float Dist = To.Size();
			if (Dist < 300.f || Dist > Range) continue;
			const float Cos = FVector::DotProduct(To / Dist, CamFwd);
			const float Ang = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(Cos, -1.f, 1.f)));
			const float Cone = (i == 0 ? 6.5f : 4.5f) * (V->IsBoss() ? 1.6f : 1.f);
			if (Ang > Cone) continue;
			const float Score = Ang + Dist * 0.00005f - (i == 0 ? 1.f : 0.f);
			if (Score < BestScore && Dist < HitDist + 400.f)
			{
				BestScore = Score; Best = V; BestPoint = Pts[i];
				// lead the target
				const float T = Dist / AFireball::Speed;
				BestPoint += V->GetHeadVelocity() * T * 0.8f;
			}
		}
	}
	AimTarget = Best;
	AimPoint = Best ? BestPoint : Point;
}

void AVahagnCharacter::UpdateVisuals(float Dt)
{
	const FVector V = GetVelocity();
	const float Speed = V.Size();
	const FVector Fwd = GetActorForwardVector();
	const float FwdSpeed = FVector::DotProduct(V, Fwd);

	// lean: superhero dive when flying forward fast, follow climb/dive, bank in turns
	const float Yaw = GetActorRotation().Yaw;
	const float YawRate = FMath::FindDeltaAngleDegrees(LastYaw, Yaw) / FMath::Max(Dt, 1e-3f);
	LastYaw = Yaw;
	const float FwdK = FMath::Clamp(FwdSpeed / 2700.f, 0.f, 1.2f);
	float TargetPitch = -62.f * FMath::Min(FwdK, 1.f);
	const float Climb = FMath::Clamp(V.Z / 2700.f, -1.f, 1.f);
	TargetPitch += Climb * 35.f * FMath::Min(FwdK, 1.f);
	if (bDead) TargetPitch = 0.f;
	float TargetRoll = FMath::Clamp(YawRate * 0.10f, -40.f, 40.f) + MoveInput.X * 18.f;
	if (bFireHeld || bChargeHeld) { TargetPitch *= 0.55f; } // upright-ish while casting so shots read clearly
	VisualPitch = FMath::FInterpTo(VisualPitch, TargetPitch, Dt, 5.f);
	VisualRoll = FMath::FInterpTo(VisualRoll, TargetRoll, Dt, 5.f);

	Bob += Dt;
	const float BobZ = (1.f - FMath::Min(FwdK, 1.f)) * FMath::Sin(Bob * 2.1f) * 10.f;
	if (USceneComponent* Pivot = GetMesh()->GetAttachParent())
	{
		Pivot->SetRelativeRotation(FRotator(VisualPitch, 0.f, VisualRoll));
		Pivot->SetRelativeLocation(FVector(0, 0, BobZ));
	}

	// pose
	if (Poser && !bDead)
	{
		const bool bWantFly = FwdSpeed > 1100.f;
		if (bWantFly != bFlyPose)
		{
			bFlyPose = bWantFly;
			Poser->SetLoop(bFlyPose ? AnimFly : AnimHover, 0.35f, bFlyPose ? 0.55f : 1.f);
		}
	}

	// camera feel
	const float SpeedK = FMath::Clamp(Speed / 5600.f, 0.f, 1.f);
	const float TargetFov = BaseFov + (bBoosting ? 14.f : 0.f) + SpeedK * 4.f;
	Camera->SetFieldOfView(FMath::FInterpTo(Camera->FieldOfView, TargetFov, Dt, 4.f));
	Boom->TargetArmLength = FMath::FInterpTo(Boom->TargetArmLength, bBoosting ? 680.f : 560.f, Dt, 3.f);
	// small shake when hurt
	Shake = FMath::Max(0.f, Shake - Dt * 1.8f);
	const float ShakeAmt = DamageFlash * 6.f + Shake * 22.f;
	if (ShakeAmt > 0.1f)
	{
		const float T2 = GetWorld()->GetRealTimeSeconds();
		Camera->SetRelativeLocation(FVector(0, FMath::Sin(T2 * 47.f) * ShakeAmt, FMath::Sin(T2 * 61.f + 1.3f) * ShakeAmt));
	}
	else Camera->SetRelativeLocation(FVector::ZeroVector);

	// fire trail
	{
		const float Now = GetWorld()->GetTimeSeconds();
		TrailTimer -= Dt;
		if (TrailTimer <= 0.f && Speed > 1300.f && !bDead && TrailBirth.Num() > 0)
		{
			TrailTimer = bBoosting ? 0.02f : 0.04f;
			TrailBirth[TrailNext] = Now;
			const FVector Back = GetActorLocation() - V.GetSafeNormal() * 70.f + FMath::VRand() * 18.f;
			FireTrail->UpdateInstanceTransform(TrailNext, FTransform(FRotator::ZeroRotator, Back, FVector(bBoosting ? 0.32f : 0.22f)), true, false, true);
			TrailNext = (TrailNext + 1) % TrailBirth.Num();
		}
		for (int32 i = 0; i < TrailBirth.Num(); ++i)
		{
			const float A = Now - TrailBirth[i];
			if (A < 0.f || A > 0.9f) continue;
			FTransform T;
			FireTrail->GetInstanceTransform(i, T, true);
			T.SetScale3D(FVector((bBoosting ? 0.32f : 0.22f) * (1.f - A / 0.9f) + 0.001f));
			T.AddToTranslation(FVector(0, 0, 60.f * Dt)); // embers drift up
			FireTrail->UpdateInstanceTransform(i, T, true, false, true);
		}
		FireTrail->MarkRenderStateDirty();
	}

	// fire glow
	const float T = GetWorld()->GetTimeSeconds();
	const float Flicker = 0.85f + 0.15f * FMath::Sin(T * 23.f) * FMath::Sin(T * 7.3f);
	Glow->SetIntensity((7000.f + Charge * 14000.f) * Flicker * (bDead ? 0.2f : 1.f));
	if (BodyMat)
	{
		BodyMat->SetScalarParameterValue(TEXT("EmissiveIntensity"), 2.6f * (1.f + Charge * 2.f) * Flicker);
		BodyMat->SetScalarParameterValue(TEXT("HitFlash"), DamageFlash * 0.18f);
	}
	if (WindLoop) WindLoop->SetVolumeMultiplier(FMath::Clamp(Speed / 5600.f, 0.f, 1.f) * 0.6f);
}

// ---------------------------------------------------------------- combat
FVector AVahagnCharacter::MuzzleLocation(bool bRight) const
{
	const FName S = bRight ? SockHandR : SockHandL;
	FVector P = GetMesh()->DoesSocketExist(S) ? GetMesh()->GetSocketLocation(S) : GetActorLocation() + GetActorRightVector() * (bRight ? 40.f : -40.f);
	return P;
}

void AVahagnCharacter::SpawnFireball(const FVector& Muzzle, const FVector& Target, float Power, bool bCharged)
{
	const FVector CamFwd = Camera->GetForwardVector();
	FVector Dir = (Target - Muzzle).GetSafeNormal();
	// never shoot sideways/backwards: the shot always follows the crosshair
	if (FVector::DotProduct(Dir, CamFwd) < 0.35f) Dir = CamFwd;
	FActorSpawnParameters P;
	P.Owner = this;
	P.Instigator = this;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	if (AFireball* F = GetWorld()->SpawnActor<AFireball>(Muzzle + Dir * 30.f, Dir.Rotation(), P))
	{
		F->Launch(Dir, bCharged ? 3.f + 6.f * Power : 1.f, bCharged ? 550.f + 900.f * Power : 0.f, bCharged ? 1.6f + 1.6f * Power : 1.f, false);
	}
}

void AVahagnCharacter::FireOnce()
{
	FireCooldown = 0.15f;
	const FVector Muzzle = MuzzleLocation(bRightHand);
	SpawnFireball(Muzzle, AimPoint, 0.f, false);
	if (Poser) Poser->PlayOneShot(bRightHand ? AnimCastA : AnimCastB, 2.0f, 0.05f, 0.18f, 0.55f);
	TwFx::Burst(GetWorld(), TwFx::EFx::MuzzleFlash, Muzzle, 0.5f);
	TwFx::Sound(GetWorld(), TEXT("sfx_fireball_cast"), Muzzle, 0.55f, FMath::FRandRange(0.92f, 1.08f));
	bRightHand = !bRightHand;
}

void AVahagnCharacter::FireCharged()
{
	if (Charge < 0.3f) { FireOnce(); return; }
	FireCooldown = 0.35f;
	const FVector Muzzle = (MuzzleLocation(true) + MuzzleLocation(false)) * 0.5f + GetActorForwardVector() * 40.f;
	SpawnFireball(Muzzle, AimPoint, Charge, true);
	if (Poser) Poser->PlayOneShot(AnimCastA, 1.4f, 0.05f, 0.25f, 0.85f);
	TwFx::Burst(GetWorld(), TwFx::EFx::MuzzleFlash, Muzzle, 1.2f + Charge);
	TwFx::LightFlash(GetWorld(), Muzzle, FLinearColor(1.f, 0.5f, 0.15f), 40000.f, 3000.f, 0.35f);
	TwFx::Sound(GetWorld(), TEXT("sfx_fireball_cast"), Muzzle, 1.f, 0.7f);
}

void AVahagnCharacter::InNova()
{
	if (!bControl || bDead || Nova < 100.f) return;
	Nova = 0.f;
	const FVector C = GetActorLocation();
	if (Poser) Poser->PlayOneShot(AnimNova, 1.3f, 0.05f, 0.3f, 1.f);
	TwFx::Burst(GetWorld(), TwFx::EFx::Nova, C, 6.f);
	TwFx::Burst(GetWorld(), TwFx::EFx::BigExplosion, C, 4.f);
	TwFx::LightFlash(GetWorld(), C, FLinearColor(1.f, 0.6f, 0.2f), 300000.f, 9000.f, 0.9f);
	TwFx::Sound2D(GetWorld(), TEXT("sfx_special_nova"), 1.f);
	AddShake(1.f);
	for (TActorIterator<AVishap> It(GetWorld()); It; ++It)
	{
		AVishap* V = *It;
		if (!V->IsAlive()) continue;
		const float D = V->DistanceToPoint(C);
		if (D < 5200.f)
		{
			const float Dmg = (V->IsBoss() ? 18.f : 14.f) * (1.f - 0.5f * D / 5200.f);
			V->ApplyHit(Dmg, C, this, true);
			V->Knockback(C, 4000.f);
		}
	}
	// a short, dramatic slow-motion beat
	if (!FMath::IsNearlyEqual(UGameplayStatics::GetGlobalTimeDilation(this), 1.f, 0.01f)) { DamageFlash = 0.3f; return; }
	UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 0.3f);
	FTimerHandle H;
	TWeakObjectPtr<UWorld> W(GetWorld());
	GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateLambda([W]() { if (W.IsValid() && FMath::IsNearlyEqual(UGameplayStatics::GetGlobalTimeDilation(W.Get()), 0.3f, 0.01f)) UGameplayStatics::SetGlobalTimeDilation(W.Get(), 1.f); }), 0.12f, false);
	DamageFlash = 0.3f;
}

void AVahagnCharacter::Heal(float Amount)
{
	Health = FMath::Min(MaxHealth, Health + Amount);
}

void AVahagnCharacter::RegisterHit(bool bKill)
{
	HitMarker = bKill ? 1.6f : 1.f;
	AddNova(bKill ? 10.f : 1.5f);
}

float AVahagnCharacter::TakeDamage(float Damage, const FDamageEvent& Event, AController* Inst, AActor* Causer)
{
	if (bDead || Damage <= 0.f) return 0.f;
	float Mult = 1.f;
	if (const AVahagnGameMode* GM = GetWorld()->GetAuthGameMode<AVahagnGameMode>()) Mult = GM->DamageToPlayerMultiplier();
	const float D = Damage * Mult;
	UE_LOG(LogTwilight, Display, TEXT("[TwDmg] %.1f from %s (hp %.0f)"), D, Causer ? *Causer->GetName() : TEXT("?"), Health);
	Health -= D;
	LastDamageTime = GetWorld()->GetTimeSeconds();
	DamageFlash = FMath::Min(1.f, DamageFlash + 0.6f);
	if (Poser && FMath::FRand() < 0.5f) Poser->PlayOneShot(AnimHit, 1.3f, 0.05f, 0.2f, 0.45f);
	TwFx::Sound(GetWorld(), TEXT("sfx_player_hurt"), GetActorLocation(), 0.8f, FMath::FRandRange(0.9f, 1.1f));
	if (Health <= 0.f) { Health = 0.f; Die(); }
	return D;
}

void AVahagnCharacter::Die()
{
	if (bDead) return;
	UE_LOG(LogTwilight, Display, TEXT("[TwDmg] DIED at %s"), *GetActorLocation().ToString());
	bDead = true;
	SetControlEnabled(false);
	GetCharacterMovement()->StopMovementImmediately();
	GetCharacterMovement()->DisableMovement();
	if (Poser) Poser->SetLoop(AnimDeath, 0.2f, 1.f, false);
	for (UFXSystemComponent* A : Auras) if (A) A->Deactivate();
	TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, GetActorLocation(), 2.f);
	if (FlameLoop) FlameLoop->FadeOut(1.f, 0.f);
}

// ---------------------------------------------------------------- autopilot (automated play-test)
void AVahagnCharacter::UpdateAutopilot(float Dt)
{
	AController* C = GetController();
	if (!C) return;
	AVishap* Target = nullptr;
	float Best = TNumericLimits<float>::Max();
	for (TActorIterator<AVishap> It(GetWorld()); It; ++It)
	{
		if (!It->IsAlive()) continue;
		const float D = FVector::Dist(It->GetHeadLocation(), GetActorLocation());
		if (D < Best) { Best = D; Target = *It; }
	}
	FVector Goal;
	if (Target)
	{
		Goal = Target->GetHeadLocation() + Target->GetHeadVelocity() * 0.3f;
	}
	else
	{
		AutoWanderTimer -= Dt;
		if (AutoWanderTimer <= 0.f)
		{
			AutoWanderTimer = 4.f;
			AutoWander = FVector(FMath::FRandRange(-20000.f, 20000.f), FMath::FRandRange(-20000.f, 20000.f), FMath::FRandRange(2500.f, 7000.f));
		}
		Goal = AutoWander;
	}
	const FVector To = Goal - Camera->GetComponentLocation();
	const FRotator Want = To.Rotation();
	C->SetControlRotation(FMath::RInterpTo(C->GetControlRotation(), Want, Dt, 3.5f));
	const float Ang = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(To.GetSafeNormal(), Camera->GetForwardVector()), -1.f, 1.f)));
	const float Dist = To.Size();
	MoveInput = FVector2D(Target ? FMath::Sin(GetWorld()->GetTimeSeconds() * 0.7f) * 0.7f : 0.f, Dist > 4500.f ? 1.f : (Dist < 2200.f ? -0.6f : 0.2f));
	UpInput = GetActorLocation().Z < 1500.f ? 1.f : 0.f;
	bBoosting = Dist > 12000.f && BoostEnergy > 30.f;
	bFireHeld = Target && Ang < 10.f && Dist < 20000.f;
	if (Nova >= 100.f && Target && Dist < 4000.f) InNova();
}
