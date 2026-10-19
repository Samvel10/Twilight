#include "HaykWorld.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/TextureCube.h"
#include "Camera/CameraActor.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Misc/PackageName.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HaykVanHeight.inl"
#include "TwGrass.h"

static bool GHaykVan = false;
bool AHaykWorld::IsVanActive() { return GHaykVan; }

// game frame: +X runs from Hayk to Bel. The Van level is turned -90 deg so the DEM's south (+Y) becomes +X,
// and shifted so the midpoint between the two archers sits at the origin.
static float VanTerrainZ(float X, float Y)
{
	const double DX = -Y / 100.0 + VanMidX, DY = X / 100.0 + VanMidY;   // DEM metres
	const double U = (DX - VanX0) / VanSp, V = (DY - VanY0) / VanSp;
	const int32 I = FMath::Clamp((int32)FMath::FloorToDouble(U), 0, VanN - 2), J = FMath::Clamp((int32)FMath::FloorToDouble(V), 0, VanN - 2);
	const double FU = FMath::Clamp(U - I, 0.0, 1.0), FV = FMath::Clamp(V - J, 0.0, 1.0);
	auto Z = [](int32 i, int32 j) { return (double)VanZ[j * VanN + i]; };
	double H;
	if (FU + FV <= 1.0) H = Z(I, J) + (Z(I + 1, J) - Z(I, J)) * FU + (Z(I, J + 1) - Z(I, J)) * FV;
	else H = Z(I + 1, J + 1) + (Z(I, J + 1) - Z(I + 1, J + 1)) * (1.0 - FU) + (Z(I + 1, J) - Z(I + 1, J + 1)) * (1.0 - FV);
	return (float)((H - VanMidZ) * 100.0);
}
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
	if (GHaykVan) return VanTerrainZ(X, Y);
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
	if (!bNight && !FParse::Param(FCommandLine::Get(), TEXT("TwOldValley")) && FPackageName::DoesPackageExist(TEXT("/Game/Test/L_Van")))
	{
		// Lake Van at sunset (highlands kit values); the level is turned -90 deg, so the sun turns with it
		P.SunRot = FRotator(-8.f, -105.f, 0.f);
		P.SunColor = FLinearColor(1.f, 0.56f, 0.32f);
		P.SunIntensity = 11.f;
		P.MoonIntensity = 0.f;
		P.FogColor = FLinearColor(0.36f, 0.42f, 0.55f);
		P.FogSunColor = FLinearColor(1.f, 0.5f, 0.25f);
		P.FogDensity = 0.00019f;
		P.FogFalloff = 0.0067f;
		P.FogStart = 0.f;
		P.FogMaxOpacity = 1.f;
		P.Exposure = 0.f;
		P.SkyLightIntensity = 0.65f;
		P.SkyLightColor = FLinearColor(1.f, 1.f, 1.f);
		P.LowerHemisphere = FLinearColor(0.03f, 0.035f, 0.04f);
		P.SkyLuminance = FLinearColor(1.f, 1.f, 1.f);
		P.GainShadows = FVector4(1.f, 1.f, 1.f, 1.f);
		P.GainHighlights = FVector4(1.f, 1.f, 1.f, 1.f);
		P.Saturation = FVector4(1.08f, 1.08f, 1.08f, 1.08f);
		P.ShadowDistance = 12000.f;
		return P;
	}
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

void AHaykWorld::StreamVan()
{
	GHaykVan = true;
	bool bOk = false;
	const FVector Off(-VanMidY * 100.0, VanMidX * 100.0, -VanMidZ * 100.0);
	EnvLevel = ULevelStreamingDynamic::LoadLevelInstance(GetWorld(), TEXT("/Game/Test/L_Van"), Off, FRotator(0.f, -90.f, 0.f), bOk);
	if (EnvLevel) { EnvLevel->SetShouldBeVisible(true); EnvLevel->bShouldBlockOnLoad = true; }
	GetWorld()->FlushLevelStreaming();
	int32 Removed = 0;
	if (ULevel* L = EnvLevel ? EnvLevel->GetLoadedLevel() : nullptr)
		for (AActor* A : L->Actors)
		{
			if (!A) continue;
			bool bDrop = A->IsA<ADirectionalLight>() || A->IsA<ASkyLight>() || A->IsA<AExponentialHeightFog>() || A->IsA<APostProcessVolume>() || A->IsA<ACameraActor>()
				|| A->FindComponentByClass<USkyAtmosphereComponent>() != nullptr;
			if (AStaticMeshActor* SM = Cast<AStaticMeshActor>(A))
				if (UMaterialInterface* M = SM->GetStaticMeshComponent() ? SM->GetStaticMeshComponent()->GetMaterial(0) : nullptr)
					bDrop |= M->GetName().Contains(TEXT("HLSky"));
			if (bDrop) { A->Destroy(); ++Removed; }
		}
	UE_LOG(LogTwilight, Display, TEXT("[TwEnv] stream L_Van ok=%d removed=%d"), bOk ? 1 : 0, Removed);
	if (Fog) Fog->SetFogCutoffDistance(0.f);
}

