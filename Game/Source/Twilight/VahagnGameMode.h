#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "VahagnGameMode.generated.h"

class AVishap;
class AVahagnCharacter;
class AVahagnWorld;

UENUM()
enum class EVahagnMatch : uint8 { Menu, Intro, Playing, Victory, Defeat };

UENUM()
enum class EVahagnDifficulty : uint8 { Easy, Normal, Hard };

/** Match flow for «Վահագն. Վիշապաքաղ»: waves of vishaps, then the Great Vishap; 8-minute limit. */
UCLASS()
class TWILIGHT_API AVahagnGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	AVahagnGameMode();

	virtual void StartPlay() override;
	virtual void RestartPlayer(AController* NewPlayer) override;
	virtual void Tick(float Dt) override;

	// --- flow
	void StartMatch();
	void RestartMatch();
	void ReturnToMenu();
	EVahagnMatch GetMatchState() const { return MatchState; }
	void SetDifficulty(EVahagnDifficulty D) { Difficulty = D; }
	EVahagnDifficulty GetDifficulty() const { return Difficulty; }
	float DamageToPlayerMultiplier() const;
	float HealthMultiplier() const;

	// --- events from actors
	void OnVishapKilled(AVishap* V);
	void OnBossPhase(AVishap* Boss, int32 Phase);

	// --- HUD queries
	float GetTimeLeft() const { return TimeLeft; }
	int32 GetWave() const { return Wave; }
	int32 GetNumWaves() const { return 3; }
	int32 GetScore() const { return Score; }
	int32 GetKills() const { return Kills; }
	int32 GetBestScore() const { return BestScore; }
	float GetIntroLeft() const { return IntroLeft; }
	float GetMatchTime() const { return MatchTime; }
	AVishap* GetBoss() const { return Boss.Get(); }
	int32 AliveVishaps() const;
	/** Latest announcement (title, subtitle, age seconds). */
	bool GetAnnouncement(FText& Title, FText& Sub, float& Age) const;

	static constexpr float MatchLength = 480.f;

private:
	void BeginWave(int32 Index);
	void SpawnVishap(bool bBoss, int32 Tier, float Dist, float AngleDeg);
	void Announce(const FText& Title, const FText& Sub);
	void EndMatch(bool bVictory);
	void TickAutoTest(float RealDt);
	AVahagnCharacter* Hero() const;

	EVahagnMatch MatchState = EVahagnMatch::Menu;
	EVahagnDifficulty Difficulty = EVahagnDifficulty::Normal;
	float TimeLeft = MatchLength;
	float MatchTime = 0.f;
	float IntroLeft = 0.f;
	int32 Wave = 0;
	float WaveTime = 0.f;
	float NextWaveDelay = -1.f;
	bool bBossSpawned = false;
	int32 Score = 0;
	int32 Kills = 0;
	int32 BestScore = 0;
	float EndTime = 0.f;
	TWeakObjectPtr<AVishap> Boss;
	UPROPERTY() TObjectPtr<AVahagnWorld> World;

	FText AnnTitle, AnnSub;
	float AnnTime = -100.f;

	// automated play-test (-TwAutoPlay=<seconds>)
	float AutoTestSeconds = 0.f;
	float AutoTestElapsed = 0.f;
	float AutoShotTimer = 0.f;
	int32 AutoShotIndex = 0;
	TArray<float> FrameTimes;
	float StatTimer = 0.f;
};
