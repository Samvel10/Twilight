#include "AralezSpirit.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "AralezWorld.h"
#include "AralezActors.h"
#include "AralezField.h"
#include "AralezBodyComponent.h"
#include "AralezWingComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "TwFlash.h"

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
	BotLane = (InSkill - 1) * 0.6f;
}

void AAralezSpirit::BeginPlay()
{
	Super::BeginPlay();
	BuildBody();
	Glow->SetLightColor(Color);
	Glow->SetIntensity(bBot ? 6000.f : 20000.f);
	Glow->SetAttenuationRadius(bBot ? 900.f : 2400.f);
	if (bBot) Camera->Deactivate();
	Boom->bDoCollisionTest = bField; // the plain has collision: keep the lens above the grass
	if (!bField) PathT = AAralezWorld::NearestT(GetActorLocation(), 0.f);
	else { Boom->TargetArmLength = 700.f; Boom->CameraLagSpeed = 6.f; Glow->SetAttenuationRadius(bBot ? 1200.f : 1800.f); Glow->SetIntensity(RealBody ? 0.f : (bBot ? 5000.f : 9000.f)); if (RealBody) Glow->SetVisibility(false); }
}

void AAralezSpirit::BuildBody()
{
	// on Ara's field the Aralez is the real winged dog (CC-BY Shiba-Inu rig + original feather wings)
	if (bField)
	{
		UAralezBodyComponent* B = NewObject<UAralezBodyComponent>(this, TEXT("AralezBody"));
		B->NumShells = bBot ? 0 : 2;
		B->GlowLight = bBot ? 0.f : 3.f; // a faint warmth only: a strong light painted a yellow disc on the grass
		B->SetupAttachment(BodyRoot);
		B->SetRelativeLocation(FVector(0.f, 0.f, -60.f));
		B->RegisterComponent();
		B->Build();
		if (B->GetDog() && B->GetDog()->GetSkeletalMeshAsset())
		{
			RealBody = B;
			RealBody->SetMode(EAralezMode::Glide, 0.f);
			Trail->SetVisibility(false);
			return;
		}
		B->DestroyComponent();
	}
	Mat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Mat)
	{
		Mat->SetVectorParameterValue(TEXT("Color"), Color);
		Mat->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		Mat->SetScalarParameterValue(TEXT("Intensity"), bBot ? 1.2f : 1.6f);
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

	Trail->SetStaticMesh(TwAssets::Cylinder());
	Trail->SetMaterial(0, Mat);
	TArray<FTransform> Init;
	for (int32 i = 0; i < SpiritTrail; ++i) Init.Add(FTransform(FRotator::ZeroRotator, GetActorLocation(), FVector(0.001f)));
	Trail->AddInstances(Init, false, true);
	TrailBirth.Init(-100.f, SpiritTrail);
	TrailLen.Init(0.f, SpiritTrail);
	PrevTrail = GetActorLocation();
}

void AAralezSpirit::UpdateCameraRig(float Dt)
{
	if (!Boom || !Controller) return;
	if (!bFreeLook)
	{
		OrbitYaw = FMath::FInterpTo(FRotator::NormalizeAxis(OrbitYaw), 0.f, Dt, 3.f);
		OrbitPitch = FMath::FInterpTo(OrbitPitch, 0.f, Dt, 3.f);
	}
	float SpinYaw = 0.f;
	if (SpinLeft > 0.f)
	{
		SpinLeft = FMath::Max(0.f, SpinLeft - Dt / 1.1f);
		const float T = 1.f - SpinLeft;
		SpinYaw = 360.f * T * T * (3.f - 2.f * T);
	}
	CamYawNow = FMath::FInterpTo(CamYawNow, OrbitYaw + (bFrontView ? 180.f : 0.f), Dt, bFreeLook ? 18.f : 6.f);
	CamPitchNow = FMath::FInterpTo(CamPitchNow, OrbitPitch + (bFrontView ? -6.f : 0.f), Dt, bFreeLook ? 18.f : 6.f);
	const FRotator Ctl = Controller->GetControlRotation();
	Boom->SetUsingAbsoluteRotation(true);
	Boom->bUsePawnControlRotation = false;
	Boom->SetWorldRotation(FRotator(FMath::Clamp(FRotator::NormalizeAxis(Ctl.Pitch) + CamPitchNow, -85.f, 85.f), Ctl.Yaw + CamYawNow + SpinYaw, 0.f));
}

