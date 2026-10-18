#include "HaykWorld.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "HaykShield.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"

AHaykWorld::AHaykWorld() {}

float AHaykWorld::TerrainZ(float X, float Y)
{
	// two hills facing each other across the valley, steep walls on both sides
	const float HillHayk = 520.f * FMath::Exp(-FMath::Square((X - HaykX) / 1900.f) - FMath::Square(Y / 2600.f));
	const float HillBel = 760.f * FMath::Exp(-FMath::Square((X - BelX) / 2100.f) - FMath::Square(Y / 2800.f));
	const float Ay = FMath::Abs(Y);
	const float Walls = 5200.f * FMath::SmoothStep(3500.f, 12000.f, Ay) + 2600.f * FMath::SmoothStep(9000.f, 20000.f, FMath::Abs(X));
	const FVector2D P(X / 2400.f, Y / 2400.f);
	float N = 0.f, A = 1.f, F = 1.f;
	for (int32 o = 0; o < 4; ++o) { N += A * FMath::PerlinNoise2D(P * F + FVector2D(4.1f, 7.3f)); A *= 0.5f; F *= 2.1f; }
	const float Rough = 90.f + 900.f * FMath::SmoothStep(3000.f, 12000.f, Ay);
	return HillHayk + HillBel + Walls + N * Rough;
}

FTwSkyPreset AHaykWorld::GetSkyPreset() const
{
	FTwSkyPreset P;
	if (!bNight)
	{
		// sun low behind Bel: his army is a dark silhouette against a burning sky
		P.SunRot = FRotator(-6.f, 160.f, 0.f);
		P.SunColor = FLinearColor(1.f, 0.55f, 0.3f);
		P.SunIntensity = 8.f;
		P.FogColor = FLinearColor(0.42f, 0.16f, 0.22f);
		P.FogSunColor = FLinearColor(1.f, 0.5f, 0.2f);
		P.FogDensity = 0.02f;
		P.FogFalloff = 0.12f;
		P.FogStart = 3000.f;
		P.ShadowDistance = 9000.f;
	}
	else
	{
		// Masis at night: cold moonlight, warm torches
		P.SunRot = FRotator(-28.f, 150.f, 0.f);
		P.SunColor = FLinearColor(0.62f, 0.7f, 1.f);
		P.SunIntensity = 2.2f;
		P.MoonRot = FRotator(-50.f, -20.f, 0.f);
		P.MoonColor = FLinearColor(0.35f, 0.4f, 0.9f);
		P.MoonIntensity = 0.4f;
		P.FogColor = FLinearColor(0.022f, 0.03f, 0.07f);
		P.FogSunColor = FLinearColor(0.3f, 0.4f, 0.8f);
		P.FogDensity = 0.025f;
		P.Exposure = 1.f;
		// the moon drives the atmosphere, so it must not paint a blue day sky: darken the dome, add stars
		P.SkyLuminance = FLinearColor(0.035f, 0.045f, 0.12f);
		P.Stars = 1400;
		P.bMoonDisc = true;
		P.EmberColor = FLinearColor(1.f, 0.55f, 0.2f);
		P.SkyLightIntensity = 0.75f;
		P.SkyLightColor = FLinearColor(0.6f, 0.68f, 1.f);
		P.GainShadows = FVector4(0.85f, 0.92f, 1.2f, 1.f);
		P.ShadowDistance = 9000.f;
	}
	return P;
}

void AHaykWorld::BuildLevel()
{
	UMaterialInstanceDynamic* Rock = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Rock)
	{
		Rock->SetVectorParameterValue(TEXT("Tint"), bNight ? FLinearColor(0.32f, 0.3f, 0.36f) : FLinearColor(0.5f, 0.36f, 0.3f));
		Rock->SetScalarParameterValue(TEXT("TopAmount"), bNight ? 0.4f : 0.15f);
	}
	BuildTerrain(FVector::ZeroVector, 22000.f, 16000.f, 176, 128, [](float X, float Y) { return TerrainZ(X, Y); }, Rock, true, 1200.f);

	// Masis: far behind Hayk's back is the homeland, Bel came from the south; put Masis on the horizon to the side
	UMaterialInstanceDynamic* Snow = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Rock")), this);
	if (Snow) { Snow->SetVectorParameterValue(TEXT("Tint"), FLinearColor(0.55f, 0.45f, 0.52f)); Snow->SetScalarParameterValue(TEXT("TopAmount"), 1.f); }
	BuildHeightfield(FVector(-30000.f, 70000.f, 0.f), 55000.f, 48000.f, 7, 96, true, Snow ? Snow : Rock, false);

	// pavises between the archers
	const FVector Shields[4] = { FVector(-1150.f, 480.f, 0.f), FVector(-150.f, -520.f, 0.f), FVector(800.f, 470.f, 0.f), FVector(1700.f, -460.f, 0.f) };
	for (const FVector& S : Shields)
	{
		const float Ground = FMath::Min(TerrainZ(S.X, S.Y - 80.f), TerrainZ(S.X, S.Y + 80.f));
		const FVector P(S.X, S.Y, Ground + 105.f);
		FActorSpawnParameters Sp;
		Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		GetWorld()->SpawnActor<AHaykShield>(P, FRotator(0.f, FMath::FRandRange(-12.f, 12.f), 0.f), Sp);
	}

	// armies
	BuildArmy(5200.f, 9800.f, -3800.f, 3800.f, 260, true, 11);
	BuildArmy(-7800.f, -5200.f, -2400.f, 2400.f, 90, false, 23);
}

