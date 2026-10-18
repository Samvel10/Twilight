#include "TwPoseAnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AnimNodeBase.h"
#include "AnimationRuntime.h"

void UTwPoseAnimInstance::SetLoop(UAnimSequence* Seq, float BlendTime, float Rate, bool bLooping)
{
	if (!Seq) return;
	if (Current.Seq == Seq) { Current.Rate = Rate; Current.bLoop = bLooping; return; }
	Previous = Current;
	Current = FTwPoseLayer();
	Current.Seq = Seq;
	Current.Rate = Rate;
	Current.bLoop = bLooping;
	Current.Weight = Previous.Seq ? 0.f : 1.f;
	BlendDuration = FMath::Max(0.01f, BlendTime);
	BlendElapsed = 0.f;
}

void UTwPoseAnimInstance::PlayOneShot(UAnimSequence* Seq, float Rate, float BlendIn, float BlendOut, float MaxWeight)
{
	if (!Seq) return;
	OneShot = FTwPoseLayer();
	OneShot.Seq = Seq;
	OneShot.Rate = Rate;
	OneShot.bLoop = false;
	OneShotIn = FMath::Max(0.01f, BlendIn);
	OneShotOut = FMath::Max(0.01f, BlendOut);
	OneShotMax = MaxWeight;
}

void UTwPoseAnimInstance::NativeUpdateAnimation(float Dt)
{
	Super::NativeUpdateAnimation(Dt);

	auto Advance = [this, Dt](FTwPoseLayer& L)
	{
		if (!L.Seq) return;
		const double Len = FMath::Max(0.01, (double)L.Seq->GetPlayLength());
		L.Time += Dt * L.Rate;
		if (L.bLoop) { L.Time = FMath::Fmod(L.Time, Len); if (L.Time < 0) L.Time += Len; }
		else if (&L != &OneShot) { L.Time = FMath::Min(L.Time, Len - 0.001); } // hold the last frame
	};
	Advance(Current);
	Advance(Previous);
	Advance(OneShot);

	// base cross-fade
	BlendElapsed += Dt;
	const float A = FMath::Clamp(BlendElapsed / BlendDuration, 0.f, 1.f);
	const float Smooth = A * A * (3.f - 2.f * A);
	Current.Weight = Previous.Seq ? Smooth : 1.f;
	if (A >= 1.f) Previous = FTwPoseLayer();

	// one-shot envelope
	if (OneShot.Seq)
	{
		const double Len = OneShot.Seq->GetPlayLength();
		const double T = OneShot.Time;
		float W = OneShotMax;
		if (T < OneShotIn) W *= T / OneShotIn;
		if (T > Len - OneShotOut) W *= FMath::Max(0.0, (Len - T) / OneShotOut);
		OneShot.Weight = FMath::Clamp(W, 0.f, 1.f);
		if (T >= Len) OneShot = FTwPoseLayer();
	}
}

FTwPoseSnapshot UTwPoseAnimInstance::GetSnapshot() const
{
	FTwPoseSnapshot S;
	S.Current = Current;
	S.Previous = Previous;
	S.OneShot = OneShot;
	S.OneShotMaskRoot = OneShotMaskRoot;
	return S;
}

void FTwPoseProxy::PreUpdate(UAnimInstance* InAnimInstance, float DeltaSeconds)
{
	FAnimInstanceProxy::PreUpdate(InAnimInstance, DeltaSeconds);
	if (const UTwPoseAnimInstance* I = Cast<UTwPoseAnimInstance>(InAnimInstance))
	{
		Snap = I->GetSnapshot();
	}
}

static void TwSample(const FTwPoseLayer& L, FPoseContext& Out)
{
	FAnimationPoseData Data(Out);
	FAnimExtractContext Ctx(L.Time, false, FDeltaTimeRecord(), L.bLoop);
	L.Seq->GetAnimationPose(Data, Ctx);
}

bool FTwPoseProxy::Evaluate(FPoseContext& Output)
{
	const FTwPoseLayer& C = Snap.Current;
	if (!C.Seq)
	{
		Output.ResetToRefPose();
		return true;
	}

	TwSample(C, Output);

	if (Snap.Previous.Seq && C.Weight < 0.999f)
	{
		FPoseContext Prev(this);
		TwSample(Snap.Previous, Prev);
		FAnimationPoseData OutData(Output);
		const FAnimationPoseData PrevData(Prev);
		// Output currently holds Current; blend: Current*W + Prev*(1-W)
		FAnimationRuntime::BlendTwoPosesTogetherInPlace(OutData, PrevData, C.Weight);
	}

	if (Snap.OneShot.Seq && Snap.OneShot.Weight > 0.001f)
	{
		// additive clips (e.g. the Rifle hit-reacts) hold deltas, not a pose: blending them as a pose collapses the skeleton
		const bool bAdditive = Snap.OneShot.Seq->IsValidAdditive();
		FPoseContext Shot(this, bAdditive);
		TwSample(Snap.OneShot, Shot);
		if (bAdditive)
		{
			FAnimationPoseData OutData(Output);
			const FAnimationPoseData ShotData(Shot);
			FAnimationRuntime::AccumulateAdditivePose(OutData, ShotData, Snap.OneShot.Weight, Snap.OneShot.Seq->GetAdditiveAnimType());
			Output.Pose.NormalizeRotations();
		}
		else if (Snap.OneShotMaskRoot.IsNone())
		{
			FAnimationPoseData OutData(Output);
			const FAnimationPoseData ShotData(Shot);
			FAnimationRuntime::BlendTwoPosesTogetherInPlace(OutData, ShotData, 1.f - Snap.OneShot.Weight);
		}
		else
		{
			// masked overlay: only the subtree under the mask root takes the action (legs keep flying)
			const FBoneContainer& BC = Output.Pose.GetBoneContainer();
			const int32 N = Output.Pose.GetNumBones();
			if (MaskFor != Snap.OneShotMaskRoot || MaskWeights.Num() != N)
			{
				MaskFor = Snap.OneShotMaskRoot;
				MaskWeights.Init(0.f, N);
				const FReferenceSkeleton& Ref = BC.GetReferenceSkeleton();
				for (FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
				{
					for (FCompactPoseBoneIndex P = I; P.GetInt() != INDEX_NONE; P = BC.GetParentBoneIndex(P))
					{
						const int32 MeshIdx = BC.MakeMeshPoseIndex(P).GetInt();
						if (MeshIdx != INDEX_NONE && Ref.GetBoneName(MeshIdx) == MaskFor) { MaskWeights[I.GetInt()] = 1.f; break; }
					}
				}
			}
			for (FCompactPoseBoneIndex I : Output.Pose.ForEachBoneIndex())
			{
				const float W = MaskWeights[I.GetInt()] * Snap.OneShot.Weight;
				if (W > 0.f) Output.Pose[I].BlendWith(Shot.Pose[I], W);
			}
		}
	}
	return true;
}
