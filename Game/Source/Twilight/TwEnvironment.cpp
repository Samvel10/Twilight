#include "TwEnvironment.h"
#include "Twilight.h"
#include "TwAssets.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/AudioComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "ProceduralMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Camera/PlayerCameraManager.h"
#include "Sound/SoundBase.h"
#include "AudioDevice.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/Engine.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

ATwEnvironment::ATwEnvironment()
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
	Music = CreateDefaultSubobject<UAudioComponent>(TEXT("Music"));
	Music->SetupAttachment(Root);
	Music->bAutoActivate = false;
	Music->bIsUISound = true;
	MusicB = CreateDefaultSubobject<UAudioComponent>(TEXT("MusicB"));
	MusicB->SetupAttachment(Root);
	MusicB->bAutoActivate = false;
	MusicB->bIsUISound = true;
	Embers = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Embers"));
	Embers->SetupAttachment(Root);
}

void ATwEnvironment::BeginPlay()
{
	Super::BeginPlay();
	if (GEngine) GEngine->bEnableOnScreenDebugMessages = false; // no debug text over the presentation
	// headroom: busy fights summed past full scale and clipped (measured on the packaged build)
	if (FAudioDeviceHandle Dev = GetWorld()->GetAudioDevice()) Dev->SetTransientPrimaryVolume(0.7f);
	const FTwSkyPreset P = GetSkyPreset();
	EmberFloorZ = P.EmberFloorZ;
	BuildSky(P);
	BuildLevel();
	BuildEmbers(P.EmberColor);
	BuildNightSky(P);
	PlayMusic(GetStartMusic());
}

void ATwEnvironment::BuildNightSky(const FTwSkyPreset& P)
{
	if (P.Stars > 0)
	{
		UInstancedStaticMeshComponent* Ism = NewObject<UInstancedStaticMeshComponent>(this);
		Ism->SetStaticMesh(TwAssets::Sphere());
		Ism->SetupAttachment(RootComponent);
		Ism->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Ism->SetCastShadow(false);
		Ism->RegisterComponent();
		Ism->SetWorldTransform(FTransform::Identity);
		if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
		{
			M->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.8f, 0.85f, 1.f));
			M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
			M->SetScalarParameterValue(TEXT("Intensity"), 6.f);
			M->SetScalarParameterValue(TEXT("Falloff"), 1.f);
			Ism->SetMaterial(0, M);
		}
		// far dome: about one to two pixels per star at 1600x900
		FRandomStream R(7);
		TArray<FTransform> Xf;
		for (int32 i = 0; i < P.Stars; ++i)
		{
			const float Az = R.FRandRange(0.f, 2.f * PI);
			const float El = FMath::Asin(R.FRandRange(0.12f, 1.f)); // uniform over the upper dome, none at the horizon haze
			const FVector Dir(FMath::Cos(El) * FMath::Cos(Az), FMath::Cos(El) * FMath::Sin(Az), FMath::Sin(El));
			const float S = R.FRandRange(2.5f, 5.5f) * (R.FRand() < 0.06f ? 1.8f : 1.f);
			Xf.Add(FTransform(FQuat::Identity, Dir * 300000.f, FVector(S)));
		}
		Ism->AddInstances(Xf, false, true);
	}
	if (P.bMoonDisc)
	{
		UStaticMeshComponent* MoonDisc = NewObject<UStaticMeshComponent>(this);
		MoonDisc->SetStaticMesh(TwAssets::Sphere());
		MoonDisc->SetupAttachment(RootComponent);
		MoonDisc->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		MoonDisc->SetCastShadow(false);
		MoonDisc->RegisterComponent();
		// the key light points FROM the moon: put the disc against its direction
		MoonDisc->SetWorldLocation(-P.SunRot.Vector() * 280000.f);
		MoonDisc->SetWorldScale3D(FVector(75.f));
		if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
		{
			M->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.85f, 0.9f, 1.f));
			M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
			M->SetScalarParameterValue(TEXT("Intensity"), 4.f);
			M->SetScalarParameterValue(TEXT("Falloff"), 0.6f);
			MoonDisc->SetMaterial(0, M);
		}
	}
}

