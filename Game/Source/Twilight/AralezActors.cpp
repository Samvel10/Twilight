#include "AralezActors.h"
#include "AralezSpirit.h"
#include "AralezWorld.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "AralezGame.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"

#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EngineUtils.h"
#include "Engine/World.h"

// ------------------------------------------------------------------ soul light
ASoulLight::ASoulLight()
{
	PrimaryActorTick.bCanEverTick = true;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCastShadow(false);
	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Mesh);
	Light->SetIntensityUnits(ELightUnits::Unitless);
	Light->SetIntensity(1800.f);
	Light->SetAttenuationRadius(450.f);
	Light->SetLightColor(FLinearColor(1.f, 0.82f, 0.45f));
	Light->SetCastShadows(false);
}

void ASoulLight::BeginPlay()
{
	Super::BeginPlay();
	Mesh->SetStaticMesh(TwAssets::Sphere());
	if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
	{
		M->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.8f, 0.4f));
		M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		M->SetScalarParameterValue(TEXT("Intensity"), 8.f);
		Mesh->SetMaterial(0, M);
	}
	Home = GetActorLocation();
	Phase = FMath::FRand() * 10.f;
	// only a few lights cast real light (iGPU budget); the rest glow through bloom
	Light->SetVisibility(FMath::FRand() < 0.12f);
	Mesh->SetWorldScale3D(FVector(0.45f));
}

void ASoulLight::Tick(float Dt)
{
	Super::Tick(Dt);
	if (bTaken) return;
	Phase += Dt;
	FVector P = GetActorLocation();
	if (!Drift.IsNearlyZero())
	{
		Home += Drift * Dt;
		Drift = FMath::VInterpTo(Drift, FVector::ZeroVector, Dt, 1.5f);
	}
	FVector Want = Home + FVector(FMath::Sin(Phase * 1.3f) * 30.f, FMath::Cos(Phase) * 30.f, FMath::Sin(Phase * 2.f) * 40.f);
	if (Puller.IsValid()) { Want = Puller->GetActorLocation(); Home = FMath::VInterpTo(Home, Want, Dt, 4.f); }
	P = FMath::VInterpTo(P, Want, Dt, Puller.IsValid() ? 6.f : 2.f);
	// never let a light fill the camera: fade it out when very close to the lens
	float CamFade = 1.f;
	if (APlayerController* PCc = GetWorld()->GetFirstPlayerController())
		if (PCc->PlayerCameraManager) CamFade = FMath::SmoothStep(120.f, 650.f, (float)FVector::Dist(P, PCc->PlayerCameraManager->GetCameraLocation()));
	SetActorTransform(FTransform(FQuat::Identity, P, FVector((0.42f + 0.08f * FMath::Sin(Phase * 6.f)) * CamFade + 0.001f)));

	// collection by a spirit (stunned victims cannot grab)
	const AAralezGameMode* GM = GetWorld()->GetAuthGameMode<AAralezGameMode>();
	if (!GM) return;
	float Nearest = TNumericLimits<float>::Max();
	for (AAralezSpirit* It : GM->GetRacers())
	{
		if (!IsValid(It) || It->IsFinished() || It->GetStun() > 0.f) continue;
		const float D = FVector::Dist(It->GetActorLocation(), P);
		Nearest = FMath::Min(Nearest, D);
		const float Grab = It->IsBot() ? 230.f : 300.f;
		if (D < Grab)
		{
			bTaken = true;
			It->AddLights(1);
			if (!It->IsBot()) TwFx::Sound2D(GetWorld(), TEXT("sfx_soul_chime"), 0.7f, 0.9f + FMath::FRand() * 0.3f);
			TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, P, It->IsBot() ? 0.2f : 0.3f);
			Destroy();
			return;
		}
	}
	SetActorTickInterval(Nearest > 7000.f ? 0.1f : 0.f);
}

// ------------------------------------------------------------------ shadow wraith
AShadowWraith::AShadowWraith()
{
	PrimaryActorTick.bCanEverTick = true;
	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	RootComponent = Body;
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetCastShadow(false);
	EyeLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("Eye"));
	EyeLight->SetupAttachment(Body);
	EyeLight->SetIntensityUnits(ELightUnits::Unitless);
	EyeLight->SetIntensity(1200.f);
	EyeLight->SetAttenuationRadius(700.f);
	EyeLight->SetLightColor(FLinearColor(1.f, 0.1f, 0.05f));
	EyeLight->SetCastShadows(false);
}

