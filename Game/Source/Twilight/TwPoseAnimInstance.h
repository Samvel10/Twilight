#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "TwPoseAnimInstance.generated.h"

class UAnimSequence;

// One playing animation layer: a sequence, its local time, play rate and blend weight.
struct FTwPoseLayer
{
	TObjectPtr<UAnimSequence> Seq = nullptr;
	double Time = 0.0;
	float Rate = 1.f;
	float Weight = 0.f;
	bool bLoop = true;
};

// Snapshot handed to the evaluation proxy (worker thread safe copy).
struct FTwPoseSnapshot
{
	FTwPoseLayer Current;   // loop being blended in
	FTwPoseLayer Previous;  // loop being blended out
	FTwPoseLayer OneShot;   // action overlay (cast/hit)
	FName OneShotMaskRoot;  // NAME_None = full body, else only this bone and its children
};

struct FTwPoseProxy : public FAnimInstanceProxy
{
	FTwPoseProxy() {}
	FTwPoseProxy(UAnimInstance* InInstance) : FAnimInstanceProxy(InInstance) {}

	virtual void PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds) override;
	virtual bool Evaluate(FPoseContext& Output) override;

	FTwPoseSnapshot Snap;
private:
	// per compact-bone weight of the one-shot mask (cached for MaskFor / bone count)
	TArray<float> MaskWeights;
	FName MaskFor;
};

/**
 * Graph-less anim instance: blends looping sequences with cross-fades and plays one-shot overlays.
 * Lets us animate the template mannequin from C++ without authoring an Animation Blueprint.
 */
UCLASS(Transient)
class TWILIGHT_API UTwPoseAnimInstance : public UAnimInstance
{
	GENERATED_BODY()
public:
	/** Switch the base loop (cross-fades from the current one). */
	void SetLoop(UAnimSequence* Seq, float BlendTime = 0.25f, float Rate = 1.f, bool bLooping = true);
	/** Play an action once over the base loop. */
	void PlayOneShot(UAnimSequence* Seq, float Rate = 1.f, float BlendIn = 0.08f, float BlendOut = 0.2f, float MaxWeight = 1.f);
	bool IsOneShotPlaying() const { return OneShot.Seq != nullptr; }
	/** Restrict one-shots to a bone subtree (e.g. "spine_01" = upper body), NAME_None = full body. */
	void SetOneShotMask(FName Root) { OneShotMaskRoot = Root; }

	FTwPoseSnapshot GetSnapshot() const;

protected:
	virtual void NativeUpdateAnimation(float DeltaSeconds) override;
	virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override { return new FTwPoseProxy(this); }
	virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override { delete static_cast<FTwPoseProxy*>(InProxy); }

private:
	FTwPoseLayer Current, Previous, OneShot;
	float BlendDuration = 0.25f, BlendElapsed = 0.f;
	float OneShotIn = 0.08f, OneShotOut = 0.2f, OneShotMax = 1.f;
	FName OneShotMaskRoot;
};
