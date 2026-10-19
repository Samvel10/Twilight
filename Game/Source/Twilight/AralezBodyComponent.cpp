#include "AralezBodyComponent.h"
#include "AralezWingComponent.h"
#include "TwPoseAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimSequence.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"

namespace AralezAssets
{
	// paths after running Tools/aralez_import.py with ARZ_DEST=/Game/Twilight/Aralez (Interchange names the clips <Mesh><Clip>)
	template <class T> T* Load(const FString& Path) { return LoadObject<T>(nullptr, *Path); }
	static FString Root = TEXT("/Game/Twilight/Aralez");
	static FString P(const TCHAR* Rel) { return Root / Rel; }
	static const TCHAR* ClipNames[5] = { TEXT("Idle"), TEXT("Glide"), TEXT("Flap"), TEXT("Land"), TEXT("Lick") };
}

UAralezBodyComponent::UAralezBodyComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
}

UTwPoseAnimInstance* UAralezBodyComponent::Anim() const
{
	return Dog ? Cast<UTwPoseAnimInstance>(Dog->GetAnimInstance()) : nullptr;
}

void UAralezBodyComponent::Build()
{
	using namespace AralezAssets;
	Root = AssetRoot;
	AActor* Owner = GetOwner();
	USkeletalMesh* DogMesh = Load<USkeletalMesh>(P(TEXT("Dog/SK_Aralez/SkeletalMeshes/SK_Aralez.SK_Aralez")));
	USkeletalMesh* WingMesh = Load<USkeletalMesh>(P(TEXT("Wings/SK_AralezWings/SkeletalMeshes/SK_AralezWings.SK_AralezWings")));
	if (!Owner || !DogMesh || !WingMesh) { UE_LOG(LogTemp, Warning, TEXT("Aralez assets missing under %s"), *Root); return; }
	for (int32 i = 0; i < 5; ++i)
		Clips[i] = Load<UAnimSequence>(P(*FString::Printf(TEXT("Dog/SK_Aralez/SkeletalMeshes/SK_AralezAralez_%s.SK_AralezAralez_%s"), ClipNames[i], ClipNames[i])));

	Dog = NewObject<USkeletalMeshComponent>(Owner, TEXT("AralezDog"));
	Dog->SetupAttachment(this);
	Dog->SetSkeletalMesh(DogMesh);
	Dog->SetRelativeRotation(FRotator(0.f, -90.f, 0.f));          // mesh faces +Y
	Dog->SetAnimInstanceClass(UTwPoseAnimInstance::StaticClass());
	Dog->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dog->SetBoundsScale(2.f);
	// the glTF import leaves Interchange material instances in the slots (they multiply by vertex colour): always set ours
	if (UMaterialInterface* FurMI = Load<UMaterialInterface>(P(TEXT("Mat/MI_AralezFur.MI_AralezFur")))) Dog->SetMaterial(0, FurMI);
	Dog->RegisterComponent();
	if (UMaterialInstanceDynamic* M = Dog->CreateDynamicMaterialInstance(0)) { M->SetScalarParameterValue(TEXT("RimIntensity"), RimIntensity); RimMats.Add(M); }

	for (int32 i = 1; i <= NumShells; ++i)
	{
		USkeletalMeshComponent* S = NewObject<USkeletalMeshComponent>(Owner);
		S->SetupAttachment(Dog);
		S->SetSkeletalMesh(DogMesh);
		S->SetLeaderPoseComponent(Dog);                                // no extra animation evaluation, only skinning
		S->SetCastShadow(false);
		S->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		S->SetBoundsScale(2.f);
		if (UMaterialInterface* SM = Load<UMaterialInterface>(P(*FString::Printf(TEXT("Mat/MI_AralezFurShell_%d.MI_AralezFurShell_%d"), i, i)))) S->SetMaterial(0, SM);
		S->RegisterComponent();
		Shells.Add(S);
	}

	Wings = NewObject<UAralezWingComponent>(Owner, TEXT("AralezWings"));
	Wings->SetupAttachment(Dog, TEXT("chest_jnt"));
	Wings->SetSkinnedAssetAndUpdate(WingMesh);
	Wings->SetRelativeLocation(FVector(0.f, 4.6f, 5.5f));          // between the shoulder blades (chest_jnt space)
	if (UMaterialInterface* FeatherMI = Load<UMaterialInterface>(P(TEXT("Mat/MI_AralezFeather.MI_AralezFeather")))) Wings->SetMaterial(0, FeatherMI);
	Wings->RegisterComponent();
	if (UMaterialInstanceDynamic* M = Wings->CreateDynamicMaterialInstance(0)) { M->SetScalarParameterValue(TEXT("RimIntensity"), RimIntensity * 1.1f); RimMats.Add(M); }

	if (GlowLight > 0.f)
	{
		Glow = NewObject<UPointLightComponent>(Owner, TEXT("AralezGlow"));
		Glow->SetupAttachment(Dog, TEXT("spine_2_jnt"));
		Glow->SetRelativeLocation(FVector(0.f, 0.f, 60.f));
		Glow->SetIntensity(GlowLight);
		Glow->SetLightColor(FLinearColor(1.f, 0.72f, 0.4f));
		Glow->SetAttenuationRadius(450.f);
		Glow->SetCastShadows(false);
		Glow->RegisterComponent();
	}
	SetMode(EAralezMode::Glide, 0.f);
}

void UAralezBodyComponent::SetMode(EAralezMode InMode, float BlendTime)
{
	Mode = InMode;
	UTwPoseAnimInstance* A = Anim();
	const int32 I = (int32)InMode;
	if (A && Clips[I])
	{
		if (InMode == EAralezMode::Land) { A->SetLoop(Clips[(int32)EAralezMode::Land], BlendTime, 1.f, false); LandTimer = Clips[I]->GetPlayLength(); }
		else A->SetLoop(Clips[I], BlendTime, 1.f, true);
	}
	if (Wings)
	{
		switch (InMode)
		{
		case EAralezMode::Flap:  Wings->SetMode(1.f, 0.f, 0.f, 0.f); break;
		case EAralezMode::Glide: Wings->SetMode(0.f, 1.f, 0.f, 0.f); break;
		case EAralezMode::Land:  Wings->SetMode(0.f, 0.f, 1.f, 0.f); break;
		default:                 Wings->SetMode(0.f, 0.f, 0.f, 1.f); break;   // Idle / Lick: raised arch over the hero
		}
	}
}

void UAralezBodyComponent::TickComponent(float Dt, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(Dt, TickType, ThisTickFunction);
	if (!Dog) return;
	// landing one-shot -> settle into idle
	if (Mode == EAralezMode::Land && (LandTimer -= Dt) <= 0.f) SetMode(EAralezMode::Idle, 0.4f);
	// body bob from the wingbeat (the dog's Flap clip is phase-locked to the wing maths: top of stroke at phase .25)
	if (Wings) Dog->SetRelativeLocation(FVector(0.f, 0.f, Wings->GetBodyLift()));
	// fur shells only near the camera
	if (Shells.Num())
	{
		bool bNear = true;
		if (APlayerCameraManager* Cam = UGameplayStatics::GetPlayerCameraManager(this, 0))
			bNear = FVector::DistSquared(Cam->GetCameraLocation(), Dog->GetComponentLocation()) < FMath::Square(ShellDistance);
		for (USkeletalMeshComponent* S : Shells) if (S && S->IsVisible() != bNear) S->SetVisibility(bNear);
	}
}