void AShadowWraith::BeginPlay()
{
	Super::BeginPlay();
	UMaterialInstanceDynamic* Dark = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (Dark)
	{
		Dark->SetVectorParameterValue(TEXT("SkinColor"), FLinearColor(0.004f, 0.003f, 0.006f));
		Dark->SetVectorParameterValue(TEXT("VeinColor"), FLinearColor(0.6f, 0.02f, 0.06f));
		Dark->SetScalarParameterValue(TEXT("VeinIntensity"), 0.12f);
		Dark->SetScalarParameterValue(TEXT("Metallic"), 0.f);
		Dark->SetScalarParameterValue(TEXT("Roughness"), 1.f);
		// a black shape with a crimson rim reads as a ghost; the lit scale pattern read as a checkered cone
		Dark->SetVectorParameterValue(TEXT("SkinColor2"), FLinearColor(0.01f, 0.005f, 0.012f));
		Dark->SetScalarParameterValue(TEXT("ScaleTiling"), 0.6f);
		Dark->SetScalarParameterValue(TEXT("RimIntensity"), 0.35f); Dark->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(0.3f, 0.01f, 0.03f)); // cave exposure is +2.2: keep it dark crimson, not pink
	}
	// a hooded robe trailing into smoke, with a small head carrying the burning eyes
	Body->SetStaticMesh(TwAssets::Sphere());
	Body->SetMaterial(0, Dark);
	Body->SetWorldScale3D(FVector(1.f));
	{
		UStaticMeshComponent* Robe = NewObject<UStaticMeshComponent>(this);
		Robe->SetStaticMesh(TwAssets::Cone());
		Robe->SetupAttachment(Body);
		Robe->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Robe->SetRelativeLocation(FVector(0.f, 0.f, -60.f));
		Robe->SetRelativeRotation(FRotator(180.f, 0.f, 0.f));
		Robe->SetRelativeScale3D(FVector(1.4f, 1.4f, 2.6f));
		Robe->SetMaterial(0, Dark);
		Robe->RegisterComponent();
	}
	UMaterialInstanceDynamic* Eye = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Eye) { Eye->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.08f, 0.04f)); Eye->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Eye->SetScalarParameterValue(TEXT("Intensity"), 9.f); }
	for (int32 s = -1; s <= 1; s += 2)
	{
		UStaticMeshComponent* E = NewObject<UStaticMeshComponent>(this);
		E->SetStaticMesh(TwAssets::Sphere());
		E->SetupAttachment(Body);
		E->SetRelativeLocation(FVector(42.f, 16.f * s, 10.f));
		E->SetRelativeScale3D(FVector(0.16f, 0.2f, 0.08f));
		E->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		E->SetMaterial(0, Eye);
		E->RegisterComponent();
	}
	// trailing smoke wisps
	for (int32 i = 0; i < 6; ++i)
	{
		UStaticMeshComponent* W = NewObject<UStaticMeshComponent>(this);
		W->SetStaticMesh(TwAssets::Sphere());
		W->SetupAttachment(Body);
		W->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		W->SetCastShadow(false);
		W->SetMaterial(0, Dark);
		W->SetRelativeLocation(FVector(-40.f - i * 28.f, 0.f, -20.f - i * 8.f));
		W->SetRelativeScale3D(FVector(0.6f, 0.25f, 0.25f) * (1.f - i * 0.12f));
		W->RegisterComponent();
		Wisps.Add(W);
	}
	// soft crimson aura so the shadow is seen against the dark rock, and a bigger body
	if (UMaterialInstanceDynamic* AuraM = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
	{
		AuraM->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.4f, 0.f, 0.03f));
		AuraM->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		AuraM->SetScalarParameterValue(TEXT("Intensity"), 0.3f);
		AuraM->SetScalarParameterValue(TEXT("Falloff"), 2.f);
		UStaticMeshComponent* Aura = NewObject<UStaticMeshComponent>(this);
		Aura->SetStaticMesh(TwAssets::Sphere());
		Aura->SetupAttachment(Body);
		Aura->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Aura->SetCastShadow(false);
		Aura->SetRelativeLocation(FVector(0.f, 0.f, -80.f));
		Aura->SetRelativeScale3D(FVector(2.2f, 2.2f, 3.4f));
		Aura->SetMaterial(0, AuraM);
		Aura->RegisterComponent();
	}
	EyeLight->SetIntensity(600.f);
	EyeLight->SetAttenuationRadius(500.f);
	SetActorScale3D(FVector(1.4f));
}

