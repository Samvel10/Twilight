#include "FireOrb.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "VahagnCharacter.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"

AFireOrb::AFireOrb()
{
	PrimaryActorTick.bCanEverTick = true;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCastShadow(false);
	Mesh->SetMobility(EComponentMobility::Movable);
	RootComponent = Mesh;
	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Mesh);
	Light->SetIntensityUnits(ELightUnits::Unitless);
	Light->SetIntensity(2500.f);
	Light->SetAttenuationRadius(350.f);
	Light->SetLightColor(FLinearColor(1.f, 0.7f, 0.3f));
	Light->SetCastShadows(false);
	InitialLifeSpan = 25.f;
}

void AFireOrb::BeginPlay()
{
	Super::BeginPlay();
	if (UStaticMesh* S = TwAssets::Sphere()) Mesh->SetStaticMesh(S);
	Mat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Mat)
	{
		Mat->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.75f, 0.35f));
		Mat->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Mat->SetScalarParameterValue(TEXT("Intensity"), 18.f);
		Mesh->SetMaterial(0, Mat);
	}
	Mesh->SetWorldScale3D(FVector(0.55f));
	Vel = FMath::VRand() * 700.f + FVector(0, 0, 500.f);
	Phase = FMath::FRand() * 10.f;
}

void AFireOrb::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt;
	AVahagnCharacter* P = Cast<AVahagnCharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	FVector Loc = GetActorLocation();
	if (P && !P->IsDead())
	{
		const FVector To = P->GetActorLocation() - Loc;
		const float D = To.Size();
		const float Magnet = D < 3500.f && Age > 0.6f ? 1.f : 0.f;
		Vel = FMath::VInterpTo(Vel, To.GetSafeNormal() * 6000.f * Magnet, Dt, 2.5f + 4.f * Magnet);
		if (D < 220.f)
		{
			P->Heal(9.f);
			P->AddNova(7.f);
			TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, Loc, 0.6f);
			TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_hover"), 0.6f, 1.6f);
			Destroy();
			return;
		}
	}
	else
	{
		Vel = FMath::VInterpTo(Vel, FVector::ZeroVector, Dt, 1.5f);
	}
	Loc += Vel * Dt;
	Loc.Z = FMath::Max(Loc.Z, 300.f) + FMath::Sin(Age * 3.f + Phase) * 2.f;
	SetActorLocation(Loc);
	const float Pulse = 0.5f + 0.12f * FMath::Sin(Age * 9.f + Phase);
	Mesh->SetWorldScale3D(FVector(Pulse * (Age > 22.f ? (25.f - Age) / 3.f : 1.f)));
}