void AHaykWorld::BuildSkyDome(float Yaw)
{
	UMaterialInterface* M = TwAssets::Material(TEXT("M_SkyHDRI"));
	UMaterialInstanceDynamic* Sky = M ? UMaterialInstanceDynamic::Create(M, this) : nullptr;
	if (!Sky) return;
	if (UTextureCube* Cube = LoadObject<UTextureCube>(nullptr, TEXT("/Game/Env/HDRI/kloppenheim_06_puresky_4k.kloppenheim_06_puresky_4k")))
		Sky->SetTextureParameterValue(TEXT("SkyCube"), Cube);
	FParse::Value(FCommandLine::Get(), TEXT("TwSkyYaw="), Yaw);
	Sky->SetScalarParameterValue(TEXT("Yaw"), Yaw);
	Sky->SetScalarParameterValue(TEXT("Exposure"), 0.8f);
	UStaticMeshComponent* Dome = NewObject<UStaticMeshComponent>(this);
	Dome->SetStaticMesh(TwAssets::Sphere());
	Dome->SetupAttachment(RootComponent);
	Dome->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dome->SetCastShadow(false);
	Dome->SetWorldScale3D(FVector(400000.f));
	Dome->SetMaterial(0, Sky);
	Dome->RegisterComponent();
}

void AHaykWorld::BuildRealArmy(float X0, float X1, int32 Rows, int32 Cols, bool bEnemy, int32 Seed)
{
	const TCHAR* C = bEnemy ? TEXT("Babsoldc") : TEXT("Armsoldc");
	USkeletalMesh* Mesh = TwAssets::Human(C);
	if (!Mesh) return;
	UAnimSequence* Idle = TwAssets::HumanAnim(C, TEXT("MM_Idle"));
	UStaticMesh* SpearMesh = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Twilight/Humans/Props/Spear2/spear/StaticMeshes/spear.spear"));
	FRandomStream R(Seed);
	const float Face = bEnemy ? 180.f : 0.f; // both armies look across the valley at each other
	for (int32 r = 0; r < Rows; ++r)
		for (int32 c = 0; c < Cols; ++c)
		{
			const float X = FMath::Lerp(X0, X1, Rows > 1 ? float(r) / (Rows - 1) : 0.f) + R.FRandRange(-60.f, 60.f);
			const float Y = (c - (Cols - 1) * 0.5f) * 170.f + R.FRandRange(-40.f, 40.f) + (r % 2) * 85.f;
			USkeletalMeshComponent* S = NewObject<USkeletalMeshComponent>(this);
			S->SetSkeletalMesh(Mesh);
			S->SetupAttachment(RootComponent);
			S->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			S->SetCastShadow(r < 2);
			S->bEnableUpdateRateOptimizations = true;
			S->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::OnlyTickPoseWhenRendered;
			S->RegisterComponent();
			S->SetWorldLocationAndRotation(FVector(X, Y, TerrainZ(X, Y)), FRotator(0.f, Face - 90.f + R.FRandRange(-8.f, 8.f), 0.f));
			S->SetWorldScale3D(FVector(R.FRandRange(0.95f, 1.05f)));
			for (int32 i = 0; i < 3; ++i) S->SetCustomPrimitiveDataFloat(i, R.FRand());
			if (Idle)
			{
				S->SetAnimationMode(EAnimationMode::AnimationSingleNode);
				S->PlayAnimation(Idle, true);
				S->SetPosition(R.FRand() * 2.f, false);
				S->SetPlayRate(R.FRandRange(0.85f, 1.15f));
			}
			if (SpearMesh && R.FRand() < 0.7f)
			{
				UStaticMeshComponent* Sp = NewObject<UStaticMeshComponent>(this);
				Sp->SetStaticMesh(SpearMesh);
				Sp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				Sp->SetCastShadow(r < 2);
				Sp->SetupAttachment(S, TEXT("hand_r"));
				Sp->SetRelativeTransform(FTransform(FRotator(21.03f, -88.92f, 85.09f), FVector(-93.86f, -4.67f, -7.52f), FVector(1.0188f)));
				Sp->RegisterComponent();
			}
			Soldiers.Add(S);
		}
}

void AHaykWorld::BuildLevel()
{
	if (!bNight && !FParse::Param(FCommandLine::Get(), TEXT("TwOldValley")) && FPackageName::DoesPackageExist(TEXT("/Game/Test/L_Van")))
	{
		// the real east shore of Lake Van, where tradition puts the battle (Hayots Dzor)
		StreamVan();
		BuildSkyDome(0.102f);
		const FVector Shields[4] = { FVector(-1150.f, 480.f, 0.f), FVector(-150.f, -520.f, 0.f), FVector(800.f, 470.f, 0.f), FVector(1700.f, -460.f, 0.f) };
		for (const FVector& S : Shields)
		{
			const FVector P(S.X, S.Y, FMath::Min(TerrainZ(S.X, S.Y - 80.f), TerrainZ(S.X, S.Y + 80.f)) + 105.f);
			FActorSpawnParameters Sp;
			Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			GetWorld()->SpawnActor<AHaykShield>(P, FRotator(0.f, FMath::FRandRange(-12.f, 12.f), 0.f), Sp);
		}
		// Bel's host fills the slope behind him; Hayk's kin stand behind Hayk
		BuildRealArmy(5200.f, 8200.f, 4, 9, true, 11);
		BuildRealArmy(-5200.f, -7000.f, 3, 7, false, 23);
		// steppe grass and poppies over the duel ground
		TwGrass::Scatter(this, FVector2D(0.f, 0.f), FVector2D(9000.f, 6000.f), 2.2f, [](float X, float Y) { return TerrainZ(X, Y); }, 7, 0.05f);
		return;
	}
	GHaykVan = false;
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
