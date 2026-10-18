#include "HaykShield.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AHaykShield::AHaykShield()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	Board = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Board"));
	Board->SetupAttachment(Root);
	Board->SetCollisionProfileName(TEXT("BlockAll"));
	Board->SetHiddenInGame(true);
}

void AHaykShield::BeginPlay()
{
	Super::BeginPlay();
	Board->SetStaticMesh(TwAssets::Cube());
	Board->SetRelativeLocation(FVector(0.f, 0.f, 0.f));
	Board->SetRelativeScale3D(FVector(0.14f, 1.6f, 2.3f)); // collision only

	UMaterialInstanceDynamic* Wood = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Wood) Wood->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.62f, 0.36f, 0.18f));
	UMaterialInstanceDynamic* Bronze = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (Bronze) { Bronze->SetVectorParameterValue(TEXT("SkinColor"), FLinearColor(0.3f, 0.17f, 0.07f)); Bronze->SetScalarParameterValue(TEXT("Metallic"), 0.8f); Bronze->SetScalarParameterValue(TEXT("VeinIntensity"), 1.5f); Bronze->SetVectorParameterValue(TEXT("VeinColor"), FLinearColor(1.f, 0.6f, 0.2f)); Bronze->SetScalarParameterValue(TEXT("RimIntensity"), 0.3f); }
	UMaterialInstanceDynamic* Edge = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Edge) { Edge->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.5f, 0.18f)); Edge->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Edge->SetScalarParameterValue(TEXT("Intensity"), 1.5f); }

	auto Part = [this](UStaticMesh* M, const FVector& Loc, const FRotator& Rot, const FVector& Scl, UMaterialInterface* Mat)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(M);
		C->SetupAttachment(Root);
		C->SetRelativeLocationAndRotation(Loc, Rot);
		C->SetRelativeScale3D(Scl);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		if (Mat) C->SetMaterial(0, Mat);
		C->RegisterComponent();
		Parts.Add(C);
	};
	// five vertical planks with small gaps, a top rail, a bronze boss and a warm edge glow
	FRandomStream R(GetUniqueID());
	for (int32 k = 0; k < 5; ++k)
	{
		const float Hgt = R.FRandRange(2.1f, 2.4f);
		Part(TwAssets::Cube(), FVector(0.f, -64.f + k * 32.f, (Hgt - 2.3f) * 50.f), FRotator::ZeroRotator, FVector(0.1f, 0.3f, Hgt), Wood);
	}
	Part(TwAssets::Cube(), FVector(-6.f, 0.f, 95.f), FRotator::ZeroRotator, FVector(0.08f, 1.7f, 0.12f), Wood);
	Part(TwAssets::Sphere(), FVector(7.f, 0.f, 10.f), FRotator::ZeroRotator, FVector(0.12f, 0.35f, 0.35f), Bronze);
	Part(TwAssets::Cube(), FVector(6.f, 0.f, 116.f), FRotator::ZeroRotator, FVector(0.02f, 1.6f, 0.03f), Edge);
	Part(TwAssets::Cube(), FVector(6.f, -81.f, 0.f), FRotator::ZeroRotator, FVector(0.02f, 0.03f, 2.3f), Edge);
	Part(TwAssets::Cube(), FVector(6.f, 81.f, 0.f), FRotator::ZeroRotator, FVector(0.02f, 0.03f, 2.3f), Edge);
	Part(TwAssets::Cube(), FVector(-60.f, 0.f, -30.f), FRotator(35.f, 0.f, 0.f), FVector(0.06f, 0.08f, 1.3f), Wood);
	SetActorRotation(GetActorRotation() + FRotator(-8.f, 0.f, 0.f)); // leaning back
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
		TArray<AActor*> Att;
		GetAttachedActors(Att);
		for (AActor* X : Att) if (X) X->Destroy();
		TwFx::Burst(GetWorld(), TwFx::EFx::Smoke, GetActorLocation(), 1.5f);
		TwFx::Burst(GetWorld(), TwFx::EFx::FireballImpact, GetActorLocation() + FVector(0, 0, 100), 1.f);
		TwFx::Sound(GetWorld(), TEXT("sfx_fireball_impact"), GetActorLocation(), 1.f, 0.7f);
		SetActorEnableCollision(false);
		SetActorHiddenInGame(true);
		SetLifeSpan(10.f);
	}
}
