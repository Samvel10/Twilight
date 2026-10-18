#include "VahagnWorld.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/AudioComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Kismet/GameplayStatics.h"

AVahagnWorld::AVahagnWorld()
{
	PrimaryActorTick.bCanEverTick = true;
	USceneComponent* Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;

	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Sun"));
	Sun->SetupAttachment(Root);
	Moon = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Moon"));
	Moon->SetupAttachment(Root);
	Atmosphere = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("Atmosphere"));
	Atmosphere->SetupAttachment(Root);
	SkyLight = CreateDefaultSubobject<USkyLightComponent>(TEXT("SkyLight"));
	SkyLight->SetupAttachment(Root);
	Fog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("Fog"));
	Fog->SetupAttachment(Root);
	Post = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Post"));
	Post->SetupAttachment(Root);
	Sea = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Sea"));
	Sea->SetupAttachment(Root);
	SkyDome = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("SkyDome"));
	SkyDome->SetupAttachment(Root);
	Music = CreateDefaultSubobject<UAudioComponent>(TEXT("Music"));
	Music->SetupAttachment(Root);
	Music->bAutoActivate = false;
	Music->bIsUISound = true;
	MusicB = CreateDefaultSubobject<UAudioComponent>(TEXT("MusicB"));
	MusicB->SetupAttachment(Root);
	MusicB->bAutoActivate = false;
	MusicB->bIsUISound = true;
}

void AVahagnWorld::BeginPlay()
{
	Super::BeginPlay();
	BuildSky();
	BuildSea();
	BuildIslands();
	PlayMusic(TEXT("music_menu"));
}

void AVahagnWorld::BuildSky()
{
	// Low sunset sun: long warm light across the purple sea
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->SetWorldRotation(FRotator(-7.f, 20.f, 0.f));
	Sun->SetIntensity(9.f);
	Sun->SetLightColor(FLinearColor(1.f, 0.62f, 0.38f));
	Sun->SetAtmosphereSunLight(true);
	Sun->SetAtmosphereSunLightIndex(0);
	Sun->SetCastShadows(true);
	Sun->SetDynamicShadowDistanceMovableLight(12000.f);
	Sun->SetDynamicShadowCascades(2);
	Sun->bUseInsetShadowsForMovableObjects = false;
	Sun->SetLightSourceAngle(2.f);
	Sun->SetEnableLightShaftBloom(true);
	Sun->SetBloomScale(0.35f);
	Sun->SetBloomThreshold(4.f);
	Sun->SetBloomTint(FColor(255, 150, 90));

	// cool purple rim light from the opposite side (the "night" half of the sky)
	Moon->SetMobility(EComponentMobility::Movable);
	Moon->SetWorldRotation(FRotator(-35.f, 200.f, 0.f));
	Moon->SetIntensity(0.6f);
	Moon->SetLightColor(FLinearColor(0.55f, 0.45f, 1.f));
	Moon->SetCastShadows(false);
	Moon->SetAtmosphereSunLight(false);

	Atmosphere->SetMobility(EComponentMobility::Movable);
	Atmosphere->SetRayleighScatteringScale(0.0331f * 1.15f);
	Atmosphere->SetMieScatteringScale(0.006f);
	Atmosphere->SetMieAnisotropy(0.85f);
	Atmosphere->SetSkyLuminanceFactor(FLinearColor(1.05f, 0.85f, 1.2f));

	SkyLight->SetMobility(EComponentMobility::Movable);
	SkyLight->SourceType = ESkyLightSourceType::SLS_CapturedScene;
	SkyLight->bRealTimeCapture = false;
	SkyLight->SetIntensity(1.2f);
	SkyLight->SetLightColor(FLinearColor(0.9f, 0.75f, 1.f));
	SkyLight->SetLowerHemisphereColor(FLinearColor(0.12f, 0.03f, 0.15f));
	SkyLight->bLowerHemisphereIsBlack = false;

	Fog->SetMobility(EComponentMobility::Movable);
	Fog->SetFogDensity(0.012f);
	Fog->SetFogHeightFalloff(0.08f);
	Fog->SetWorldLocation(FVector(0, 0, 0));
	Fog->SetFogInscatteringColor(FLinearColor(0.32f, 0.10f, 0.38f));
	Fog->SetDirectionalInscatteringColor(FLinearColor(1.f, 0.42f, 0.18f));
	Fog->SetDirectionalInscatteringExponent(6.f);
	Fog->SetDirectionalInscatteringStartDistance(3000.f);
	Fog->SetStartDistance(4500.f);
	Fog->SetFogMaxOpacity(0.92f);
	Fog->SetVolumetricFog(false);

	// Post-process: warm highlights, violet shadows, strong bloom, cinematic vignette
	Post->bUnbound = true;
	Post->Priority = 1.f;
	FPostProcessSettings& P = Post->Settings;
	P.bOverride_AutoExposureMethod = true; P.AutoExposureMethod = EAutoExposureMethod::AEM_Manual;
	P.bOverride_AutoExposureBias = true; P.AutoExposureBias = 11.5f;
	P.bOverride_AutoExposureApplyPhysicalCameraExposure = true; P.AutoExposureApplyPhysicalCameraExposure = false;
	P.bOverride_BloomIntensity = true; P.BloomIntensity = 1.35f;
	P.bOverride_BloomThreshold = true; P.BloomThreshold = 1.2f;
	P.bOverride_VignetteIntensity = true; P.VignetteIntensity = 0.55f;
	P.bOverride_FilmGrainIntensity = true; P.FilmGrainIntensity = 0.12f;
	P.bOverride_ColorSaturation = true; P.ColorSaturation = FVector4(1.08f, 1.02f, 1.12f, 1.1f);
	P.bOverride_ColorContrast = true; P.ColorContrast = FVector4(1.f, 1.f, 1.f, 1.08f);
	P.bOverride_ColorGainShadows = true; P.ColorGainShadows = FVector4(0.95f, 0.85f, 1.15f, 1.f);
	P.bOverride_ColorGainHighlights = true; P.ColorGainHighlights = FVector4(1.08f, 0.98f, 0.9f, 1.f);
	P.bOverride_SceneFringeIntensity = true; P.SceneFringeIntensity = 0.6f;
	P.bOverride_LensFlareIntensity = true; P.LensFlareIntensity = 0.35f;
	P.bOverride_MotionBlurAmount = true; P.MotionBlurAmount = 0.f;
	P.bOverride_AmbientOcclusionIntensity = true; P.AmbientOcclusionIntensity = 0.35f;

	SkyRecaptureTimer = 0.3f;
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
	// sky dome fallback only if the atmosphere is unavailable (kept hidden by default)
	SkyDome->SetVisibility(false);
}

