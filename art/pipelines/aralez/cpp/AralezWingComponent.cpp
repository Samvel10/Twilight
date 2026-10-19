#include "AralezWingComponent.h"
#include "Engine/SkeletalMesh.h"
#include "ReferenceSkeleton.h"

UAralezWingComponent::UAralezWingComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickGroup = TG_PrePhysics;
	bTickInEditor = true;
	SetCollisionEnabled(ECollisionEnabled::NoCollision);
	SetGenerateOverlapEvents(false);
	bCastDynamicShadow = true;
	// the wings are large: keep them from culling when the root bone is off screen
	SetBoundsScale(1.6f);
}

void UAralezWingComponent::OnRegister()
{
	Super::OnRegister();
	bCached = false;
}

void UAralezWingComponent::SetMode(float InFlap, float InGlide, float InMantle, float InArch)
{
	Target = FVector4f(InFlap, InGlide, InMantle, InArch);
}

float UAralezWingComponent::GetBodyLift() const
{
	// the body rises during the downstroke (phase .25 -> .75) and sinks on the upstroke
	return BobAmplitude * Weights.X * -FMath::Cos(2.f * PI * (Phase - 0.25f - 0.12f));
}

void UAralezWingComponent::CacheReference()
{
	const USkinnedAsset* Asset = GetSkinnedAsset();
	if (!Asset) return;
	const FReferenceSkeleton& Ref = Asset->GetRefSkeleton();
	auto RefCS = [&Ref](int32 Index)
	{
		FTransform T = FTransform::Identity;
		for (int32 I = Index; I != INDEX_NONE; I = Ref.GetParentIndex(I)) T = T * Ref.GetRefBonePose()[I];
		return T;
	};
	static const TCHAR* Names[3] = { TEXT("humerus"), TEXT("forearm"), TEXT("hand") };
	for (int32 S = 0; S < 2; ++S)
	{
		FSide& Side = Sides[S];
		FTransform CS[3];
		for (int32 B = 0; B < 3; ++B)
		{
			Side.Bones[B] = FName(*FString::Printf(TEXT("%s_%s"), S == 0 ? TEXT("L") : TEXT("R"), Names[B]));
			const int32 Idx = Ref.FindBoneIndex(Side.Bones[B]);
			if (Idx == INDEX_NONE) return;
			CS[B] = RefCS(Idx);
			Side.RefCS[B] = CS[B].GetRotation();
		}
		const int32 HandIdx = Ref.FindBoneIndex(Side.Bones[2]);
		// hand tip ~ hand head + (hand head - forearm head) * 0.7 (bone tails are not stored)
		const FVector Shoulder = CS[0].GetLocation(), Elbow = CS[1].GetLocation(), Wrist = CS[2].GetLocation();
		Side.Span = (Wrist - Shoulder).GetSafeNormal();
		Side.Up = FVector::UpVector;                               // glTF Y-up is imported as component +Z
		Side.Up = (Side.Up - Side.Span * (Side.Up | Side.Span)).GetSafeNormal();
		Side.Back = (Side.Up ^ Side.Span).GetSafeNormal();
		// the elbow sits slightly behind the shoulder-wrist line: use it to fix the sign of Back
		const FVector ElbowOff = (Elbow - Shoulder) - Side.Span * ((Elbow - Shoulder) | Side.Span);
		if ((ElbowOff | Side.Back) < 0.f) Side.Back = -Side.Back;
		(void)HandIdx;
	}
	bCached = true;
}

// --- identical to scripts/wingflap.py:wing_pose (degrees: x = twist, y = -elevation, z = sweep back) -------------
void UAralezWingComponent::WingPose(float Ph, const FVector4f& W, float T, FVector Out[3])
{
	const float Th = 2.f * PI * Ph;
	const float S = FMath::Sin(Th), Up = FMath::Max(0.f, FMath::Cos(Th)), Dn = FMath::Max(0.f, -FMath::Cos(Th));
	const float Br = FMath::Sin(T * 2.f * PI * 0.35f);
	const FVector F[3] = {
		FVector(6.f * FMath::Cos(Th), -(12.f + 40.f * S), 4.f - 8.f * Dn + 6.f * Up),
		FVector(0.f, -(10.f * FMath::Sin(Th - 0.5f)), 16.f * Up),
		FVector(-8.f * FMath::Cos(Th), -(16.f * FMath::Sin(Th - 0.9f) - 4.f), 34.f * Up + 4.f) };
	const FVector G[3] = {
		FVector(2.f, -(9.f + 2.f * Br), 6.f),
		FVector(0.f, -(2.f + Br), 2.f),
		FVector(-3.f, -(8.f + 2.f * Br), 6.f) };
	const FVector M[3] = {
		FVector(-24.f, -(52.f + 6.f * FMath::Sin(Th)), -22.f),
		FVector(-8.f, -6.f, 14.f),
		FVector(-16.f, -(14.f + 8.f * FMath::Sin(Th - 0.6f)), 20.f) };
	const FVector D[3] = {
		FVector(-4.f, -(32.f + 2.f * FMath::Sin(T * 1.3f)), 42.f),
		FVector(2.f, 14.f, 30.f),
		FVector(6.f, 30.f + 3.f * FMath::Sin(T * 1.3f + 1.f), 30.f) };
	const float Tot = FMath::Max(1e-4f, W.X + W.Y + W.Z + W.W);
	for (int32 B = 0; B < 3; ++B) Out[B] = (F[B] * W.X + G[B] * W.Y + M[B] * W.Z + D[B] * W.W) / Tot;
}

void UAralezWingComponent::TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(Dt, TickType, ThisTickFunction);
	Time += Dt;
	const float A = 1.f - FMath::Exp(-BlendSpeed * Dt);
	Weights = Weights + (Target - Weights) * A;
	// flapping runs at FlapHz; gliding lets the phase drift slowly so a new flap starts smoothly
	const float Hz = FMath::Lerp(0.15f, FlapHz, FMath::Clamp(Weights.X + Weights.Z, 0.f, 1.f));
	Phase = FMath::Fmod(Phase + Dt * Hz, 1.f);
	ApplyPose();
}

void UAralezWingComponent::ApplyPose()
{
	if (!bCached) CacheReference();
	if (!bCached) return;
	FVector Deg[3];
	WingPose(Phase, Weights, Time, Deg);
	// rotate vector A towards B by Angle (deg): axis = A x B, valid in either handedness
	auto Towards = [](const FVector& A, const FVector& B, float AngleDeg) { return FQuat((A ^ B).GetSafeNormal(), FMath::DegreesToRadians(AngleDeg)); };
	for (int32 S = 0; S < 2; ++S)
	{
		const FSide& Side = Sides[S];
		FQuat Chain = FQuat::Identity;
		for (int32 B = 0; B < 3; ++B)
		{
			// Blender Euler XYZ about fixed armature axes = Rz * Ry * Rx
			const FQuat Twist = Towards(Side.Back, Side.Up, Deg[B].X);   // +x: leading edge down
			const FQuat Elev = Towards(Side.Span, Side.Up, -Deg[B].Y);   // +y: tip down
			const FQuat Sweep = Towards(Side.Span, Side.Back, Deg[B].Z); // +z: tip back
			Chain = Chain * (Sweep * Elev * Twist);
			SetBoneRotationByName(Side.Bones[B], (Chain * Side.RefCS[B]).Rotator(), EBoneSpaces::ComponentSpace);
		}
	}
}
