#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AralezBodyComponent.h"
#include "AralezShowcase.generated.h"

/** Test/showcase actor: builds an Aralez and either holds one mode or cycles Glide -> Flap -> Land -> Lick. */
UCLASS()
class TWILIGHT_API AAralezShowcase : public AActor
{
	GENERATED_BODY()
public:
	AAralezShowcase();
	UPROPERTY(VisibleAnywhere) TObjectPtr<UAralezBodyComponent> Body;
	UPROPERTY(EditAnywhere) FString AssetRoot = TEXT("/Game/Aralez");
	/** -1 = cycle, else EAralezMode index held */
	UPROPERTY(EditAnywhere) int32 FixedMode = -1;
	UPROPERTY(EditAnywhere) float FlapHz = 1.1f;
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;
private:
	float T = 0.f; int32 Stage = -1;
};
