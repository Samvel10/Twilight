#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TwFlash.generated.h"

class UStaticMeshComponent;
class UMaterialInstanceDynamic;

/** Cheap impact flash: one additive sphere that pops and fades (1 primitive, no particles). */
UCLASS()
class TWILIGHT_API ATwFlash : public AActor
{
	GENERATED_BODY()
public:
	ATwFlash();
	void Init(const FLinearColor& Color, float Size, float Duration);
	virtual void Tick(float Dt) override;
private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Mesh;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Mat;
	float Age = 0.f, Dur = 0.25f, Size = 1.f;
};
