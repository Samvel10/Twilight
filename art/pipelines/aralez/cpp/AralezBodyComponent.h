#pragma once

#include "CoreMinimal.h"
#include "Components/SceneComponent.h"
#include "AralezBodyComponent.generated.h"

class USkeletalMeshComponent;
class UAralezWingComponent;
class UTwPoseAnimInstance;
class UAnimSequence;
class UPointLightComponent;
class UMaterialInstanceDynamic;

UENUM()
enum class EAralezMode : uint8 { Idle, Glide, Flap, Land, Lick };

/**
 * The realistic Aralez: SK_Aralez (CC-BY Shiba-Inu rig by quander, rescaled to a gampr-sized dog) driven by
 * UTwPoseAnimInstance clips, SK_AralezWings (procedural feather cards) attached at chest_jnt and flapped by
 * UAralezWingComponent, optional fur shells (leader-posed copies, close range only) and a faint warm fill light.
 * Drop-in replacement for AAralezSpirit::BuildBody(): create it under BodyRoot and call SetMode() from Move().
 * Mesh space: the dog faces +Y, so the component yaws the meshes -90 to face the owner's +X.
 */
UCLASS(ClassGroup = (Twilight), meta = (BlueprintSpawnableComponent))
class TWILIGHT_API UAralezBodyComponent : public USceneComponent
{
	GENERATED_BODY()
public:
	UAralezBodyComponent();

	/** Creates the dog, wings, shells and light (call once, e.g. from the owner's BeginPlay). */
	void Build();
	void SetMode(EAralezMode Mode, float BlendTime = 0.3f);
	EAralezMode GetMode() const { return Mode; }

	USkeletalMeshComponent* GetDog() const { return Dog; }
	UAralezWingComponent* GetWings() const { return Wings; }

	/** Content folder holding Dog/, Wings/, Mat/ (as written by the import script). */
	UPROPERTY(EditAnywhere, Category = "Aralez") FString AssetRoot = TEXT("/Game/Twilight/Aralez");
	/** Fur shells cost ~0.3 ms each at 5 m on Iris Xe; they are hidden beyond ShellDistance. */
	UPROPERTY(EditAnywhere, Category = "Aralez") int32 NumShells = 2;
	UPROPERTY(EditAnywhere, Category = "Aralez") float ShellDistance = 900.f;
	/** Divine rim (fresnel emissive) on fur + feathers; 0.15-0.25 reads as sunlit, >0.5 looks fake. */
	UPROPERTY(EditAnywhere, Category = "Aralez") float RimIntensity = 0.18f;
	/** Small warm point light carried on the back (no shadows). */
	UPROPERTY(EditAnywhere, Category = "Aralez") float GlowLight = 12.f;

	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
	UPROPERTY() TObjectPtr<USkeletalMeshComponent> Dog;
	UPROPERTY() TObjectPtr<UAralezWingComponent> Wings;
	UPROPERTY() TArray<TObjectPtr<USkeletalMeshComponent>> Shells;
	UPROPERTY() TObjectPtr<UPointLightComponent> Glow;
	UPROPERTY() TObjectPtr<UAnimSequence> Clips[5];
	UPROPERTY() TArray<TObjectPtr<UMaterialInstanceDynamic>> RimMats;

	UTwPoseAnimInstance* Anim() const;
	EAralezMode Mode = EAralezMode::Glide;
	float LandTimer = 0.f;
};
