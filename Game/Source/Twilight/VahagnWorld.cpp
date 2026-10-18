#include "VahagnWorld.h"
#include "Twilight.h"
#include "TwAssets.h"

#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AVahagnWorld::AVahagnWorld()
{
	Sea = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Sea"));
	Sea->SetupAttachment(RootComponent);
}

void AVahagnWorld::BuildLevel()
{
	BuildSea();
	BuildIslands();
}

void AVahagnWorld::BuildSea()
{
	if (UStaticMesh* PlaneMesh = TwAssets::Plane()) Sea->SetStaticMesh(PlaneMesh);
	Sea->SetMobility(EComponentMobility::Movable);
	Sea->SetWorldLocation(FVector(0, 0, 0));
	Sea->SetWorldScale3D(FVector(5000.f, 5000.f, 1.f)); // 5 km
	Sea->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Sea->SetCastShadow(false);
	UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Water_Purple")), this);
	if (M)
	{
		M->SetVectorParameterValue(TEXT("DeepColor"), FLinearColor(0.10f, 0.02f, 0.14f));
		Sea->SetMaterial(0, M);
	}
}

void AVahagnWorld::BuildVishapakar(const FVector& Base, float Yaw, float Scale)
{
	UStaticMesh* Cube = TwAssets::Cube();
	UMaterialInstanceDynamic* Stone = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Stone) Stone->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.5f, 0.42f, 0.45f));
	UMaterialInstanceDynamic* Glyph = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Glyph) { Glyph->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.4f, 0.1f)); Glyph->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Glyph->SetScalarParameterValue(TEXT("Intensity"), 12.f); }

	auto Part = [&](const FVector& Rel, const FVector& Scl, UMaterialInterface* M)
	{
		UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
		C->SetStaticMesh(Cube);
		C->SetupAttachment(RootComponent);
		C->RegisterComponent();
		const FTransform Tr(FRotator(0, Yaw, 0), Base);
		C->SetWorldLocationAndRotation(Tr.TransformPosition(Rel * Scale), FRotator(0, Yaw, 0));
		C->SetWorldScale3D(Scl * Scale);
		C->SetCollisionEnabled(M == Glyph ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryAndPhysics);
		C->SetCollisionObjectType(ECC_WorldStatic);
		C->SetCastShadow(M != Glyph);
		if (M) C->SetMaterial(0, M);
	};
	// tall stele (cube is 100 cm): 4 m wide, 2 m deep, 18 m tall, slightly tapered by a cap
	Part(FVector(0, 0, 900), FVector(4.f, 1.8f, 18.f), Stone);
	Part(FVector(0, 0, 1850), FVector(3.4f, 1.6f, 1.2f), Stone);
	// glowing carved vishap-head and wavy body lines on the face
	Part(FVector(95, 0, 1500), FVector(0.1f, 2.4f, 0.25f), Glyph);
	Part(FVector(95, 0, 1300), FVector(0.1f, 1.6f, 0.2f), Glyph);
	Part(FVector(95, 0, 1000), FVector(0.1f, 2.0f, 0.2f), Glyph);
	Part(FVector(95, 0, 700), FVector(0.1f, 1.2f, 0.2f), Glyph);
	Part(FVector(95, 0, 1150), FVector(0.1f, 0.2f, 6.0f), Glyph);

	UPointLightComponent* L = NewObject<UPointLightComponent>(this);
	L->SetupAttachment(RootComponent);
	L->RegisterComponent();
	L->SetWorldLocation(Base + FRotator(0, Yaw, 0).RotateVector(FVector(400, 0, 1200)) * Scale);
	L->SetIntensityUnits(ELightUnits::Unitless);
	L->SetIntensity(30000.f);
	L->SetAttenuationRadius(3500.f * Scale);
	L->SetLightColor(FLinearColor(1.f, 0.4f, 0.12f));
	L->SetCastShadows(false);
}

void AVahagnWorld::BuildIslands()
{
	UMaterialInstanceDynamic* Rock = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Rock) Rock->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.42f, 0.3f, 0.34f));
	UMaterialInstanceDynamic* Snow = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Snow) { Snow->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.5f, 0.38f, 0.45f)); Snow->SetScalarParameterValue(TEXT("TopAmount"), 1.f); }

	// ring of cliffs around the arena (visual boundary, collidable)
	FRandomStream Rs(4242);
	const int32 Ring = 11;
	for (int32 i = 0; i < Ring; ++i)
	{
		const float A = 2.f * PI * i / Ring + Rs.FRandRange(-0.12f, 0.12f);
		const float Dist = Rs.FRandRange(60000.f, 72000.f);
		const float Rad = Rs.FRandRange(11000.f, 17000.f);
		const float Hgt = Rs.FRandRange(7000.f, 16000.f);
		BuildHeightfield(FVector(FMath::Cos(A) * Dist, FMath::Sin(A) * Dist, 0.f), Rad, Hgt, 10 + i, 56, false, Rock, true);
	}
	// three inner islands with vishapakar stones (Aragats-like plateaus)
	const FVector Inner[3] = { FVector(16000, -9000, 0), FVector(-21000, -14000, 0), FVector(-6000, 25000, 0) };
	for (int32 i = 0; i < 3; ++i)
	{
		const float Rad = 7000.f + i * 900.f;
		const float Hgt = 2600.f + i * 700.f;
		BuildHeightfield(Inner[i], Rad, Hgt, 50 + i, 60, false, Rock, true);
		const float Top = HillHeight(0.f, 0.f, Rad, Hgt, 50 + i, false);
		BuildVishapakar(Inner[i] + FVector(0, 0, Top - 150.f), 30.f + i * 70.f, 1.2f);
	}
	// Masis on the horizon, catching the last sun (no collision, far away)
	BuildHeightfield(FVector(-150000.f, -60000.f, 0.f), 60000.f, 52000.f, 7, 96, true, Snow ? Snow : Rock, false);
}

