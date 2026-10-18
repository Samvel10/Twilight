#include "AralezSpirit.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "AralezWorld.h"
#include "AralezActors.h"

#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EngineUtils.h"
#include "Engine/World.h"

static constexpr int32 SpiritTrail = 36;

AAralezSpirit::AAralezSpirit()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	BodyRoot = CreateDefaultSubobject<USceneComponent>(TEXT("BodyRoot"));
	BodyRoot->SetupAttachment(Root);
	Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("Boom"));
	Boom->SetupAttachment(Root);
	Boom->TargetArmLength = 520.f;
	Boom->SocketOffset = FVector(0, 0, 120.f);
	Boom->bUsePawnControlRotation = true;
	Boom->bEnableCameraLag = true;
	Boom->CameraLagSpeed = 8.f;
	Boom->bDoCollisionTest = false;
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Boom, USpringArmComponent::SocketName);
	Camera->SetFieldOfView(90.f);
	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(BodyRoot);
	Glow->SetIntensityUnits(ELightUnits::Unitless);
	Glow->SetCastShadows(false);
	Trail = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Trail"));
	Trail->SetupAttachment(Root);
	Trail->SetAbsolute(true, true, true);
	Trail->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Trail->SetCastShadow(false);
	AutoPossessAI = EAutoPossessAI::Disabled;
}

void AAralezSpirit::Setup(bool bInBot, const FLinearColor& InColor, const FText& InName, int32 InSkill)
{
	bBot = bInBot; Color = InColor; Name = InName; Skill = InSkill;
	BotLane = FMath::FRandRange(-0.5f, 0.5f);
}

void AAralezSpirit::BeginPlay()
{
	Super::BeginPlay();
	BuildBody();
	Glow->SetLightColor(Color);
	Glow->SetIntensity(bBot ? 6000.f : 20000.f);
	Glow->SetAttenuationRadius(bBot ? 900.f : 2400.f);
	if (bBot) Camera->Deactivate();
	PathT = AAralezWorld::NearestT(GetActorLocation(), 0.f);
}

