#include "SerpentBodyComponent.h"
#include "Engine/SkinnedAsset.h"
#include "ReferenceSkeleton.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"

USerpentBodyComponent::USerpentBodyComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	bUseBoundsFromLeaderPoseComponent = false;
	SetCollisionEnabled(ECollisionEnabled::NoCollision);
	CastShadow = true;
	bCastDynamicShadow = true;
}

float USerpentBodyComponent::GetBodyLength() const
{
	return RestLength * GetComponentScale().X;
}

bool USerpentBodyComponent::InitChain()
{
	Chain.Reset();
	JawIndex = INDEX_NONE;
	const USkinnedAsset* Asset = GetSkinnedAsset();
	ChainAsset = Asset;
	if (!Asset) return false;
	const FReferenceSkeleton& Ref = Asset->GetRefSkeleton();
	const TArray<FTransform>& Local = Ref.GetRefBonePose();
	TArray<FTransform> CS;
	CS.SetNum(Local.Num());
	for (int32 i = 0; i < Local.Num(); ++i)
	{
		const int32 Parent = Ref.GetParentIndex(i);
		CS[i] = Parent == INDEX_NONE ? Local[i] : Local[i] * CS[Parent];
	}
	auto AddLink = [&](int32 Bone)
	{
		FLink L;
		L.Bone = Bone;
		L.RefRotCS = CS[Bone].GetRotation();
		L.Dist = Chain.Num() ? Chain.Last().Dist + FVector::Dist(CS[Chain.Last().Bone].GetLocation(), CS[Bone].GetLocation()) : 0.f;
		Chain.Add(L);
	};
	const int32 Head = Ref.FindBoneIndex(HeadBone);
	if (Head == INDEX_NONE) return false;
	AddLink(Head);
	for (int32 k = 1; k < 1000; ++k)
	{
		const int32 B = Ref.FindBoneIndex(FName(*FString::Printf(TEXT("%s%02d"), *ChainPrefix, k)));
		if (B == INDEX_NONE) break;
		AddLink(B);
	}
	if (Chain.Num() < 3) { Chain.Reset(); return false; }
	RestLength = FMath::Max(1.f, Chain.Last().Dist);
	for (int32 i = 0; i < Chain.Num(); i += 8)
		UE_LOG(LogTemp, Verbose, TEXT("Serpent chain %d %s pos=%s rot=%s dist=%.1f"), i, *Ref.GetBoneName(Chain[i].Bone).ToString(),
			*CS[Chain[i].Bone].GetLocation().ToString(), *CS[Chain[i].Bone].GetRotation().Rotator().ToString(), Chain[i].Dist);

	// body frame at rest: X = towards the head, Z = up (mesh up projected), Y = the remaining axis
	const FVector Fwd = (CS[Chain[0].Bone].GetLocation() - CS[Chain[1].Bone].GetLocation()).GetSafeNormal();
	FVector Up = FVector::UpVector - Fwd * (Fwd | FVector::UpVector);
	if (!Up.Normalize()) Up = FVector::ForwardVector;
	const FQuat RestFrame = FRotationMatrix::MakeFromXZ(Fwd, Up).ToQuat();
	RestFrameInv = RestFrame.Inverse();
	for (FLink& L : Chain)
	{
		L.RefOffsetCS = FVector::ZeroVector;
		// which local bone axis runs along the body (so neck links can thicken without stretching)
		const FVector A = L.RefRotCS.Inverse().RotateVector(Fwd).GetAbs();
		L.LongAxis = A.X >= A.Y && A.X >= A.Z ? 0 : (A.Y >= A.Z ? 1 : 2);
	}

	JawIndex = Ref.FindBoneIndex(JawBone);
	if (JawIndex != INDEX_NONE)
	{
		JawRefLocal = Local[JawIndex];
		// hinge axis = body lateral axis, expressed in the jaw's parent (head) bone space
		const int32 JP = Ref.GetParentIndex(JawIndex);
		const FQuat ParentRot = JP == INDEX_NONE ? FQuat::Identity : CS[JP].GetRotation();
		JawAxisCS = ParentRot.Inverse().RotateVector(RestFrame.GetAxisY());
	}
	const FBoxSphereBounds MB = Asset->GetBounds();
	MaxRadius = FMath::Max(MB.BoxExtent.Y, MB.BoxExtent.Z) * 1.1f + 1.f;
	return true;
}