void AAralezSpirit::InLook(const FVector2D& V)
{
	if (!bControl) return;
	if (bFreeLook)
	{
		OrbitYaw += V.X * 2.2f;
		OrbitPitch = FMath::Clamp(OrbitPitch + V.Y * 2.2f, -70.f, 70.f);
		return;
	}
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
	// a soft blue shock-wave instead of a blinding explosion (the camera is very close in the cave)
	{
		FActorSpawnParameters Sp;
		Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		if (ATwFlash* F = GetWorld()->SpawnActor<ATwFlash>(P, FRotator::ZeroRotator, Sp)) F->Init(FLinearColor(0.25f, 0.7f, 1.f) * 0.35f, bBot ? 10.f : 16.f, 0.5f);
	}
	for (TActorIterator<AShadowWraith> It(GetWorld()); It; ++It)
		if (FVector::Dist(It->GetActorLocation(), P) < 2600.f) It->Repel(P);
	for (TActorIterator<ASoulLight> It(GetWorld()); It; ++It)
		if (FVector::Dist(It->GetActorLocation(), P) < 2600.f) It->PullTo(this);
	// on Ara's plain the howl drives Shamiram's spearmen back
	for (TActorIterator<AShamiramSoldier> It(GetWorld()); It; ++It)
		if (FVector::Dist(It->GetActorLocation(), P) < 2200.f) It->Repel(P);
}

float AAralezSpirit::GetAltitude() const
{
	const FVector P = GetActorLocation();
	return P.Z - AAralezField::GroundZ(P.X, P.Y);
}

void AAralezSpirit::ThinkBotField(float Dt)
{
	BotThink -= Dt;
	AActor* Pat = BotPatient.Get();
	const AFallenWarrior* W = Cast<AFallenWarrior>(Pat);
	if (BotThink <= 0.f || !W || W->IsRevived() || W->IsLocked())
	{
		BotThink = 1.f;
		// nearest fallen warrior nobody else (no other spirit) is already tending
		float Best = TNumericLimits<float>::Max();
		AFallenWarrior* Pick = nullptr;
		for (TActorIterator<AFallenWarrior> It(GetWorld()); It; ++It)
		{
			if (It->IsRevived() || It->IsLocked()) continue;
			bool bTaken = false;
			for (TActorIterator<AAralezSpirit> S(GetWorld()); S; ++S)
				if (*S != this && FVector::Dist2D(S->GetActorLocation(), It->GetActorLocation()) < 900.f) bTaken = true;
			float D = FVector::Dist2D(It->GetActorLocation(), GetActorLocation());
			if (bTaken) D += 20000.f;
			if (It->IsAra()) D += 6000.f; // the king last: he needs the whole pack
			if (D < Best) { Best = D; Pick = *It; }
		}
		if (Pick != Pat) BotHover = 0.f;
		BotPatient = Pick;
		W = Pick;
	}
	FVector Goal = GetActorLocation();
	if (W)
	{
		const FVector T = W->GetActorLocation();
		const float D = FVector::Dist2D(T, GetActorLocation());
		// cruise high (out of spear reach), drop only for the last stretch
		const float H = D > 2500.f ? 1800.f : 260.f;
		Goal = T + FVector(0, 0, H) + FVector(FMath::Cos(BotLane * 3.f), FMath::Sin(BotLane * 3.f), 0.f) * 160.f;
	}
	// spearmen close: climb away, howl when cornered
	for (TActorIterator<AShamiramSoldier> It(GetWorld()); It; ++It)
	{
		const float D = FVector::Dist2D(It->GetActorLocation(), GetActorLocation());
		if (D < 900.f)
		{
			if (HowlCd <= 0.f && FMath::FRand() < 0.02f * (Skill + 1)) InHowl();
			Goal += FVector(0, 0, 900.f);
		}
	}
	BotGoal = Goal;
}