static float IslandHeight(float X, float Y, float R, float H, int32 Seed, bool bTwin)
{
	const float D = FMath::Sqrt(X * X + Y * Y) / R;
	if (D >= 1.f) return -900.f;
	const FVector2D P(X / 2600.f + Seed * 17.3f, Y / 2600.f - Seed * 9.1f);
	float N = 0.f, A = 1.f, F = 1.f;
	for (int32 o = 0; o < 5; ++o) { N += A * FMath::PerlinNoise2D(P * F); A *= 0.5f; F *= 2.05f; }
	const float Ridge = 1.f - FMath::Abs(FMath::PerlinNoise2D(P * 0.7f + FVector2D(3.3f, 1.1f)));
	float Shape = FMath::Pow(FMath::Max(0.f, 1.f - D), 1.6f);
	if (bTwin)
	{
		// Masis: big cone + smaller Sis to the side
		const float D2 = FMath::Sqrt(FMath::Square(X - R * 0.62f) + FMath::Square(Y + R * 0.18f)) / (R * 0.45f);
		Shape = FMath::Max(FMath::Pow(FMath::Max(0.f, 1.f - D), 1.25f), 0.55f * FMath::Pow(FMath::Max(0.f, 1.f - D2), 1.2f));
	}
	return -900.f + (H + 900.f) * Shape * (0.78f + 0.22f * N + 0.15f * Ridge * Shape);
}