FVector USerpentBodyComponent::SamplePath(const TArray<FVector>& P, const TArray<float>& Cum, float D, FVector* OutTangent)
{
	const int32 N = P.Num();
	if (D <= 0.f)
	{
		const FVector T = (P[1] - P[0]).GetSafeNormal();
		if (OutTangent) *OutTangent = T;
		return P[0] + T * D;
	}
	if (D >= Cum[N - 1])   // past the end of the path: continue straight
	{
		const FVector T = (P[N - 1] - P[N - 2]).GetSafeNormal();
		if (OutTangent) *OutTangent = T;
		return P[N - 1] + T * (D - Cum[N - 1]);
	}
	// binary search for the segment
	int32 Lo = 0, Hi = N - 1;
	while (Hi - Lo > 1) { const int32 M = (Lo + Hi) / 2; (Cum[M] <= D ? Lo : Hi) = M; }
	const float SegLen = FMath::Max(Cum[Hi] - Cum[Lo], KINDA_SMALL_NUMBER);
	const float A = (D - Cum[Lo]) / SegLen;
	if (OutTangent)
	{
		// smooth tangent: blend the neighbouring segment directions (C1-ish on polylines)
		const FVector T0 = (P[Hi] - P[Lo]).GetSafeNormal();
		const FVector TPrev = Lo > 0 ? (P[Lo] - P[Lo - 1]).GetSafeNormal() : T0;
		const FVector TNext = Hi < N - 1 ? (P[Hi + 1] - P[Hi]).GetSafeNormal() : T0;
		const FVector TA = (TPrev + T0).GetSafeNormal(), TB = (T0 + TNext).GetSafeNormal();
		*OutTangent = FMath::Lerp(TA, TB, A).GetSafeNormal();
	}
	return FMath::Lerp(P[Lo], P[Hi], A);
}