void AAralezSpirit::MoveField(float Dt)
{
	FVector Wish = FVector::ZeroVector;
	if (bBot)
	{
		const FVector To = BotGoal - GetActorLocation();
		Wish = To.GetSafeNormal() * FMath::Clamp(To.Size() / 600.f, 0.f, 1.f);
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
	if (bTending && RealBody && (bBot || Wish.Size() < 0.3f))
	{
		// kneel beside the fallen warrior's head and lick his wounds (only while the player isn't steering away)
		const FVector Along = (TendHead - TendFeet).GetSafeNormal2D();
		const FVector Side = FVector::CrossProduct(FVector::UpVector, Along) * (BotLane >= 0.f ? 1.f : -1.f);
		FVector Spot = TendHead + Side * 72.f;
		Spot.Z = AAralezField::GroundZ(Spot.X, Spot.Y) + 60.f;
		const FVector P = FMath::VInterpTo(GetActorLocation(), Spot, Dt, 3.f);
		Vel = (P - GetActorLocation()) / FMath::Max(Dt, 1e-3f);
		SetActorLocation(P);
		const FVector Face = (TendHead - P).GetSafeNormal2D();
		SetActorRotation(FMath::RInterpTo(GetActorRotation(), Face.Rotation(), Dt, 5.f));
		return;
	}
	const float BotScale = bBot ? (0.62f + 0.06f * Skill) : 1.f;
	const float MaxSpd = Speed * BotScale * (DashTime > 0.f ? 2.2f : 1.f);
	Vel = FMath::VInterpTo(Vel, Wish * MaxSpd, Dt, Wish.IsNearlyZero() ? 1.5f : 3.f);
	FVector P = GetActorLocation() + Vel * Dt;
	// never below the grass, never above the low clouds, never off the plain
	const float G = AAralezField::GroundZ(P.X, P.Y);
	const float Floor = RealBody ? 60.f : 110.f; // the dog can stand on the grass
	if (P.Z < G + Floor) { P.Z = G + Floor; Vel.Z = FMath::Max(0.f, Vel.Z); }
	if (P.Z > G + 9000.f) { P.Z = G + 9000.f; Vel.Z = FMath::Min(0.f, Vel.Z); }
	const float R = FVector2D(P.X, P.Y).Size();
	if (R > AAralezField::FieldRadius)
	{
		const FVector In = FVector(-P.X, -P.Y, 0.f).GetSafeNormal();
		P += In * (R - AAralezField::FieldRadius);
		Vel += In * FMath::Max(0.f, -FVector::DotProduct(Vel, In));
	}
	SetActorLocation(P);
	if (!Vel.IsNearlyZero(50.f)) SetActorRotation(FMath::RInterpTo(GetActorRotation(), Vel.Rotation(), Dt, 6.f));
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
		// personal space: rivals keep off the player (and so off the lens right behind them)
		if (APlayerController* LPC = GetWorld()->GetFirstPlayerController())
			if (APawn* PP = LPC->GetPawn())
			{
				const FVector Away = GetActorLocation() - PP->GetActorLocation();
				if (Away.Size() < 1000.f) BotGoal += Away.GetSafeNormal() * 1400.f;
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
		// the real (noisy) wall at this angle, minus body + wing span: a flat fraction of the mean radius let the
		// spirit sink into the narrow spots
		float Ang = FMath::Atan2(FVector::DotProduct(Dir, UpV), FVector::DotProduct(Dir, RightV));
		if (Ang < 0.f) Ang += 2.f * PI;
		const float Lim = FMath::Max(400.f, AAralezWorld::WallRadius(PathT, Ang) - 260.f);
		if (D > Lim)
		{
			P -= Dir * (D - Lim);
			Vel -= Dir * FMath::Max(0.f, FVector::DotProduct(Vel, Dir));
		}
		// skim over the underground river, never dive under its surface
		if (PathT > AAralezWorld::RiverT0 && PathT < AAralezWorld::RiverT1)
		{
			const float MinUp = -AAralezWorld::RiverDepth * AAralezWorld::TunnelRadius(PathT) + 140.f;
			const float CurUp = FVector::DotProduct(P - C, UpV);
			if (CurUp < MinUp)
			{
				P += UpV * (MinUp - CurUp);
				Vel -= UpV * FMath::Min(0.f, FVector::DotProduct(Vel, UpV));
			}
		}
	}
	if (PathT <= 0.001f && FVector::DotProduct(Vel, Tan) < 0.f) Vel -= Tan * FVector::DotProduct(Vel, Tan);
	SetActorLocation(P);
	if (!Vel.IsNearlyZero(50.f)) SetActorRotation(FMath::RInterpTo(GetActorRotation(), Vel.Rotation(), Dt, 6.f));
}

void AAralezSpirit::UpdateRealBody(float Dt)
{
	const float Alt = GetAltitude();
	const float Spd = Vel.Size();
	EAralezMode Want = EAralezMode::Glide;
	if (bTending) Want = EAralezMode::Lick;
	else if (Alt < 140.f && Spd < 350.f) Want = (RealBody->GetMode() == EAralezMode::Land) ? EAralezMode::Land : EAralezMode::Idle;
	else if (Vel.Z > 120.f || DashTime > 0.f || (Spd < 500.f && Alt > 200.f)) Want = EAralezMode::Flap; // climbing or hovering takes wingbeats
	// touching down: one landing clip with the wing air-brake, then it stands
	if ((Want == EAralezMode::Idle || Want == EAralezMode::Lick) && RealBody->GetMode() != EAralezMode::Idle && RealBody->GetMode() != EAralezMode::Lick && RealBody->GetMode() != EAralezMode::Land)
		Want = EAralezMode::Land;
	if (Want != RealBody->GetMode() && !(RealBody->GetMode() == EAralezMode::Land && Want == EAralezMode::Lick && Alt > 100.f)) RealBody->SetMode(Want, 0.3f);
	if (UAralezWingComponent* W = RealBody->GetWings()) W->SetFlapRate(1.f + 0.5f * FMath::Clamp(Spd / Speed, 0.f, 1.f) + (DashTime > 0.f ? 0.6f : 0.f));
	// bank into turns while flying, level on the ground
	const bool bGround = Alt < 150.f;
	FRotator R = GetActorRotation();
	R.Pitch = bGround ? 0.f : FMath::Clamp(R.Pitch, -22.f, 18.f);
	R.Roll = 0.f;
	SetActorRotation(R);
	BodyRoot->SetRelativeLocation(FVector::ZeroVector);
}

void AAralezSpirit::Animate(float Dt)
{
	if (RealBody) { UpdateRealBody(Dt); return; }
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
	if (Mat) Mat->SetScalarParameterValue(TEXT("Intensity"), (bBot ? 1.2f : 1.6f) * (1.f + Pulse * 1.5f) * (Stun > 0.f ? 0.3f + 0.3f * FMath::Sin(Flap * 6.f) : 1.f));

	// light trail
	const float Now = GetWorld()->GetTimeSeconds();
	TrailTimer -= Dt;
	if (TrailTimer <= 0.f)
	{
		TrailTimer = 0.025f;
		TrailBirth[TrailNext] = Now;
		const FVector Tail = GetActorLocation() - GetActorForwardVector() * 120.f;
		const FVector Seg = Tail - PrevTrail;
		const float Len = FMath::Min(Seg.Size(), 400.f);
		TrailLen[TrailNext] = Len / 100.f;
		if (Len > 1.f) Trail->UpdateInstanceTransform(TrailNext, FTransform(FRotationMatrix::MakeFromZ(Seg.GetSafeNormal()).Rotator(), Tail - Seg.GetSafeNormal() * Len * 0.5f, FVector(0.06f, 0.06f, Len / 100.f)), true, false, true);
		PrevTrail = Tail;
		TrailNext = (TrailNext + 1) % SpiritTrail;
	}
	FVector CamLoc = FVector(1e9f);
	if (APlayerController* CPC = GetWorld()->GetFirstPlayerController())
		if (CPC->PlayerCameraManager) CamLoc = CPC->PlayerCameraManager->GetCameraLocation();
	for (int32 i = 0; i < SpiritTrail; ++i)
	{
		const float A = Now - TrailBirth[i];
		const float Life = bBot ? 0.6f : 1.2f; // rival trails short and thin: long ones read as laser beams across the frame
		if (A < 0.f || A > Life) continue;
		FTransform T;
		Trail->GetInstanceTransform(i, T, true);
		// segments crossing right in front of the lens read as a flat band: thin them out there
		const float CamK = FMath::SmoothStep(150.f, 1200.f, (float)FVector::Dist(T.GetLocation(), CamLoc));
		const float TW = (bBot ? 0.03f : 0.055f) * FMath::Square(1.f - A / Life) * CamK + 0.001f;
		T.SetScale3D(FVector(TW, TW, TrailLen[i]));
		Trail->UpdateInstanceTransform(i, T, true, false, true);
	}
	Trail->MarkRenderStateDirty();
}

void AAralezSpirit::Tick(float Dt)
{
	Super::Tick(Dt);
	// a rival flying through the lens fills the screen with a flat pale body: hide it for that instant
	if (bBot && BodyRoot)
	{
		bool bNearLens = false;
		if (APlayerController* LPC = GetWorld()->GetFirstPlayerController())
			if (LPC->PlayerCameraManager) bNearLens = FVector::DistSquared(GetActorLocation(), LPC->PlayerCameraManager->GetCameraLocation()) < FMath::Square(450.f);
		if (BodyRoot->IsVisible() == bNearLens) BodyRoot->SetVisibility(!bNearLens, true);
	}
	bTending = GetWorld()->GetTimeSeconds() - TendStamp < 0.2f;
	DashCd = FMath::Max(0.f, DashCd - Dt);
	HowlCd = FMath::Max(0.f, HowlCd - Dt);
	DashTime = FMath::Max(0.f, DashTime - Dt);
	Stun = FMath::Max(0.f, Stun - Dt);
	if (bControl && !bFinished)
	{
		if (bField) { if (bBot) ThinkBotField(Dt); MoveField(Dt); }
		else { if (bBot) ThinkBot(Dt); Move(Dt); }
		if (bBot && Controller && !Vel.IsNearlyZero(50.f))
		{
			// autopilot camera: follow the flight but keep the horizon in view
			FRotator Want = Vel.Rotation();
			Want.Pitch = FMath::Clamp(Want.Pitch, -35.f, -4.f);
			Controller->SetControlRotation(FMath::RInterpTo(Controller->GetControlRotation(), Want, Dt, 2.5f));
		}
	}
	else
	{
		Vel = FMath::VInterpTo(Vel, FVector::ZeroVector, Dt, 2.f);
		SetActorLocation(GetActorLocation() + Vel * Dt);
	}
	Animate(Dt);
	if (!bBot && bField) UpdateCameraRig(Dt);
	if (!bBot && bField) Camera->SetFieldOfView(FMath::FInterpTo(Camera->FieldOfView, DashTime > 0.f ? 100.f : 85.f, Dt, 5.f));
	else if (!bBot)
	{
		Camera->SetFieldOfView(FMath::FInterpTo(Camera->FieldOfView, DashTime > 0.f ? 104.f : 90.f, Dt, 5.f));
		// keep the lens inside the cave: pull the boom in when the camera nears the rock
		const FVector CL = Camera->GetComponentLocation();
		const float CT = AAralezWorld::NearestT(CL, PathT);
		FVector O = CL - AAralezWorld::PathPoint(CT);
		const FVector Tn = AAralezWorld::PathTangent(CT);
		O -= Tn * FVector::DotProduct(O, Tn);
		const FVector Rv = FVector::CrossProduct(FVector::UpVector, Tn).GetSafeNormal();
		const FVector Uv = FVector::CrossProduct(Tn, Rv);
		float CA = FMath::Atan2(FVector::DotProduct(O, Uv), FVector::DotProduct(O, Rv));
		if (CA < 0.f) CA += 2.f * PI;
		const bool bTight = O.Size() > AAralezWorld::WallRadius(CT, CA) - 180.f;
		Boom->TargetArmLength = FMath::FInterpTo(Boom->TargetArmLength, bTight ? 260.f : 520.f, Dt, 4.f);
	}
}