void AShadowWraith::Repel(const FVector& From)
{
	Vel = (GetActorLocation() - From).GetSafeNormal() * 4000.f;
	RepelTime = 2.5f;
	TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, GetActorLocation(), 1.5f);
}

void AShadowWraith::Tick(float Dt)
{
	// a shade flying through the lens fills the screen with a flat red cone: hide it for that instant
	if (APlayerController* LPC = GetWorld()->GetFirstPlayerController())
		if (LPC->PlayerCameraManager)
		{
			const bool bNear = FVector::DistSquared(GetActorLocation(), LPC->PlayerCameraManager->GetCameraLocation()) < FMath::Square(420.f);
			if (Body->IsVisible() == bNear) Body->SetVisibility(!bNear, true);
		}
	Super::Tick(Dt);
	Age += Dt;
	Cooldown = FMath::Max(0.f, Cooldown - Dt);
	RepelTime = FMath::Max(0.f, RepelTime - Dt);
	const FVector P = GetActorLocation();
	FVector Target = AAralezWorld::PathPoint(PatrolT) + FVector(FMath::Sin(Age * 0.7f), FMath::Cos(Age * 0.5f), FMath::Sin(Age)) * 900.f;

	// hunt the richest spirit nearby
	AAralezSpirit* Prey = nullptr;
	float BestScore = 0.f;
	for (TActorIterator<AAralezSpirit> It(GetWorld()); It; ++It)
	{
		if (It->IsFinished() || It->GetLights() <= 0) continue;
		const float D = FVector::Dist(It->GetActorLocation(), P);
		if (D > 5000.f) continue;
		const float Score = It->GetLights() * 1.f / (D + 500.f);
		if (Score > BestScore) { BestScore = Score; Prey = *It; }
	}
	float Spd = 1500.f;
	if (Prey && RepelTime <= 0.f && Cooldown <= 0.f) { Target = Prey->GetActorLocation(); Spd = 2100.f; }
	if (RepelTime <= 0.f) Vel = FMath::VInterpTo(Vel, (Target - P).GetSafeNormal() * Spd, Dt, 1.6f);
	else Vel = FMath::VInterpTo(Vel, FVector::ZeroVector, Dt, 0.8f);
	SetActorLocation(P + Vel * Dt);
	if (!Vel.IsNearlyZero(10.f)) SetActorRotation(FMath::RInterpTo(GetActorRotation(), Vel.Rotation(), Dt, 4.f));
	for (int32 i = 0; i < Wisps.Num(); ++i)
	{
		FVector L = Wisps[i]->GetRelativeLocation();
		L.Y = FMath::Sin(Age * 3.f - i) * 14.f * i;
		Wisps[i]->SetRelativeLocation(L);
	}

	// touch: steal lights, stun briefly
	if (Prey && Cooldown <= 0.f && RepelTime <= 0.f && FVector::Dist(Prey->GetActorLocation(), P) < 320.f)
	{
		const int32 Lost = Prey->StealLights(3);
		Prey->Stunned(1.2f);
		Cooldown = 4.f;
		TwFx::Sound(GetWorld(), TEXT("sfx_wraith_hiss"), P, Prey->IsBot() ? 0.4f : 1.f);
		TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, P, 1.2f);
		// stolen lights scatter back into the tunnel
		const FVector Away = (P - Prey->GetActorLocation()).GetSafeNormal();
		for (int32 i = 0; i < Lost; ++i)
		{
			const FVector Dir = (FMath::VRand() + Away * 1.2f).GetSafeNormal();
			FActorSpawnParameters Sp;
			Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			if (ASoulLight* L = GetWorld()->SpawnActor<ASoulLight>(P + Dir * 250.f, FRotator::ZeroRotator, Sp)) L->Scatter(Dir * 1400.f);
		}
	}
}
