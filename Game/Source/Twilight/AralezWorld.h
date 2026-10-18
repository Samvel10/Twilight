#pragma once

#include "CoreMinimal.h"
#include "TwEnvironment.h"
#include "AralezWorld.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMeshComponent;
class UPointLightComponent;

/** The descent: a helical cave tunnel from the surface to the abyss where Ara's soul waits. */
UCLASS()
class TWILIGHT_API AAralezWorld : public ATwEnvironment
{
	GENERATED_BODY()
public:
	AAralezWorld();
	virtual void Tick(float Dt) override;

	// --- the tunnel path, t in [0,1]
	static FVector PathPoint(float T);
	static FVector PathTangent(float T);
	static float TunnelRadius(float T);
	/** Zone index for depth: 0 cave, 1 underground river, 2 abyss. */
	static int32 ZoneAt(float T) { return T < 0.36f ? 0 : (T < 0.7f ? 1 : 2); }
	/** Local search for the path parameter nearest to P, starting from Hint. */
	static float NearestT(const FVector& P, float Hint);
	static constexpr float PathLength = 160000.f; // approx. cm

	FVector GetGate() const { return PathPoint(1.f); }

protected:
	virtual FTwSkyPreset GetSkyPreset() const override;
	virtual void BuildLevel() override;
	virtual const TCHAR* GetStartMusic() const override { return TEXT("music_menu"); }

private:
	void BuildTunnel();
	void BuildCrystals();
	void BuildGate();

	UPROPERTY() TArray<TObjectPtr<UInstancedStaticMeshComponent>> CrystalSets;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> GateCore;
	UPROPERTY() TObjectPtr<UPointLightComponent> GateLight;
	int32 LastZone = -1;
};
