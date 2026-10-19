#pragma once

#include "CoreMinimal.h"
#include "Components/PoseableMeshComponent.h"
#include "AralezWingComponent.generated.h"

/**
 * Procedural feathered wings for the Aralez (SK_AralezWings: wings_root, L/R_humerus, L/R_forearm, L/R_hand).
 * Attach it to the dog mesh at the "wing_socket" (or bone chest_jnt + offset) and drive it with SetMode().
 * The maths mirrors scripts/wingflap.py (the baked Wing_* clips are produced from the same function), so
 * pose-for-pose the procedural wings and the baked clips match.
 *
 *  Modes (weights are smoothed, any mix is allowed):
 *    Flap   - full wingbeat at FlapHz (downstroke fast, hand folds on the upstroke)
 *    Glide  - spread with dihedral, tips curled up, slow "breathing"
 *    Mantle - landing air-brake: raised, swept forward, leading edge up
 *    Arch   - standing guard: lifted and swept back over the body, tips lowered like a canopy
 */
UCLASS(ClassGroup = (Twilight), meta = (BlueprintSpawnableComponent))
class TWILIGHT_API UAralezWingComponent : public UPoseableMeshComponent
{
	GENERATED_BODY()
public:
	UAralezWingComponent();

	/** Target weights (0..1). They are normalised and eased with BlendSpeed. */
	void SetMode(float InFlap, float InGlide, float InMantle, float InArch);
	/** Wingbeat frequency (Hz) while flapping. A 45 kg flier would beat ~1.2 Hz; 0.9-1.4 reads best. */
	void SetFlapRate(float Hz) { FlapHz = FMath::Max(0.05f, Hz); }
	/** 0..1 stroke phase: 0.25 = top of the upstroke, 0.75 = bottom of the downstroke. Use it to sync the body clip. */
	float GetStrokePhase() const { return Phase; }
	/** Vertical body bob (cm) the owner can add to the mesh so the beats look like they carry weight. */
	float GetBodyLift() const;

	UPROPERTY(EditAnywhere, Category = "Aralez") float FlapHz = 1.1f;
	UPROPERTY(EditAnywhere, Category = "Aralez") float BlendSpeed = 3.f;
	UPROPERTY(EditAnywhere, Category = "Aralez") float BobAmplitude = 6.f;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

protected:
	virtual void OnRegister() override;

private:
	struct FSide
	{
		FName Bones[3];          // humerus, forearm, hand
		FQuat RefCS[3];          // reference component-space rotations
		FVector Span, Back, Up;  // wing frame in component space (ref pose)
	};
	void CacheReference();
	void ApplyPose();
	static void WingPose(float Phase, const FVector4f& W, float Time, FVector OutDeg[3]);

	FSide Sides[2];
	bool bCached = false;
	FVector4f Target = FVector4f(0.f, 1.f, 0.f, 0.f);
	FVector4f Weights = FVector4f(0.f, 1.f, 0.f, 0.f);
	float Phase = 0.f;
	float Time = 0.f;
};
