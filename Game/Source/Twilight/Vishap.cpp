#include "Vishap.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "Fireball.h"
#include "FireOrb.h"
#include "VahagnCharacter.h"
#include "VahagnGameMode.h"

#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraComponent.h"

namespace
{
	const FLinearColor SkinNormal(0.035f, 0.028f, 0.05f);
	const FLinearColor SkinElite(0.12f, 0.02f, 0.02f);
	const FLinearColor SkinBoss(0.02f, 0.03f, 0.035f);
	const FLinearColor VeinNormal(1.f, 0.25f, 0.05f);
	const FLinearColor VeinBoss(1.f, 0.12f, 0.02f);
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
		MaxHealth = 170.f * HealthMult;
	}
	else
	{
		NumSeg = 26; R0 = Tier ? 95.f : 82.f; Spacing = R0 * 1.35f; BaseSpeed = Tier ? 2900.f : 2400.f; TurnRate = Tier ? 120.f : 95.f;
		MaxHealth = (Tier ? 16.f : 10.f) * HealthMult;
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
	const FLinearColor Vein = bBoss ? VeinBoss : VeinNormal;
	if (SkinMat)
	{
		SkinMat->SetVectorParameterValue(TEXT("SkinColor"), Skin);
		SkinMat->SetVectorParameterValue(TEXT("VeinColor"), Vein);
		SkinMat->SetScalarParameterValue(TEXT("VeinIntensity"), bBoss ? 9.f : 6.f);
	}
	BoneMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (BoneMat)
	{
		BoneMat->SetVectorParameterValue(TEXT("SkinColor"), FLinearColor(0.09f, 0.07f, 0.06f));
		BoneMat->SetVectorParameterValue(TEXT("VeinColor"), Vein);
		BoneMat->SetScalarParameterValue(TEXT("VeinIntensity"), 2.f);
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
			C->SetCollisionObjectType(ECC_WorldDynamic);
			C->SetCollisionResponseToAllChannels(ECR_Ignore);
			C->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
			C->SetCollisionResponseToChannel(ECC_WorldDynamic, ECR_Overlap);
			C->SetGenerateOverlapEvents(true);
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
		S->SetWorldScale3D(FVector(R / 50.f * 1.25f, R / 50.f, R / 50.f * 0.92f));
		Segments.Add(S);

		// dorsal spikes, longer near the head
		if (i >= 2 && i % 2 == 0 && i < NumSeg - 2)
		{
			UStaticMeshComponent* Sp = MakePart(ConeMesh, S, BoneMat, false);
			const float L = FMath::Lerp(1.4f, 0.5f, T);
			Sp->SetRelativeLocation(FVector(-10.f, 0.f, 42.f));
			Sp->SetRelativeRotation(FRotator(-35.f, 0.f, 0.f));
			Sp->SetRelativeScale3D(FVector(0.32f, 0.32f, 0.7f * L));
		}
		// side fins on a few segments
		if (i == 4 || i == 9)
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
		Horn->SetRelativeScale3D(FVector(0.22f, 0.22f, bBoss ? 1.5f : 1.1f));
		UStaticMeshComponent* Eye = MakePart(SphereMesh, H, EyeMat, false);
		Eye->SetRelativeLocation(FVector(88.f, 20.f * s, 20.f));
		Eye->SetRelativeScale3D(FVector(0.17f, 0.12f, 0.1f));
		// brow spikes
		UStaticMeshComponent* Brow = MakePart(ConeMesh, H, BoneMat, false);
		Brow->SetRelativeLocation(FVector(70.f, 22.f * s, 30.f));
		Brow->SetRelativeRotation(FRotator(-75.f, 0.f, 25.f * s));
		Brow->SetRelativeScale3D(FVector(0.12f, 0.12f, 0.45f));
	}

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
}

AVahagnCharacter* AVishap::Player() const
{
	return Cast<AVahagnCharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
}