void USerpentBodyComponent::ApplyPath(const TArray<FVector>& Path, FVector UpHint, float TimeSeconds)
{
	if (Path.Num() < 2 || !GetSkinnedAsset()) return;
	if (ChainAsset.Get() != GetSkinnedAsset() || Chain.Num() == 0)
	{
		if (!InitChain()) return;
	}
	const USkinnedAsset* Asset = GetSkinnedAsset();
	const FReferenceSkeleton& Ref = Asset->GetRefSkeleton();
	if (BoneSpaceTransforms.Num() != Ref.GetNum()) return;   // not registered yet
	if (HeadAttachment && !HeadAttachmentComp && GetOwner())
	{
		HeadAttachmentComp = NewObject<UStaticMeshComponent>(GetOwner());
		HeadAttachmentComp->SetStaticMesh(HeadAttachment);
		HeadAttachmentComp->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		HeadAttachmentComp->SetupAttachment(this, HeadBone);
		HeadAttachmentComp->RegisterComponent();
	}

	const int32 N = Chain.Num();
	const float S = GetComponentScale().X;
	const float L = RestLength * S;
	UpHint = UpHint.GetSafeNormal();
	if (UpHint.IsNearlyZero()) UpHint = FVector::UpVector;

	TArray<float> Cum;
	Cum.SetNumUninitialized(Path.Num());
	Cum[0] = 0.f;
	for (int32 i = 1; i < Path.Num(); ++i) Cum[i] = Cum[i - 1] + FVector::Dist(Path[i - 1], Path[i]);

	// 1) centre-line samples and base frames (parallel transport of the up vector from the head)
	TArray<FVector> Pos, Fwd, Up;
	Pos.SetNum(N); Fwd.SetNum(N); Up.SetNum(N);
	for (int32 i = 0; i < N; ++i)
	{
		FVector T;
		Pos[i] = SamplePath(Path, Cum, Chain[i].Dist * S, &T);
		Fwd[i] = -T;   // path runs head -> tail, the body faces the head
	}
	auto Transport = [&](const FVector& PrevUp, const FVector& F)
	{
		FVector U = PrevUp - F * (F | PrevUp);
		FVector Upright = UpHint - F * (F | UpHint);
		if (Upright.Normalize()) U = FMath::Lerp(U.GetSafeNormal(), Upright, UprightBlend);
		if (!U.Normalize()) U = FVector::CrossProduct(F, FVector::RightVector).GetSafeNormal();
		return U;
	};
	Up[0] = Transport(UpHint, Fwd[0]);
	for (int32 i = 1; i < N; ++i) Up[i] = Transport(Up[i - 1], Fwd[i]);

	// bank (roll into turns) from the curvature of the *path* (not of the swim wave, which would corkscrew the body);
	// smoothed along the body so neighbouring links never roll against each other
	TArray<float> BankDeg;
	BankDeg.Init(0.f, N);
	if (BankPerCurvature > 0.f)
	{
		for (int32 i = 1; i < N - 1; ++i)
		{
			const float Ds = FMath::Max(FVector::Dist(Pos[i - 1], Pos[i + 1]), 1.f);
			const FVector Kv = (Fwd[i - 1] - Fwd[i + 1]) / (0.5f * Ds) * 100.f;     // curvature vector, 1/m
			const FVector Side = FVector::CrossProduct(Up[i], Fwd[i]);
			BankDeg[i] = FMath::Clamp(BankPerCurvature * (Kv | Side), -MaxBank, MaxBank);
		}
		BankDeg[0] = BankDeg[1]; BankDeg[N - 1] = BankDeg[N - 2];
		for (int32 Pass = 0; Pass < 3; ++Pass)
		{
			TArray<float> B2 = BankDeg;
			for (int32 i = 1; i < N - 1; ++i) B2[i] = 0.25f * BankDeg[i - 1] + 0.5f * BankDeg[i] + 0.25f * BankDeg[i + 1];
			BankDeg = B2;
		}
	}

	// 2) travelling swim wave (lateral + a bit vertical), small at the head, full along the body
	if (WaveAmplitude > 0.f && WaveLength > 0.f)
	{
		const float K = 2.f * PI / (WaveLength * L);
		const float W = 2.f * PI * WaveSpeed;
		for (int32 i = 1; i < N; ++i)
		{
			const float D = Chain[i].Dist * S;
			const float X = D / L;
			const float Env = FMath::SmoothStep(0.f, 0.18f, X) * (0.55f + 0.45f * X);
			const FVector Side = FVector::CrossProduct(Up[i], Fwd[i]).GetSafeNormal();
			const float Ph = K * D - W * TimeSeconds;
			Pos[i] += (Side * FMath::Sin(Ph) + Up[i] * (WaveVertical * FMath::Sin(Ph * 0.5f + 1.3f))) * (WaveAmplitude * L * Env);
		}
	}

	// 3) final forward from the posed neighbours, bank into turns, then bone transforms
	TArray<FTransform> CS;
	CS.SetNum(Ref.GetNum());
	const TArray<FTransform>& RefLocal = Ref.GetRefBonePose();
	const FTransform& C2W = GetComponentTransform();
	PosedCS.SetNum(N);
	PosedWorld.SetNum(N);
	TArray<bool> IsChain;
	IsChain.Init(false, Ref.GetNum());
	for (int32 i = 0; i < N; ++i)
	{
		FVector F = i == 0 ? (Pos[0] - Pos[1]) : (i == N - 1 ? (Pos[i - 1] - Pos[i]) : (Pos[i - 1] - Pos[i + 1]));
		F = F.GetSafeNormal();
		if (i == 0) F = (F + Fwd[0]).GetSafeNormal();   // keep the head steadier than the wave
		FVector U = Up[i] - F * (F | Up[i]);
		if (!U.Normalize()) U = Up[i];
		if (BankDeg[i] != 0.f) U = FQuat(F, -FMath::DegreesToRadians(BankDeg[i])).RotateVector(U);   // tilt the back into the turn
		const FQuat BodyQ = FRotationMatrix::MakeFromXZ(F, U).ToQuat();
		const FTransform World(BodyQ * RestFrameInv * Chain[i].RefRotCS, Pos[i], FVector(S));
		CS[Chain[i].Bone] = World.GetRelativeTransform(C2W);
		// head bigger; the first neck links blend from HeadScale back to 1 so there is no step
		const float Sc = i == 0 ? HeadScale : FMath::Lerp(HeadScale, 1.f, FMath::Clamp(i / 4.f, 0.f, 1.f));
		FVector Sv(Sc);
		if (i > 0) Sv[Chain[i].LongAxis] = 1.f;   // neck: thicker cross-section only, no overlap along the body
		CS[Chain[i].Bone].SetScale3D(Sv);
		IsChain[Chain[i].Bone] = true;
		PosedCS[i] = CS[Chain[i].Bone].GetLocation();
		PosedWorld[i] = Pos[i];
	}
	// 4) everything else follows its parent with the reference local pose (jaw opens around its hinge)
	for (int32 b = 0; b < Ref.GetNum(); ++b)
	{
		const int32 Parent = Ref.GetParentIndex(b);
		if (!IsChain[b])
		{
			FTransform LocalT = RefLocal[b];
			if (b == JawIndex && JawOpen != 0.f)
				LocalT.SetRotation(FQuat(JawAxisCS, FMath::DegreesToRadians(JawMaxDegrees * JawOpen)) * LocalT.GetRotation());
			CS[b] = Parent == INDEX_NONE ? LocalT : LocalT * CS[Parent];
		}
		BoneSpaceTransforms[b] = Parent == INDEX_NONE ? CS[b] : CS[b].GetRelativeTransform(CS[Parent]);
	}
	RefreshBoneTransforms();
	UpdateLod();
}

