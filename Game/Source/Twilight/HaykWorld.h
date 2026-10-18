#pragma once

#include "CoreMinimal.h"
#include "TwEnvironment.h"
#include "HaykWorld.generated.h"

class UInstancedStaticMeshComponent;

/** «Հայոց ձոր»: the valley of the battle. Two hills, pavises between, Bel's army with torches, Masis behind. */
UCLASS()
class TWILIGHT_API AHaykWorld : public ATwEnvironment
{
	GENERATED_BODY()
public:
	AHaykWorld();
	/** World Z of the valley terrain at (X,Y). */
	static float TerrainZ(float X, float Y);
	void SetNight(bool bInNight) { bNight = bInNight; }

	static constexpr float HaykX = -3800.f;
	static constexpr float BelX = 3800.f;

protected:
	virtual FTwSkyPreset GetSkyPreset() const override;
	virtual void BuildLevel() override;
	virtual const TCHAR* GetStartMusic() const override { return TEXT("music_menu"); }

private:
	void BuildArmy(float X0, float X1, float Y0, float Y1, int32 Count, bool bEnemy, int32 Seed);

	UPROPERTY() TArray<TObjectPtr<UInstancedStaticMeshComponent>> ArmyParts;
	bool bNight = false;
};
