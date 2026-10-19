#include "TwLightning.h"
#include "TwAssets.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/World.h"
#include "Twilight.h"

static constexpr float BoltLife = 0.55f;

ATwLightning::ATwLightning()
{
	PrimaryActorTick.bCanEverTick = true;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	RootComponent = Root;
	auto MakeIsm = [this](const TCHAR* N)
	{
		UInstancedStaticMeshComponent* C = CreateDefaultSubobject<UInstancedStaticMeshComponent>(N);
		C->SetupAttachment(Root);
		C->SetAbsolute(true, true, true);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		return C;
	};
	Core = MakeIsm(TEXT("Core"));
	Halo = MakeIsm(TEXT("Halo"));
	Light = CreateDefaultSubobject<UPointLightComponent>(TEXT("Light"));
	Light->SetupAttachment(Root);
	Light->SetIntensityUnits(ELightUnits::Unitless);
	Light->SetLightColor(FLinearColor(0.7f, 0.8f, 1.f));
	Light->SetCastShadows(false);
}

ATwLightning* ATwLightning::Strike(UWorld* World, const FVector& From, const FVector& To, float Width, int32 Seed)
{
	if (!World) return nullptr;
	FActorSpawnParameters S;
	S.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	ATwLightning* L = World->SpawnActor<ATwLightning>(To, FRotator::ZeroRotator, S);
	if (L) L->Build(From, To, Width, Seed ? Seed : FMath::Rand());
	return L;
}

void ATwLightning::AddSeg(const FVector& A, const FVector& B, float Width)
{
	const FVector D = B - A;
	const float Len = D.Size();
	if (Len < 1.f) return;
	const FRotator Rot = FRotationMatrix::MakeFromZ(D / Len).Rotator();
	const FVector Mid = (A + B) * 0.5f;
	// engine cylinder: 100 cm tall, 100 cm across
	Core->AddInstance(FTransform(Rot, Mid, FVector(Width / 100.f, Width / 100.f, Len / 100.f)), true);
	Halo->AddInstance(FTransform(Rot, Mid, FVector(Width * 3.f / 100.f, Width * 3.f / 100.f, Len / 100.f)), true);
}

void ATwLightning::AddBranch(FRandomStream& R, const FVector& A, const FVector& B, float Width, int32 Depth)
{
	const FVector D = B - A;
	const float Len = D.Size();
	const FVector Dir = D / FMath::Max(1.f, Len);
	const FVector U = FVector::CrossProduct(Dir, FMath::Abs(Dir.Z) < 0.9f ? FVector::UpVector : FVector::ForwardVector).GetSafeNormal();
	const FVector V = FVector::CrossProduct(Dir, U);
	const int32 N = FMath::Clamp(FMath::RoundToInt(Len / 500.f), 6, 28);
	FVector Prev = A;
	for (int32 i = 1; i <= N; ++i)
	{
		const float T = (float)i / N;
		// jag amplitude: largest in the middle, zero at both ends
		const float Amp = (i == N) ? 0.f : Len * 0.07f * FMath::Sin(T * PI) * R.FRandRange(0.4f, 1.f);
		const float A0 = R.FRandRange(0.f, 2.f * PI);
		const FVector P = A + D * T + (U * FMath::Cos(A0) + V * FMath::Sin(A0)) * Amp;
		const float W = Width * (1.f - 0.45f * T);
		AddSeg(Prev, P, W);
		// forks: shorter, thinner, heading roughly the same way
		if (Depth < 2 && i < N - 1 && R.FRand() < (Depth == 0 ? 0.28f : 0.15f))
		{
			const FVector FDir = (Dir + (U * R.FRandRange(-1.f, 1.f) + V * R.FRandRange(-1.f, 1.f)) * 0.8f).GetSafeNormal();
			AddBranch(R, P, P + FDir * Len * R.FRandRange(0.12f, 0.3f), W * 0.5f, Depth + 1);
		}
		Prev = P;
	}
}

void ATwLightning::Build(const FVector& From, const FVector& To, float Width, int32 Seed)
{
	UStaticMesh* Cyl = TwAssets::Cylinder();
	Core->SetStaticMesh(Cyl);
	Halo->SetStaticMesh(Cyl);
	CoreMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	HaloMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (CoreMat)
	{
		CoreMat->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.75f, 0.85f, 1.f));
		CoreMat->SetScalarParameterValue(TEXT("GlowMode"), 0.f);
		CoreMat->SetScalarParameterValue(TEXT("Intensity"), 60.f);
		Core->SetMaterial(0, CoreMat);
	}
	if (HaloMat)
	{
		HaloMat->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.35f, 0.5f, 1.f));
		HaloMat->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		HaloMat->SetScalarParameterValue(TEXT("Falloff"), 3.f);
		HaloMat->SetScalarParameterValue(TEXT("Intensity"), 6.f);
		Halo->SetMaterial(0, HaloMat);
	}
	FRandomStream R(Seed);
	AddBranch(R, From, To, Width, 0);
	Light->SetWorldLocation(To + (From - To).GetSafeNormal() * 300.f);
	Light->SetAttenuationRadius(FMath::Clamp((float)FVector::Dist(From, To) * 0.8f, 3000.f, 20000.f));
	Light->SetIntensity(600000.f);
	SetLifeSpan(BoltLife + 0.05f);
}

void ATwLightning::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt;
	// two flickers, then a fade
	const float A = Age / BoltLife;
	float K = A < 0.15f ? 1.f : (A < 0.24f ? 0.1f : (A < 0.42f ? 0.9f : FMath::Square(1.f - (A - 0.42f) / 0.58f)));
	K = FMath::Clamp(K, 0.f, 1.f);
	if (CoreMat) CoreMat->SetScalarParameterValue(TEXT("Intensity"), 60.f * K);
	if (HaloMat) HaloMat->SetScalarParameterValue(TEXT("Intensity"), 6.f * K);
	Light->SetIntensity(600000.f * K);
	if (K <= 0.01f) { Core->SetVisibility(false); Halo->SetVisibility(false); }
	else if (!Core->IsVisible()) { Core->SetVisibility(true); Halo->SetVisibility(true); }
}
