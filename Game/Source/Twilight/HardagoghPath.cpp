#include "HardagoghPath.h"
#include "TwAssets.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

AHardagoghPath::AHardagoghPath()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void AHardagoghPath::Build(const FVector& Center, const FVector& InFwd, float Radius)
{
	const FVector Fwd = InFwd.GetSafeNormal2D();
	const FVector Side = FVector::CrossProduct(FVector::UpVector, Fwd);
	// the arc rises from one horizon, passes high in front of the viewer and sets on the other side
	const float Tilt = FMath::DegreesToRadians(58.f);
	const FVector ArcUp = (FVector::UpVector * FMath::Cos(Tilt) + Fwd * FMath::Sin(Tilt)).GetSafeNormal();
	const FVector Normal = FVector::CrossProduct(Side, ArcUp);
	for (int32 s = 0; s < Segs; ++s)
	{
		UInstancedStaticMeshComponent* C = NewObject<UInstancedStaticMeshComponent>(this);
		C->SetStaticMesh(TwAssets::Sphere());
		C->SetupAttachment(RootComponent);
		C->SetAbsolute(true, true, true);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		C->RegisterComponent();
		UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
		if (M)
		{
			// gold straw toward the middle of the band, paler dust at the ends
			const float K = FMath::Sin(PI * (s + 0.5f) / Segs);
			M->SetVectorParameterValue(TEXT("Color"), FMath::Lerp(FLinearColor(0.75f, 0.8f, 1.f), FLinearColor(1.f, 0.82f, 0.5f), K));
			M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
			M->SetScalarParameterValue(TEXT("Falloff"), 1.f);
			M->SetScalarParameterValue(TEXT("Intensity"), 0.f);
			C->SetMaterial(0, M);
		}
		Parts.Add(C);
		Mats.Add(M);
	}
	FRandomStream R(2492);
	TArray<TArray<FTransform>> Inst;
	Inst.SetNum(Segs);
	for (int32 i = 0; i < 3600; ++i)
	{
		const float U = R.FRand();
		const float Th = FMath::Lerp(0.04f, PI - 0.04f, U);
		const FVector OnArc = Side * FMath::Cos(Th) + ArcUp * FMath::Sin(Th);
		// gaussian spread across the band, a brighter thin core
		const float G = (R.FRand() + R.FRand() + R.FRand() - 1.5f) * (R.FRand() < 0.3f ? 0.025f : 0.07f);
		const FVector Dir = (OnArc + Normal * G).GetSafeNormal();
		const FVector P = Center + Dir * Radius * R.FRandRange(0.97f, 1.03f);
		const bool bStraw = R.FRand() < 0.18f;
		const float Sz = Radius * (bStraw ? 0.0012f : R.FRandRange(0.002f, 0.006f)) * (FMath::Abs(G) < 0.02f ? 1.3f : 1.f);
		FVector Scale(Sz / 100.f);
		FRotator Rot = FRotator::ZeroRotator;
		if (bStraw)
		{
			// a stalk of straw lying roughly along the band
			const FVector Tan = (FVector::CrossProduct(Normal, Dir) + Normal * R.FRandRange(-0.6f, 0.6f)).GetSafeNormal();
			Rot = FRotationMatrix::MakeFromX(Tan).Rotator();
			Scale = FVector(Radius * R.FRandRange(0.008f, 0.02f) / 100.f, Sz / 100.f, Sz / 100.f);
		}
		Inst[FMath::Min(Segs - 1, (int32)(U * Segs))].Add(FTransform(Rot, P, Scale));
	}
	// the milky haze the dust swims in
	for (int32 i = 0; i < 160; ++i)
	{
		const float U = (i + R.FRand()) / 160.f;
		const float Th = FMath::Lerp(0.04f, PI - 0.04f, U);
		const FVector Dir = (Side * FMath::Cos(Th) + ArcUp * FMath::Sin(Th) + Normal * R.FRandRange(-0.03f, 0.03f)).GetSafeNormal();
		const float Sz = Radius * R.FRandRange(0.035f, 0.06f) / 100.f;
		Haze.Add(FTransform(FRotator::ZeroRotator, Center + Dir * Radius * 1.05f, FVector(Sz, Sz, Sz * 0.6f)));
		HazeSeg.Add(FMath::Min(Segs - 1, (int32)(U * Segs)));
	}
	HazeIsm = NewObject<UInstancedStaticMeshComponent>(this);
	HazeIsm->SetStaticMesh(TwAssets::Sphere());
	HazeIsm->SetupAttachment(RootComponent);
	HazeIsm->SetAbsolute(true, true, true);
	HazeIsm->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	HazeIsm->SetCastShadow(false);
	HazeIsm->RegisterComponent();
	HazeMat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (HazeMat)
	{
		HazeMat->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.9f, 0.85f, 1.f));
		HazeMat->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		HazeMat->SetScalarParameterValue(TEXT("Falloff"), 4.f);
		HazeMat->SetScalarParameterValue(TEXT("Intensity"), 0.f);
		HazeIsm->SetMaterial(0, HazeMat);
	}
	HazeIsm->AddInstances(Haze, false, true);
	HazeIsm->MarkRenderStateDirty();
	for (int32 s = 0; s < Segs; ++s)
	{
		Parts[s]->AddInstances(Inst[s], false, true);
		Parts[s]->MarkRenderStateDirty();
	}
}

void AHardagoghPath::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += FMath::Min(Dt, 0.1f);
	for (int32 s = 0; s < Mats.Num(); ++s)
	{
		if (!Mats[s]) continue;
		// unrolls from one horizon to the other, each stretch flaring as it appears, then a slow shimmer
		const float Start = RevealTime * s / Segs;
		const float A = FMath::Clamp((Age - Start) / 0.8f, 0.f, 1.f);
		const float Flare = 1.f + 1.5f * FMath::Max(0.f, 1.f - (Age - Start) / 1.5f) * A;
		const float Shimmer = 0.9f + 0.1f * FMath::Sin(Age * 1.7f + s * 0.9f);
		Mats[s]->SetScalarParameterValue(TEXT("Intensity"), 9.f * A * Flare * Shimmer);
	}
	if (HazeMat) HazeMat->SetScalarParameterValue(TEXT("Intensity"), 0.35f * FMath::Clamp((Age - 1.f) / RevealTime, 0.f, 1.f));
}
