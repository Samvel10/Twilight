#include "HaykShield.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AHaykShield::AHaykShield()
{
	PrimaryActorTick.bCanEverTick = true;
	Board = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Board"));
	RootComponent = Board;
	Board->SetCollisionProfileName(TEXT("BlockAll"));
	Brace = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Brace"));
	Brace->SetupAttachment(Board);
	Brace->SetCollisionEnabled(ECollisionEnabled::NoCollision);
}

void AHaykShield::BeginPlay()
{
	Super::BeginPlay();
	Board->SetStaticMesh(TwAssets::Cube());
	Brace->SetStaticMesh(TwAssets::Cube());
	// 1.6 m wide, 2.3 m tall, 12 cm thick
	Board->SetWorldScale3D(FVector(0.12f, 1.6f, 2.3f));
	Brace->SetRelativeLocation(FVector(-260.f, 0.f, -20.f));
	Brace->SetRelativeRotation(FRotator(35.f, 0.f, 0.f));
	Brace->SetRelativeScale3D(FVector(0.5f, 0.06f, 0.8f));
	if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this))
	{
		M->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.55f, 0.32f, 0.16f));
		Board->SetMaterial(0, M);
		Brace->SetMaterial(0, M);
	}
	BaseRot = GetActorRotation();
}

void AHaykShield::Tick(float Dt)
{
	Super::Tick(Dt);
	if (Shake > 0.f)
	{
		Shake = FMath::Max(0.f, Shake - Dt * 3.f);
		SetActorRotation(BaseRot + FRotator(0.f, 0.f, FMath::Sin(GetWorld()->GetTimeSeconds() * 60.f) * 4.f * Shake));
	}
}

void AHaykShield::TakeArrow(const FVector& Where, bool bSpecial)
{
	Hits += bSpecial ? 2 : 1;
	Shake = 1.f;
	TwFx::Burst(GetWorld(), TwFx::EFx::Sparks, Where, 0.7f);
	if (IsBroken())
	{
		TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, GetActorLocation(), 1.5f);
		TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, GetActorLocation() + FVector(0, 0, 100), 1.f);
		TwFx::Sound(GetWorld(), TEXT("sfx_fireball_impact"), GetActorLocation(), 1.f, 0.7f);
		SetActorEnableCollision(false);
		SetActorHiddenInGame(true);
		SetLifeSpan(10.f);
	}
}