void AAralezSpirit::BuildBody()
{
	Mat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Mat)
	{
		Mat->SetVectorParameterValue(TEXT("Color"), Color);
		Mat->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		Mat->SetScalarParameterValue(TEXT("Intensity"), bBot ? 2.4f : 3.2f);
	}
	auto Part = [this](UStaticMesh* M, USceneComponent* Parent, const FVector& Loc, const FRotator& Rot, const FVector& Scl) -> UStaticMeshComponent*
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(M);
		C->SetupAttachment(Parent);
		C->SetRelativeLocationAndRotation(Loc, Rot);
		C->SetRelativeScale3D(Scl);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		C->SetMaterial(0, Mat);
		C->RegisterComponent();
		return C;
	};
	UStaticMesh* Sph = TwAssets::Sphere();
	UStaticMesh* Cone = TwAssets::Cone();
	UStaticMesh* Cyl = TwAssets::Cylinder();
	// body along +X (forward)
	Part(Sph, BodyRoot, FVector(0, 0, 0), FRotator::ZeroRotator, FVector(1.5f, 0.62f, 0.62f));        // torso
	Part(Sph, BodyRoot, FVector(55, 0, 10), FRotator::ZeroRotator, FVector(0.8f, 0.68f, 0.72f));      // chest
	Part(Sph, BodyRoot, FVector(100, 0, 42), FRotator::ZeroRotator, FVector(0.55f, 0.42f, 0.45f));    // head
	Part(Cone, BodyRoot, FVector(132, 0, 36), FRotator(-90, 0, 0), FVector(0.22f, 0.2f, 0.42f));      // snout
	Part(Cone, BodyRoot, FVector(92, 12, 70), FRotator(-15, 0, 15), FVector(0.1f, 0.1f, 0.3f));       // ears
	Part(Cone, BodyRoot, FVector(92, -12, 70), FRotator(-15, 0, -15), FVector(0.1f, 0.1f, 0.3f));
	// legs tucked back like a leaping dog
	for (int32 s = -1; s <= 1; s += 2)
	{
		Part(Cyl, BodyRoot, FVector(50, 18.f * s, -32), FRotator(-55, 0, 0), FVector(0.1f, 0.1f, 0.55f));
		Part(Cyl, BodyRoot, FVector(-50, 18.f * s, -30), FRotator(55, 0, 0), FVector(0.11f, 0.11f, 0.6f));
	}
	// tail
	for (int32 i = 0; i < 5; ++i)
	{
		const float K = 1.f - i * 0.17f;
		TailParts.Add(Part(Sph, BodyRoot, FVector(-75.f - i * 26.f, 0, 8.f + i * 6.f), FRotator::ZeroRotator, FVector(0.32f * K)));
	}
	// feathered wings (flattened cubes) pivoting at the shoulders
	USceneComponent* PivotL = NewObject<USceneComponent>(this); PivotL->SetupAttachment(BodyRoot); PivotL->SetRelativeLocation(FVector(30, 20, 30)); PivotL->RegisterComponent();
	USceneComponent* PivotR = NewObject<USceneComponent>(this); PivotR->SetupAttachment(BodyRoot); PivotR->SetRelativeLocation(FVector(30, -20, 30)); PivotR->RegisterComponent();
	// feathered wings: a fan of long tapered feathers per side
	for (int32 s = 0; s < 2; ++s)
	{
		USceneComponent* Pv = s == 0 ? PivotL : PivotR;
		const float Side = s == 0 ? 1.f : -1.f;
		for (int32 f = 0; f < 6; ++f)
		{
			const float Ang = (-10.f - f * 13.f) * Side;            // fan sweeping backwards
			const float Len = 1.5f + 0.35f * FMath::Sin(f * 0.6f);   // long primaries in the middle
			const FVector Dir = FRotator(0.f, -90.f * Side + Ang, 0.f).Vector() * -1.f;
			UStaticMeshComponent* Fe = Part(TwAssets::Sphere(), Pv, FVector(Dir.X, Dir.Y, 0.f) * Len * 50.f, FRotator(0.f, Ang + 90.f * Side, 0.f), FVector(0.22f, Len, 0.03f));
			if (f == 2) { if (s == 0) WingL = Fe; else WingR = Fe; }
		}
	}
	BodyRoot->SetRelativeScale3D(FVector(bBot ? 0.9f : 1.f));

	Trail->SetStaticMesh(Sph);
	Trail->SetMaterial(0, Mat);
	TArray<FTransform> Init;
	for (int32 i = 0; i < SpiritTrail; ++i) Init.Add(FTransform(FRotator::ZeroRotator, GetActorLocation(), FVector(0.001f)));
	Trail->AddInstances(Init, false, true);
	TrailBirth.Init(-100.f, SpiritTrail);
}

void AAralezSpirit::InLook(const FVector2D& V)
{
	if (!bControl) return;
	AddControllerYawInput(V.X);
	AddControllerPitchInput(V.Y);
}

void AAralezSpirit::InDash()
{
	if (!bControl || DashCd > 0.f || Stun > 0.f) return;
	DashCd = 2.5f;
	DashTime = 0.45f;
	TwFx::Sound(GetWorld(), TEXT("sfx_boost"), GetActorLocation(), bBot ? 0.4f : 0.9f, 1.2f);
}

void AAralezSpirit::InHowl()
{
	if (!bControl || HowlCd > 0.f || Stun > 0.f) return;
	HowlCd = 12.f;
	const FVector P = GetActorLocation();
	TwFx::Sound(GetWorld(), TEXT("sfx_aralez_howl"), P, bBot ? 0.4f : 1.f);
	TwFx::Burst(GetWorld(), TwFx::EFx::Nova, P, 2.f);
	for (TActorIterator<AShadowWraith> It(GetWorld()); It; ++It)
		if (FVector::Dist(It->GetActorLocation(), P) < 2600.f) It->Repel(P);
	for (TActorIterator<ASoulLight> It(GetWorld()); It; ++It)
		if (FVector::Dist(It->GetActorLocation(), P) < 2600.f) It->PullTo(this);
}

