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
	virtual void Tick(float Dt) override;
	/** 0 = calm sunset, 1 = crimson storm with lightning (the Great Vishap's world). Blends over a few seconds. */
	void SetStorm(bool bOn) { StormTarget = bOn ? 1.f : 0.f; }
	/** The real Geghama highlands + Lake Sevan (streamed sublevel built from DEM data) instead of the procedural sea. */
	static bool UseHighlands();
	/** Offset applied to the highlands level so a spot on Lake Sevan, ~900 m off the west shore, is the arena centre. */
	static FVector HighlandsOffset() { return FVector(-1100000.f, 200000.f, 0.f); }

protected:
	virtual void BuildLevel() override;
	virtual FTwSkyPreset GetSkyPreset() const override;

private:
	void BuildSea();
	void BuildIslands();
	void BuildVishapakar(const FVector& Base, float Yaw, float Scale);
	void BuildSkyDome();
	void BuildMasis(UMaterialInterface* Mat);

	void ApplyStorm(float K);
	void StreamHighlands();
	void AdoptStreamedEnv();
	UPROPERTY() TObjectPtr<class ULevelStreamingDynamic> EnvLevel;
	bool bEnvAdopted = false;
	void StrikeLightning();
	void UpdateBolt(float Dt);

	UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> Sea;
	UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> SeaMat;
	UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> SkyMat;
	UPROPERTY() TObjectPtr<class ACameraActor> DebugCam;
	float SkyExposure = 1.f;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> BoltSegs;
	UPROPERTY() TObjectPtr<class UMaterialInstanceDynamic> BoltMat;
	float Storm = 0.f;
	float StormTarget = 0.f;
	float LastApplied = -1.f;
	float NextStrike = 3.f;
	float BoltAge = 10.f;
	float CapturedAt = 0.f;
};
