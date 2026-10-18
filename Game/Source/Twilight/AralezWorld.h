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
	/** Wall distance from the axis at path T and angle A (same noise as the mesh). */
	static float WallRadius(float T, float A);
	static constexpr float PathLength = 160000.f; // approx. cm
	/** Underground river (zone 1): water surface height below the path axis, as a fraction of the tunnel radius. */
	static constexpr float RiverT0 = 0.37f, RiverT1 = 0.69f, RiverDepth = 0.56f;

	FVector GetGate() const { return PathPoint(1.f); }

protected:
	virtual FTwSkyPreset GetSkyPreset() const override;
	virtual void BuildLevel() override;
	virtual const TCHAR* GetStartMusic() const override { return TEXT("music_menu"); }

private:
	void BuildTunnel();
	void BuildCrystals();
	void BuildGate();
	void BuildRiver();

	UPROPERTY() TArray<TObjectPtr<UInstancedStaticMeshComponent>> CrystalSets;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> GateCore;
	UPROPERTY() TObjectPtr<UPointLightComponent> GateLight;
	UPROPERTY() TObjectPtr<USceneComponent> GateRing;
	int32 LastZone = -1;
};