int32 AAralezSpirit::StealLights(int32 N)
{
	const int32 Lost = FMath::Min(N, Lights);
	Lights -= Lost;
	return Lost;
}

void AAralezSpirit::ThinkBot(float Dt)
{
	BotThink -= Dt;
	if (BotThink <= 0.f)
	{
		BotThink = 0.25f;
		// default goal: ahead along the path, on a personal lane
		const float Ahead = FMath::Min(1.f, PathT + 0.025f + 0.004f * Skill);
		const FVector P = AAralezWorld::PathPoint(Ahead);
		const FVector Fwd = AAralezWorld::PathTangent(Ahead);
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
		BotGoal = P + Right * BotLane * AAralezWorld::TunnelRadius(Ahead) * 0.6f;
		// grab a nearby light that is roughly ahead
		float Best = 2600.f + 600.f * Skill;
		for (TActorIterator<ASoulLight> It(GetWorld()); It; ++It)
		{
			if (It->IsTaken()) continue;
			{
				const FVector LP = It->GetActorLocation();
				const float LT = AAralezWorld::NearestT(LP, PathT);
				if (FVector::Dist(LP, AAralezWorld::PathPoint(LT)) > AAralezWorld::TunnelRadius(LT) * 0.6f) continue; // unreachable
			}
			const FVector To = It->GetActorLocation() - GetActorLocation();
			const float D = To.Size();
			if (D < Best && FVector::DotProduct(To.GetSafeNormal(), Fwd) > -0.2f) { Best = D; BotGoal = It->GetActorLocation(); }
		}
		// flee wraiths
		for (TActorIterator<AShadowWraith> It(GetWorld()); It; ++It)
		{
			const FVector Away = GetActorLocation() - It->GetActorLocation();
			if (Away.Size() < 1300.f) BotGoal += Away.GetSafeNormal() * 1500.f;
		}
		if (DashCd <= 0.f && FMath::FRand() < 0.05f * Skill) InDash();
	}
}

void AAralezSpirit::Move(float Dt)
{
	FVector Wish = FVector::ZeroVector;
	if (bBot)
	{
		Wish = (BotGoal - GetActorLocation()).GetSafeNormal();
	}
	else if (Controller)
	{
		const FRotator C = Controller->GetControlRotation();
		const FVector F = C.Vector();
		const FVector R = FRotationMatrix(FRotator(0, C.Yaw, 0)).GetUnitAxis(EAxis::Y);
		Wish = F * MoveIn.Y + R * MoveIn.X + FVector::UpVector * UpIn;
		Wish = Wish.GetClampedToMaxSize(1.f);
	}
	if (Stun > 0.f) Wish *= 0.15f;
	const float BotScale = bBot ? (0.86f + 0.05f * Skill) : 1.f;
	const float MaxSpd = Speed * BotScale * (DashTime > 0.f ? 2.2f : 1.f);
	const FVector Target = Wish * MaxSpd;
	Vel = FMath::VInterpTo(Vel, Target, Dt, Wish.IsNearlyZero() ? 1.5f : 3.f);

	FVector P = GetActorLocation() + Vel * Dt;
	// stay inside the tunnel (soft wall)
	PathT = AAralezWorld::NearestT(P, PathT);
	const FVector C = AAralezWorld::PathPoint(PathT);
	FVector Off = P - C;
	const FVector Tan = AAralezWorld::PathTangent(PathT);
	Off -= Tan * FVector::DotProduct(Off, Tan);
	const float D = Off.Size();
	if (D > KINDA_SMALL_NUMBER)
	{
		const FVector Dir = Off / D;
		// same frame as AAralezWorld::BuildTunnel; the floor is flatter (closer) than the walls
		const FVector RightV = FVector::CrossProduct(FVector::UpVector, Tan).GetSafeNormal();
		const FVector UpV = FVector::CrossProduct(Tan, RightV).GetSafeNormal();
		const float Frac = FVector::DotProduct(Dir, UpV) < -0.35f ? 0.60f : 0.76f;
		const float Lim = AAralezWorld::TunnelRadius(PathT) * Frac;
		if (D > Lim)
		{
			P -= Dir * (D - Lim);
			Vel -= Dir * FMath::Max(0.f, FVector::DotProduct(Vel, Dir));
		}
	}
	if (PathT <= 0.001f && FVector::DotProduct(Vel, Tan) < 0.f) Vel -= Tan * FVector::DotProduct(Vel, Tan);
	SetActorLocation(P);
	if (!Vel.IsNearlyZero(50.f)) SetActorRotation(FMath::RInterpTo(GetActorRotation(), Vel.Rotation(), Dt, 6.f));
}