void ATwEnvironment::Tick(float Dt)
{
	Super::Tick(Dt);
	UpdateEmbers(Dt);
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

void ATwEnvironment::BuildSky(const FTwSkyPreset& S)
{
	// Low sunset sun: long warm light across the purple sea
	Sun->SetMobility(EComponentMobility::Movable);
	Sun->SetWorldRotation(S.SunRot);
	Sun->SetIntensity(S.SunIntensity);
	Sun->SetLightColor(S.SunColor);
	Sun->SetAtmosphereSunLight(true);
	Sun->SetAtmosphereSunLightIndex(0);
	Sun->SetCastShadows(true);
	Sun->SetDynamicShadowDistanceMovableLight(S.ShadowDistance);
	Sun->SetDynamicShadowCascades(2);
	Sun->bUseInsetShadowsForMovableObjects = false;
	Sun->SetLightSourceAngle(2.f);
	Sun->SetEnableLightShaftBloom(true);
	Sun->SetBloomScale(0.35f);
	Sun->SetBloomThreshold(4.f);
	Sun->SetBloomTint(FColor(255, 150, 90));

	// cool purple rim light from the opposite side (the "night" half of the sky)
	Sun->SetForwardShadingPriority(1);
	Moon->SetMobility(EComponentMobility::Movable);
	Moon->SetWorldRotation(S.MoonRot);
	Moon->SetIntensity(S.MoonIntensity);
	Moon->SetLightColor(S.MoonColor);
	Moon->SetCastShadows(false);
	Moon->SetAtmosphereSunLight(false);

	Atmosphere->SetMobility(EComponentMobility::Movable);
	Atmosphere->SetRayleighScatteringScale(0.0331f * 1.15f);
	Atmosphere->SetMieScatteringScale(0.006f);
	Atmosphere->SetMieAnisotropy(0.85f);
	Atmosphere->SetSkyLuminanceFactor(S.SkyLuminance);

	SkyLight->SetMobility(EComponentMobility::Movable);
	SkyLight->SourceType = ESkyLightSourceType::SLS_CapturedScene;
	SkyLight->bRealTimeCapture = false;
	SkyLight->SetIntensity(S.SkyLightIntensity);
	SkyLight->SetLightColor(S.SkyLightColor);
	SkyLight->SetLowerHemisphereColor(FLinearColor(0.12f, 0.03f, 0.15f));
	SkyLight->bLowerHemisphereIsBlack = false;

	Fog->SetMobility(EComponentMobility::Movable);
	Fog->SetFogDensity(S.FogDensity);
	Fog->SetFogHeightFalloff(S.FogFalloff);
	Fog->SetWorldLocation(FVector(0, 0, 0));
	Fog->SetFogInscatteringColor(S.FogColor);
	Fog->SetDirectionalInscatteringColor(S.FogSunColor);
	Fog->SetDirectionalInscatteringExponent(6.f);
	Fog->SetDirectionalInscatteringStartDistance(3000.f);
	Fog->SetStartDistance(S.FogStart);
	Fog->SetFogMaxOpacity(0.92f);
	Fog->SetVolumetricFog(false);

	// Post-process: warm highlights, violet shadows, strong bloom, cinematic vignette
	Post->bUnbound = true;
	Post->Priority = 1.f;
	FPostProcessSettings& P = Post->Settings;
	P.bOverride_AutoExposureMethod = true; P.AutoExposureMethod = EAutoExposureMethod::AEM_Manual;
	P.bOverride_AutoExposureBias = true; P.AutoExposureBias = S.Exposure;
	{ float Ov = 0.f; if (FParse::Value(FCommandLine::Get(), TEXT("TwExposure="), Ov)) P.AutoExposureBias = Ov; }
	P.bOverride_AutoExposureApplyPhysicalCameraExposure = true; P.AutoExposureApplyPhysicalCameraExposure = false;
	P.bOverride_BloomIntensity = true; P.BloomIntensity = 1.35f;
	P.bOverride_BloomThreshold = true; P.BloomThreshold = 1.2f;
	P.bOverride_VignetteIntensity = true; P.VignetteIntensity = 0.55f;
	P.bOverride_FilmGrainIntensity = true; P.FilmGrainIntensity = 0.12f;
	P.bOverride_ColorSaturation = true; P.ColorSaturation = FVector4(1.08f, 1.02f, 1.12f, 1.1f);
	P.bOverride_ColorContrast = true; P.ColorContrast = FVector4(1.f, 1.f, 1.f, 1.08f);
	P.bOverride_ColorGainShadows = true; P.ColorGainShadows = S.GainShadows;
	P.bOverride_ColorGainHighlights = true; P.ColorGainHighlights = S.GainHighlights;
	P.bOverride_SceneFringeIntensity = true; P.SceneFringeIntensity = 0.6f;
	P.bOverride_LensFlareIntensity = true; P.LensFlareIntensity = 0.35f;
	P.bOverride_MotionBlurAmount = true; P.MotionBlurAmount = 0.f;
	P.bOverride_AmbientOcclusionIntensity = true; P.AmbientOcclusionIntensity = 0.35f;

}

float ATwEnvironment::HillHeight(float X, float Y, float R, float H, int32 Seed, bool bTwin)
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

UProceduralMeshComponent* ATwEnvironment::BuildHeightfield(const FVector& Center, float Radius, float Height, int32 Seed, int32 Res, bool bTwin, UMaterialInterface* Mat, bool bCollide)
{
	return BuildTerrain(Center, Radius, Radius, Res, Res, [Radius, Height, Seed, bTwin](float X, float Y) { return HillHeight(X, Y, Radius, Height, Seed, bTwin); }, Mat, bCollide);
}

UProceduralMeshComponent* ATwEnvironment::BuildTerrain(const FVector& Center, float HalfX, float HalfY, int32 ResX, int32 ResY, TFunctionRef<float(float, float)> HeightFn, UMaterialInterface* Mat, bool bCollide, float UVScale)
{
	UProceduralMeshComponent* PM = NewObject<UProceduralMeshComponent>(this);
	PM->SetupAttachment(RootComponent);
	PM->RegisterComponent();
	PM->SetWorldLocation(Center);
	PM->bUseComplexAsSimpleCollision = true;
	PM->SetCastShadow(true);

	TArray<FVector> V; TArray<int32> T; TArray<FVector> N; TArray<FVector2D> UV; TArray<FLinearColor> Col; TArray<FProcMeshTangent> Tan;
	const int32 RX = ResX + 1, RY = ResY + 1;
	const float SX = 2.f * HalfX / ResX, SY = 2.f * HalfY / ResY;
	V.Reserve(RX * RY);
	float MaxZ = 1.f;
	for (int32 y = 0; y <= ResY; ++y)
	{
		for (int32 x = 0; x <= ResX; ++x)
		{
			const float X = -HalfX + x * SX, Y = -HalfY + y * SY;
			const float Z = HeightFn(X, Y);
			MaxZ = FMath::Max(MaxZ, Z);
			V.Add(FVector(X, Y, Z));
			UV.Add(FVector2D((Center.X + X) / UVScale, (Center.Y + Y) / UVScale));
		}
	}
	N.SetNum(V.Num());
	for (int32 y = 0; y <= ResY; ++y)
	{
		for (int32 x = 0; x <= ResX; ++x)
		{
			const int32 i = y * RX + x;
			const float hl = V[y * RX + FMath::Max(x - 1, 0)].Z, hr = V[y * RX + FMath::Min(x + 1, ResX)].Z;
			const float hd = V[FMath::Max(y - 1, 0) * RX + x].Z, hu = V[FMath::Min(y + 1, ResY) * RX + x].Z;
			N[i] = FVector((hl - hr) * SY, (hd - hu) * SX, 2.f * SX * SY).GetSafeNormal();
			Tan.Add(FProcMeshTangent(FVector(1, 0, 0), false));
			Col.Add(FLinearColor(V[i].Z / MaxZ, 0, 0, 1));
		}
	}
	for (int32 y = 0; y < ResY; ++y)
	{
		for (int32 x = 0; x < ResX; ++x)
		{
			const int32 a = y * RX + x, b = a + 1, c = a + RX, d = c + 1;
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
	Heightfields.Add(PM);
	return PM;
}

static constexpr float EmberBox = 7000.f;

void ATwEnvironment::BuildEmbers(const FLinearColor& Color)
{
	Embers->SetStaticMesh(TwAssets::Sphere());
	Embers->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Embers->SetCastShadow(false);
	Embers->SetMobility(EComponentMobility::Movable);
	Embers->SetAbsolute(true, true, true);
	Embers->SetWorldTransform(FTransform::Identity);
	if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
	{
		M->SetVectorParameterValue(TEXT("Color"), Color);
		M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		M->SetScalarParameterValue(TEXT("Intensity"), 30.f);
		Embers->SetMaterial(0, M);
	}
	FRandomStream R(77);
	const int32 N = 280;
	EmberPos.SetNum(N);
	EmberSize.SetNum(N);
	TArray<FTransform> T;
	for (int32 i = 0; i < N; ++i)
	{
		EmberPos[i] = FVector(R.FRandRange(-EmberBox, EmberBox), R.FRandRange(-EmberBox, EmberBox), R.FRandRange(-EmberBox, EmberBox) * 0.5f);
		EmberSize[i] = R.FRandRange(0.06f, 0.16f);
		T.Add(FTransform(FRotator::ZeroRotator, EmberPos[i], FVector(EmberSize[i])));
	}
	Embers->AddInstances(T, false, true);
}

void ATwEnvironment::UpdateEmbers(float Dt)
{
	APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0);
	if (!Cam || EmberPos.Num() == 0) return;
	const FVector C = Cam->GetCameraLocation();
	const float T = GetWorld()->GetTimeSeconds();
	TArray<FTransform> Tr;
	Tr.SetNum(EmberPos.Num());
	for (int32 i = 0; i < EmberPos.Num(); ++i)
	{
		FVector& P = EmberPos[i];
		P += FVector(FMath::Sin(T * 0.3f + i) * 40.f, FMath::Cos(T * 0.23f + i * 1.7f) * 40.f, 70.f + (i % 7) * 12.f) * Dt;
		// wrap around the camera so the field always surrounds the player
		FVector D = P - C;
		for (int32 a = 0; a < 3; ++a)
		{
			const float Box = a == 2 ? EmberBox * 0.5f : EmberBox;
			if (D[a] > Box) P[a] -= 2.f * Box; else if (D[a] < -Box) P[a] += 2.f * Box;
		}
		FVector W = P;
		if (W.Z < EmberFloorZ) W.Z = EmberFloorZ + (EmberFloorZ - W.Z);
		const float Flick = 0.75f + 0.25f * FMath::Sin(T * (3.f + (i % 5)) + i);
		Tr[i] = FTransform(FRotator::ZeroRotator, W, FVector(EmberSize[i] * Flick));
	}
	Embers->BatchUpdateInstancesTransforms(0, Tr, true, true, false);
}

void ATwEnvironment::PlayMusic(const TCHAR* Name)
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
