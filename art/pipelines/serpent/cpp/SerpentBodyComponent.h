// SerpentBodyComponent: drives a serpent skeletal mesh (bone chain Head -> Spine_01..Spine_NN, plus Jaw)
// along an arbitrary world-space path every frame. Drop-in for UE 5.8; depends only on Engine.
//
// Usage (any actor):
//   Body = CreateDefaultSubobject<USerpentBodyComponent>(TEXT("Body"));
//   Body->SetSkinnedAssetAndUpdate(SerpentMesh);           // e.g. /Game/Twilight/Vishap/SK_VishapSerpent
//   // every Tick:  Path[0] = where the head is, then points going back along the body (any spacing, >= 2 points)
//   Body->ApplyPath(Path, FVector::UpVector, GetWorld()->GetTimeSeconds());
//   Body->JawOpen = 0..1;
//
// The path is sampled at each bone's rest distance from the head (times the component scale), so the body length
// stays constant whatever the path spacing is; if the path is shorter than the body the tail continues straight.
#pragma once

#include "CoreMinimal.h"
#include "Components/PoseableMeshComponent.h"
#include "SerpentBodyComponent.generated.h"

UCLASS(ClassGroup = (Twilight), meta = (BlueprintSpawnableComponent))
class USerpentBodyComponent : public UPoseableMeshComponent
{
	GENERATED_BODY()
public:
	USerpentBodyComponent();

	/** Root bone at the neck pivot; the chain continues with ChainPrefix01, 02, ... until a name is missing. */
	UPROPERTY(EditAnywhere, Category = "Serpent") FName HeadBone = TEXT("Head");
	UPROPERTY(EditAnywhere, Category = "Serpent") FString ChainPrefix = TEXT("Spine_");
	UPROPERTY(EditAnywhere, Category = "Serpent") FName JawBone = TEXT("Jaw");

	/** Swimming wave added on top of the path (side-to-side, like a snake / eel), in body-lengths units. */
	UPROPERTY(EditAnywhere, Category = "Serpent|Wave") float WaveAmplitude = 0.05f;   // fraction of body length
	UPROPERTY(EditAnywhere, Category = "Serpent|Wave") float WaveLength = 0.38f;       // fraction of body length
	UPROPERTY(EditAnywhere, Category = "Serpent|Wave") float WaveSpeed = 1.1f;         // waves per second
	UPROPERTY(EditAnywhere, Category = "Serpent|Wave") float WaveVertical = 0.25f;     // 0 = pure lateral, 1 = as much up/down
	/** 0 = pure parallel transport of the head's up vector, 1 = every segment keeps its back towards UpHint. */
	UPROPERTY(EditAnywhere, Category = "Serpent") float UprightBlend = 0.35f;
	/** Bank (roll) into turns, degrees per (1/m) of curvature, clamped to MaxBank. */
	UPROPERTY(EditAnywhere, Category = "Serpent") float BankPerCurvature = 900.f;
	UPROPERTY(EditAnywhere, Category = "Serpent") float MaxBank = 45.f;
	/** Jaw opening 0..1 and the angle that 1 means. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Serpent") float JawOpen = 0.f;
	UPROPERTY(EditAnywhere, Category = "Serpent") float JawMaxDegrees = 38.f;
	/** Uniform scale of the head bone (bigger, more dragon-like skull without touching the mesh). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Serpent") float HeadScale = 1.35f;

	/** Optional rigid attachment on the head bone (e.g. SM_VishapHorns, authored in head-bone space). */
	UPROPERTY(EditAnywhere, Category = "Serpent") TObjectPtr<class UStaticMesh> HeadAttachment;
	UPROPERTY(Transient) TObjectPtr<class UStaticMeshComponent> HeadAttachmentComp;

	/** Distance-based LOD (nearest body point to the camera, divided by the component scale, in cm):
	 *  beyond LodDistances[0] -> LOD1, beyond [1] -> LOD2 ... Empty = engine screen-size LOD. */
	UPROPERTY(EditAnywhere, Category = "Serpent|LOD") TArray<float> LodDistances = { 2500.f, 7000.f };

	/** Rest length head-pivot -> tail tip in world units (includes component scale). Valid after InitChain(). */
	UFUNCTION(BlueprintCallable, Category = "Serpent") float GetBodyLength() const;

	/** Reads the chain from the reference skeleton. Called automatically by ApplyPath when the mesh changes. */
	UFUNCTION(BlueprintCallable, Category = "Serpent") bool InitChain();

	/** Pose the body. Path: world points from the head backwards (index 0 = head). UpHint: usually +Z. */
	UFUNCTION(BlueprintCallable, Category = "Serpent")
	void ApplyPath(const TArray<FVector>& Path, FVector UpHint, float TimeSeconds);

	/** World position of a point on the body, 0 = head pivot, 1 = tail tip (after the last ApplyPath). */
	UFUNCTION(BlueprintCallable, Category = "Serpent") FVector GetBodyPoint(float Alpha) const;

	virtual FBoxSphereBounds CalcBounds(const FTransform& LocalToWorld) const override;

private:
	struct FLink { int32 Bone = INDEX_NONE; int32 LongAxis = 0; float Dist = 0.f; FQuat RefRotCS = FQuat::Identity; FVector RefOffsetCS = FVector::ZeroVector; };
	TArray<FLink> Chain;                 // Head first
	int32 JawIndex = INDEX_NONE;
	FTransform JawRefLocal;
	FQuat RestFrameInv = FQuat::Identity; // inverse of the body frame (forward=to head, up) in component space at rest
	FVector JawAxisCS = FVector::YAxisVector;
	float RestLength = 1.f;               // component-space units
	float MaxRadius = 50.f;               // component-space, for bounds
	TWeakObjectPtr<const USkinnedAsset> ChainAsset;
	TArray<FVector> PosedCS;              // component-space bone positions of the last pose (bounds / queries)
	TArray<FVector> PosedWorld;

	void UpdateLod();
	static FVector SamplePath(const TArray<FVector>& P, const TArray<float>& Cum, float D, FVector* OutTangent);
};