UProceduralMeshComponent* AVahagnWorld::BuildIsland(const FVector& Center, float Radius, float Height, int32 Seed, int32 Res, bool bTwin, UMaterialInterface* Mat, bool bCollide)
{
	UProceduralMeshComponent* PM = NewObject<UProceduralMeshComponent>(this);
	PM->SetupAttachment(RootComponent);
	PM->RegisterComponent();
	PM->SetWorldLocation(Center);
	PM->bUseComplexAsSimpleCollision = true;
	PM->SetCastShadow(true);

	TArray<FVector> V; TArray<int32> T; TArray<FVector> N; TArray<FVector2D> UV; TArray<FLinearColor> Col; TArray<FProcMeshTangent> Tan;
	const int32 R1 = Res + 1;
	const float Step = 2.f * Radius / Res;
	V.Reserve(R1 * R1);
	for (int32 y = 0; y <= Res; ++y)
	{
		for (int32 x = 0; x <= Res; ++x)
		{
			const float X = -Radius + x * Step, Y = -Radius + y * Step;
			const float Z = IslandHeight(X, Y, Radius, Height, Seed, bTwin);
			V.Add(FVector(X, Y, Z));
			UV.Add(FVector2D((Center.X + X) / 1500.f, (Center.Y + Y) / 1500.f));
			Col.Add(FLinearColor(Z / FMath::Max(Height, 1.f), 0, 0, 1));
		}
	}
	N.SetNum(V.Num());
	for (int32 y = 0; y <= Res; ++y)
	{
		for (int32 x = 0; x <= Res; ++x)
		{
			const int32 i = y * R1 + x;
			const float hl = V[y * R1 + FMath::Max(x - 1, 0)].Z, hr = V[y * R1 + FMath::Min(x + 1, Res)].Z;
			const float hd = V[FMath::Max(y - 1, 0) * R1 + x].Z, hu = V[FMath::Min(y + 1, Res) * R1 + x].Z;
			N[i] = FVector(hl - hr, hd - hu, 2.f * Step).GetSafeNormal();
			Tan.Add(FProcMeshTangent(FVector(1, 0, 0), false));
		}
	}
	for (int32 y = 0; y < Res; ++y)
	{
		for (int32 x = 0; x < Res; ++x)
		{
			const int32 a = y * R1 + x, b = a + 1, c = a + R1, d = c + 1;
			T.Append({ a, c, b, b, c, d });
		}
	}
	PM->CreateMeshSection_LinearColor(0, V, T, N, UV, Col, Tan, bCollide);
	if (Mat) PM->SetMaterial(0, Mat);
	if (bCollide)
	{
		PM->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		PM->SetCollisionObjectType(ECC_WorldStatic);
		PM->SetCollisionResponseToAllChannels(ECR_Block);
	}
	else PM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Islands.Add(PM);
	return PM;
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
		BuildIsland(FVector(FMath::Cos(A) * Dist, FMath::Sin(A) * Dist, 0.f), Rad, Hgt, 10 + i, 56, false, Rock, true);
	}
	// three inner islands with vishapakar stones (Aragats-like plateaus)
	const FVector Inner[3] = { FVector(16000, -9000, 0), FVector(-21000, -14000, 0), FVector(-6000, 25000, 0) };
	for (int32 i = 0; i < 3; ++i)
	{
		const float Rad = 7000.f + i * 900.f;
		const float Hgt = 2600.f + i * 700.f;
		BuildIsland(Inner[i], Rad, Hgt, 50 + i, 60, false, Rock, true);
		const float Top = IslandHeight(0.f, 0.f, Rad, Hgt, 50 + i, false);
		BuildVishapakar(Inner[i] + FVector(0, 0, Top - 150.f), 30.f + i * 70.f, 1.2f);
	}
	// Masis on the horizon, catching the last sun (no collision, far away)
	BuildIsland(FVector(-150000.f, -60000.f, 0.f), 60000.f, 52000.f, 7, 96, true, Snow ? Snow : Rock, false);
}

void AVahagnWorld::Tick(float Dt)
{
	Super::Tick(Dt);
	// capture the sky light a couple of times once everything is in place
	if (SkyCaptures < 2)
	{
		SkyRecaptureTimer -= Dt;
		if (SkyRecaptureTimer <= 0.f)
		{
			SkyLight->RecaptureSky();
			++SkyCaptures;
			SkyRecaptureTimer = 1.5f;
		}
	}
}

void AVahagnWorld::PlayMusic(const TCHAR* Name)
{
	USoundBase* S = TwAssets::Sound(Name);
	if (!S) return;
	UAudioComponent* From = bMusicA ? Music : MusicB;
	UAudioComponent* To = bMusicA ? MusicB : Music;
	if (From->Sound == S && From->IsPlaying()) return;
	bMusicA = !bMusicA;
	From->FadeOut(1.5f, 0.f);
	To->SetSound(S);
	To->FadeIn(1.5f, 0.55f);
}