void AAralezSpirit::Animate(float Dt)
{
	Flap += Dt * (DashTime > 0.f ? 16.f : 7.f);
	const float W = FMath::Sin(Flap) * 38.f;
	if (WingL && WingL->GetAttachParent()) WingL->GetAttachParent()->SetRelativeRotation(FRotator(0, 0, -W));
	if (WingR && WingR->GetAttachParent()) WingR->GetAttachParent()->SetRelativeRotation(FRotator(0, 0, W));
	for (int32 i = 0; i < TailParts.Num(); ++i)
	{
		FVector L = TailParts[i]->GetRelativeLocation();
		L.Y = FMath::Sin(Flap * 0.7f - i * 0.6f) * 8.f * i;
		TailParts[i]->SetRelativeLocation(L);
	}
	BodyRoot->SetRelativeLocation(FVector(0, 0, FMath::Sin(Flap * 0.5f) * 12.f));
	Pulse = FMath::Max(0.f, Pulse - Dt * 2.f);
	if (Mat) Mat->SetScalarParameterValue(TEXT("Intensity"), (bBot ? 2.4f : 3.2f) * (1.f + Pulse * 1.5f) * (Stun > 0.f ? 0.3f + 0.3f * FMath::Sin(Flap * 6.f) : 1.f));

	// light trail
	const float Now = GetWorld()->GetTimeSeconds();
	TrailTimer -= Dt;
	if (TrailTimer <= 0.f)
	{
		TrailTimer = 0.04f;
		TrailBirth[TrailNext] = Now;
		Trail->UpdateInstanceTransform(TrailNext, FTransform(FRotator::ZeroRotator, GetActorLocation() - GetActorForwardVector() * 120.f, FVector(0.12f)), true, false, true);
		TrailNext = (TrailNext + 1) % SpiritTrail;
	}
	for (int32 i = 0; i < SpiritTrail; ++i)
	{
		const float A = Now - TrailBirth[i];
		if (A < 0.f || A > 1.4f) continue;
		FTransform T;
		Trail->GetInstanceTransform(i, T, true);
		T.SetScale3D(FVector(0.12f * (1.f - A / 1.4f) + 0.001f));
		Trail->UpdateInstanceTransform(i, T, true, false, true);
	}
	Trail->MarkRenderStateDirty();
}

void AAralezSpirit::Tick(float Dt)
{
	Super::Tick(Dt);
	DashCd = FMath::Max(0.f, DashCd - Dt);
	HowlCd = FMath::Max(0.f, HowlCd - Dt);
	DashTime = FMath::Max(0.f, DashTime - Dt);
	Stun = FMath::Max(0.f, Stun - Dt);
	if (bControl && !bFinished)
	{
		if (bBot) ThinkBot(Dt);
		Move(Dt);
		if (bBot && Controller && !Vel.IsNearlyZero(50.f)) Controller->SetControlRotation(FMath::RInterpTo(Controller->GetControlRotation(), Vel.Rotation(), Dt, 2.5f));
	}
	else
	{
		Vel = FMath::VInterpTo(Vel, FVector::ZeroVector, Dt, 2.f);
		SetActorLocation(GetActorLocation() + Vel * Dt);
	}
	Animate(Dt);
	if (!bBot)
	{
		Camera->SetFieldOfView(FMath::FInterpTo(Camera->FieldOfView, DashTime > 0.f ? 104.f : 90.f, Dt, 5.f));
	}
}
