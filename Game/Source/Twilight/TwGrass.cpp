#include "TwGrass.h"
#include "Components/HierarchicalInstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/Actor.h"

int32 TwGrass::Scatter(AActor* Owner, const FVector2D& Center, const FVector2D& HalfSize, float Density, TFunctionRef<float(float, float)> HeightFn,
	int32 Seed, float FlowerShare, TFunction<bool(float, float)> Keep, float CullEnd)
{
	if (!Owner) return 0;
	struct FVariant { const TCHAR* Name; float Weight; bool bFlower; };
	static const FVariant Variants[] = {
		{ TEXT("SM_GrassDry_0"), 1.f, false }, { TEXT("SM_GrassDry_1"), 1.f, false }, { TEXT("SM_GrassDry_2"), 1.f, false }, { TEXT("SM_GrassDry_3"), 1.f, false },
		{ TEXT("SM_GrassGreen_0"), 0.8f, false }, { TEXT("SM_GrassGreen_1"), 0.8f, false }, { TEXT("SM_GrassGreen_2"), 0.8f, false }, { TEXT("SM_GrassGreen_3"), 0.8f, false },
		{ TEXT("SM_GrassScan_a"), 0.7f, false }, { TEXT("SM_GrassScan_b"), 0.7f, false }, { TEXT("SM_GrassScan_c"), 0.7f, false }, { TEXT("SM_GrassScan_d"), 0.7f, false },
		{ TEXT("SM_Poppy_0"), 1.f, true }, { TEXT("SM_Poppy_1"), 1.f, true }, { TEXT("SM_Poppy_2"), 1.f, true },
		{ TEXT("SM_Daisy_0"), 1.f, true }, { TEXT("SM_Daisy_1"), 1.f, true },
	};
	TArray<UHierarchicalInstancedStaticMeshComponent*> Grass, Flowers;
	TArray<float> GrassW;
	for (const FVariant& V : Variants)
	{
		const FString Path = FString::Printf(TEXT("/Game/Env/Veg/%s/%s/StaticMeshes/%s.%s"), V.Name, V.Name, V.Name, V.Name);
		UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, *Path);
		if (!M) continue;
		UHierarchicalInstancedStaticMeshComponent* H = NewObject<UHierarchicalInstancedStaticMeshComponent>(Owner);
		H->SetStaticMesh(M);
		// the kit's two-sided foliage instances (alpha-tested cards, per-instance tint, distance thinning)
		const FString N(V.Name);
		const TCHAR* MI = N.Contains(TEXT("Dry")) ? TEXT("MI_GrassDry") : N.Contains(TEXT("Green")) ? TEXT("MI_GrassGreen")
			: N.Contains(TEXT("Poppy")) ? TEXT("MI_Poppy") : N.Contains(TEXT("Daisy")) ? TEXT("MI_Daisy") : (N.EndsWith(TEXT("_d")) ? TEXT("MI_GrassScan07") : TEXT("MI_GrassScan12"));
		if (UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *FString::Printf(TEXT("/Game/Env/Materials/%s.%s"), MI, MI))) H->SetMaterial(0, Mat);
		H->SetupAttachment(Owner->GetRootComponent());
		H->SetMobility(EComponentMobility::Static);
		H->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		H->SetCastShadow(false);
		H->SetCullDistances(CullEnd * 0.85f, CullEnd);
		H->bAffectDistanceFieldLighting = false;
		H->RegisterComponent();
		H->SetWorldTransform(FTransform::Identity);
		(V.bFlower ? Flowers : Grass).Add(H);
		if (!V.bFlower) GrassW.Add(V.Weight);
	}
	if (Grass.Num() == 0) return 0;
	float WSum = 0.f; for (float W : GrassW) WSum += W;
	FRandomStream R(Seed);
	const int32 N = FMath::RoundToInt(HalfSize.X * HalfSize.Y * 4.f / 10000.f * Density);
	TArray<TArray<FTransform>> GT, FT;
	GT.SetNum(Grass.Num()); FT.SetNum(Flowers.Num());
	int32 Count = 0;
	for (int32 i = 0; i < N; ++i)
	{
		const float X = Center.X + R.FRandRange(-HalfSize.X, HalfSize.X), Y = Center.Y + R.FRandRange(-HalfSize.Y, HalfSize.Y);
		// meadow patches: thicker in the swales of a 25 m noise, thin on the knolls
		const float Patch = 0.5f + 0.5f * FMath::PerlinNoise2D(FVector2D(X, Y) / 2500.f + FVector2D(Seed * 0.37f, 1.3f));
		if (R.FRand() > 0.35f + 0.65f * Patch) continue;
		if (Keep && !Keep(X, Y)) continue;
		const FVector P(X, Y, HeightFn(X, Y) - 2.f);
		const float S = R.FRandRange(0.75f, 1.25f);
		const FTransform T(FRotator(R.FRandRange(-6.f, 6.f), R.FRandRange(0.f, 360.f), R.FRandRange(-6.f, 6.f)), P, FVector(1.7f * S, 1.7f * S, S));
		const bool bFlower = Flowers.Num() > 0 && R.FRand() < FlowerShare * (0.4f + 1.2f * Patch);
		if (bFlower) FT[R.RandRange(0, Flowers.Num() - 1)].Add(FTransform(T.GetRotation(), P, FVector(S)));
		else
		{
			float Pick = R.FRand() * WSum; int32 k = 0;
			while (k < GrassW.Num() - 1 && Pick > GrassW[k]) { Pick -= GrassW[k]; ++k; }
			GT[k].Add(T);
		}
		++Count;
	}
	for (int32 k = 0; k < Grass.Num(); ++k) if (GT[k].Num()) Grass[k]->AddInstances(GT[k], false, true);
	for (int32 k = 0; k < Flowers.Num(); ++k) if (FT[k].Num()) Flowers[k]->AddInstances(FT[k], false, true);
	return Count;
}