FVector AVishap::MouthLocation() const
{
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
	case EVishapState::Dying: StateDur = 3.f; break;
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
	if (GetWorld()->LineTraceSingleByChannel(Hit, HeadPos, HeadPos + Fwd * 2500.f, ECC_WorldStatic, Q))
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
		if (P && !P->IsDead() && Dist < Range && AttackCooldown <= 0.f)
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
		UGameplayStatics::ApplyDamage(P, bBoss ? 4.5f : 3.f, nullptr, this, nullptr);
	}
	// visible fire puffs along the cone
	TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, M + Fwd * FMath::FRandRange(0.3f, 0.9f) * Range * 0.8f, bBoss ? 1.3f : 0.7f);
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
	TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, Where, bBoss ? 1.5f : 1.f);
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
	if (Hero && bNotify) Hero->NotifyHit(bKill);
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
		DebrisVel[i] = HeadVel * 0.35f + FMath::VRand() * FMath::FRandRange(200.f, 900.f) + FVector(0, 0, FMath::FRandRange(0.f, 700.f));
	}
	if (Skull) Skull->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	TwFx::Burst(GetWorld(), TwFx::EFx::VishapDeath, HeadPos, bBoss ? 6.f : 2.5f);
	TwFx::LightFlash(GetWorld(), HeadPos, FLinearColor(1.f, 0.4f, 0.1f), bBoss ? 400000.f : 80000.f, bBoss ? 12000.f : 4000.f, bBoss ? 1.5f : 0.6f);
	TwFx::Sound(GetWorld(), TEXT("sfx_vishap_death"), HeadPos, 1.f, bBoss ? 0.7f : 1.f);
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
		const int32 Need = FMath::CeilToInt((NumSeg + 2) * Spacing / TrailStep) + 4;
		if (Trail.Num() > Need) Trail.SetNum(Need);
	}
	UpdateBody(Dt);
	HitFlash = FMath::Max(0.f, HitFlash - Dt * 6.f);
}

void AVishap::UpdateBody(float Dt)
{
	const float Lag = FVector::Dist(HeadPos, Trail[0]);
	for (int32 i = 0; i < Segments.Num(); ++i)
	{
		FVector Tan;
		const float DistAlong = FMath::Max(0.f, i * Spacing - Lag);
		FVector P = i == 0 ? HeadPos : SampleTrail(DistAlong + Lag * 0.f, &Tan);
		if (i == 0) Tan = HeadVel.GetSafeNormal().IsNearlyZero() ? FVector::ForwardVector : HeadVel.GetSafeNormal();
		// gentle undulation travelling down the body
		const float Wave = FMath::Sin(LifeTime * 5.f - i * 0.55f) * SegRadius[i] * 0.25f;
		const FVector Side = FVector::CrossProduct(Tan, FVector::UpVector).GetSafeNormal();
		P += Side * Wave;
		const FRotator Rot = FRotationMatrix::MakeFromXZ(Tan, FVector::UpVector).Rotator();
		Segments[i]->SetWorldLocationAndRotation(P, Rot);
	}
	if (Jaw)
	{
		Jaw->SetRelativeRotation(FRotator(-JawOpen * 32.f, 0.f, 0.f));
		Jaw->SetRelativeLocation(FVector(60.f - JawOpen * 6.f, 0.f, -22.f - JawOpen * 10.f));
	}
	if (SkinMat) SkinMat->SetScalarParameterValue(TEXT("HitFlash"), HitFlash);
	if (EyeLight)
	{
		const bool bAngry = State == EVishapState::BreathWindup || State == EVishapState::Breath || State == EVishapState::DashWindup;
		EyeLight->SetIntensity((bBoss ? 12000.f : 3500.f) * (bAngry ? 2.5f : 1.f));
	}
	SetActorLocation(HeadPos, false, nullptr, ETeleportType::TeleportPhysics);
}

void AVishap::UpdateDying(float Dt)
{
	DyingTime += Dt;
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
	while (NextPop < Segments.Num() && DyingTime > NextPop * PopInterval)
	{
		if (NextPop % 2 == 0)
		{
			const FVector P = Segments[NextPop]->GetComponentLocation();
			TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, P, (bBoss ? 2.2f : 1.f) * (1.f - 0.5f * NextPop / float(Segments.Num())));
		}
		++NextPop;
	}
	if (DyingTime > StateDur) Destroy();
}