void AHaykWorld::BuildArmy(float X0, float X1, float Y0, float Y1, int32 Count, bool bEnemy, int32 Seed)
{
	auto MakeIsm = [this](UStaticMesh* Mesh, UMaterialInterface* Mat) -> UInstancedStaticMeshComponent*
	{
		UInstancedStaticMeshComponent* C = NewObject<UInstancedStaticMeshComponent>(this);
		C->SetStaticMesh(Mesh);
		C->SetupAttachment(RootComponent);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		C->RegisterComponent();
		C->SetWorldTransform(FTransform::Identity);
		if (Mat) C->SetMaterial(0, Mat);
		ArmyParts.Add(C);
		return C;
	};
	UMaterialInstanceDynamic* Dark = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_VishapSkin")), this);
	if (Dark)
	{
		Dark->SetVectorParameterValue(TEXT("SkinColor"), bEnemy ? FLinearColor(0.02f, 0.015f, 0.02f) : FLinearColor(0.12f, 0.07f, 0.04f));
		Dark->SetVectorParameterValue(TEXT("VeinColor"), bEnemy ? FLinearColor(1.f, 0.1f, 0.03f) : FLinearColor(1.f, 0.6f, 0.2f));
		Dark->SetScalarParameterValue(TEXT("VeinIntensity"), 0.6f); Dark->SetScalarParameterValue(TEXT("RimIntensity"), 0.35f); Dark->SetVectorParameterValue(TEXT("RimColor"), FLinearColor(1.f, 0.55f, 0.25f));
	}
	UMaterialInstanceDynamic* Fire = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Fire) { Fire->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.45f, 0.12f)); Fire->SetScalarParameterValue(TEXT("GlowMode"), 1.f); Fire->SetScalarParameterValue(TEXT("Intensity"), 25.f); }

	UInstancedStaticMeshComponent* Bodies = MakeIsm(TwAssets::Cone(), Dark);
	UInstancedStaticMeshComponent* Shields = MakeIsm(TwAssets::Cylinder(), Dark);
	UInstancedStaticMeshComponent* Heads = MakeIsm(TwAssets::Sphere(), Dark);
	UInstancedStaticMeshComponent* Spears = MakeIsm(TwAssets::Cylinder(), Dark);
	UInstancedStaticMeshComponent* Torches = MakeIsm(TwAssets::Sphere(), Fire);

	FRandomStream R(Seed);
	TArray<FVector> TorchSpots;
	for (int32 i = 0; i < Count; ++i)
	{
		const float X = R.FRandRange(X0, X1), Y = R.FRandRange(Y0, Y1);
		const float Z = TerrainZ(X, Y);
		const float H = R.FRandRange(0.9f, 1.1f) * (bEnemy ? 1.15f : 1.f);
		// a robed warrior: cone body, round head, a round shield facing the valley
		const float Face = bEnemy ? -1.f : 1.f;
		Bodies->AddInstance(FTransform(FRotator(0, 0, R.FRandRange(-3.f, 3.f)), FVector(X, Y, Z + 82.f * H), FVector(0.62f, 0.55f, 1.65f * H)), true);
		Heads->AddInstance(FTransform(FRotator::ZeroRotator, FVector(X, Y, Z + 172.f * H), FVector(0.24f * H)), true);
		if (R.FRand() < 0.55f) Shields->AddInstance(FTransform(FRotator(90.f, 0.f, 0.f), FVector(X + 32.f * Face, Y + 8.f, Z + 105.f * H), FVector(0.75f, 0.75f, 0.06f)), true);
		if (R.FRand() < 0.6f)
			Spears->AddInstance(FTransform(FRotator(0, 0, R.FRandRange(-8.f, 8.f)), FVector(X + 22.f, Y, Z + 170.f * H), FVector(0.04f, 0.04f, 3.4f * H)), true);
		if (R.FRand() < 0.22f)
		{
			const FVector T(X - 20.f, Y + 18.f, Z + 230.f * H);
			Torches->AddInstance(FTransform(FRotator::ZeroRotator, T, FVector(0.18f)), true);
			TorchSpots.Add(T);
		}
	}
	// a handful of real lights among the torches (cheap: no shadows)
	for (int32 i = 0; i < FMath::Min(6, TorchSpots.Num()); ++i)
	{
		UPointLightComponent* L = NewObject<UPointLightComponent>(this);
		L->SetupAttachment(RootComponent);
		L->RegisterComponent();
		L->SetWorldLocation(TorchSpots[i * TorchSpots.Num() / 6]);
		L->SetIntensityUnits(ELightUnits::Unitless);
		L->SetIntensity(12000.f);
		L->SetAttenuationRadius(1600.f);
		L->SetLightColor(FLinearColor(1.f, 0.45f, 0.15f));
		L->SetCastShadows(false);
	}
}