void USerpentBodyComponent::UpdateLod()
{
	if (LodDistances.Num() == 0 || PosedWorld.Num() == 0) return;
	const UWorld* W = GetWorld();
	const APlayerController* PC = W ? W->GetFirstPlayerController() : nullptr;
	if (!PC || !PC->PlayerCameraManager) return;
	const FVector Cam = PC->PlayerCameraManager->GetCameraLocation();
	float Best = TNumericLimits<float>::Max();
	for (int32 i = 0; i < PosedWorld.Num(); i += 2) Best = FMath::Min(Best, FVector::DistSquared(Cam, PosedWorld[i]));
	const float D = FMath::Sqrt(Best) / FMath::Max(GetComponentScale().X, 0.01f);
	int32 Lod = 0;
	while (Lod < LodDistances.Num() && D > LodDistances[Lod]) ++Lod;
	const int32 NumLods = GetSkinnedAsset() ? GetNumLODs() : 1;
	SetForcedLOD(FMath::Min(Lod, NumLods - 1) + 1);   // ForcedLOD is 1-based (0 = automatic)
}

FVector USerpentBodyComponent::GetBodyPoint(float Alpha) const
{
	if (PosedWorld.Num() < 2) return GetComponentLocation();
	const float F = FMath::Clamp(Alpha, 0.f, 1.f) * (PosedWorld.Num() - 1);
	const int32 I = FMath::Min(FMath::FloorToInt(F), PosedWorld.Num() - 2);
	return FMath::Lerp(PosedWorld[I], PosedWorld[I + 1], F - I);
}

FBoxSphereBounds USerpentBodyComponent::CalcBounds(const FTransform& LocalToWorld) const
{
	if (PosedCS.Num() < 2) return Super::CalcBounds(LocalToWorld);
	FBox Box(ForceInit);
	for (const FVector& P : PosedCS) Box += P;
	Box = Box.ExpandBy(MaxRadius * 1.6f);   // head width + jaw
	return FBoxSphereBounds(Box.TransformBy(LocalToWorld));
}
