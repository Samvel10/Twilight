#pragma once

#include "CoreMinimal.h"
#include "TwEnvironment.h"
#include "VahagnWorld.generated.h"

class UStaticMeshComponent;

/** «Ծիրանի ծով»: purple sea at sunset, ring of cliffs, three islands with vishapakar stones, Masis on the horizon. */
UCLASS()
class TWILIGHT_API AVahagnWorld : public ATwEnvironment
{
	GENERATED_BODY()
public:
	AVahagnWorld();

protected:
	virtual void BuildLevel() override;

private:
	void BuildSea();
	void BuildIslands();
	void BuildVishapakar(const FVector& Base, float Yaw, float Scale);

	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Sea;
};
