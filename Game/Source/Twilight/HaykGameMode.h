#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "TwTestHarness.h"
#include "HaykGameMode.generated.h"

class AHaykArcher;
class AHaykArrow;
class AHaykWorld;
class ACameraActor;
class UInstancedStaticMeshComponent;

UENUM()
enum class EHaykState : uint8 { Menu, Intro, Aim, Flight, Impact, End };

/** Holds the dotted trajectory preview (instanced glow dots). */
UCLASS()
class TWILIGHT_API AHaykPreview : public AActor
{
	GENERATED_BODY()
public:
	AHaykPreview();
	void Show(const TArray<FVector>& Points);
	void Hide();
private:
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Dots;
	bool bInit = false;
};

/** «Հայկ. Նետի թռիչք»: turn-based archery duel, Hayk vs Bel (bot or second player). */
UCLASS()
class TWILIGHT_API AHaykGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	AHaykGameMode();
	virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;
	virtual void StartPlay() override;
	virtual void Tick(float Dt) override;
	virtual APawn* SpawnDefaultPawnFor_Implementation(AController* NewPlayer, AActor* StartSpot) override { return nullptr; }
	virtual void RestartPlayer(AController* NewPlayer) override {}

	// --- menu / flow
	void StartDuel(bool bVsBot);
	void Restart();
	void ToMenu();
	void ToggleNight();
	void CycleDifficulty() { Difficulty = (Difficulty + 1) % 3; }
	int32 GetDifficulty() const { return Difficulty; }
	bool IsNight() const { return bNight; }

	// --- input from the controller (current human shooter)
	void AimDelta(const FVector2D& Delta);
	void DrawStart();
	void DrawRelease();
	void CancelDraw();
	void ToggleSpecial();
	void SteerArrow(const FVector2D& In);

	// --- HUD queries
	EHaykState GetState() const { return State; }
	AHaykArcher* GetHayk() const { return Hayk; }
	AHaykArcher* GetBel() const { return Bel; }
	bool IsBelTurn() const { return bBelTurn; }
	bool IsHumanTurn() const { return !bAutoBoth && (!bBelTurn || !bVsBot); }
	bool IsVsBot() const { return bVsBot; }
	float GetPower() const { return Power; }
	float GetTurnLeft() const { return TurnLeft; }
	FVector GetWind() const { return Wind; }
	int32 GetSpecials(bool bForBel) const { return bForBel ? SpecialsBel : SpecialsHayk; }
	bool IsSpecialArmed() const { return bSpecialArmed; }
	int32 GetTurn() const { return Turn; }
	bool GetAnnouncement(FText& Title, FText& Sub, float& Age) const;
	bool DidHaykWin() const { return bHaykWon; }
	int32 GetHits(bool bForBel) const { return bForBel ? HitsBel : HitsHayk; }
	int32 GetHeadshots(bool bForBel) const { return bForBel ? HeadsBel : HeadsHayk; }
	AHaykArrow* GetArrow() const { return Arrow.Get(); }

private:
	void BeginTurn();
	void Shoot(float InPower);
	void FinishImpact();
	void UpdateCamera(float Dt);
	void UpdatePreview();
	void ThinkBot(float Dt);
	void SolveBot();
	void Announce(const FText& T, const FText& S);
	AHaykArcher* Shooter() const { return bBelTurn ? Bel : Hayk; }
	AHaykArcher* Target() const { return bBelTurn ? Hayk : Bel; }
	float BaseYawFor(AHaykArcher* A) const;

	UPROPERTY() TObjectPtr<AHaykWorld> World;
	UPROPERTY() TObjectPtr<AHaykArcher> Hayk;
	UPROPERTY() TObjectPtr<AHaykArcher> Bel;
	UPROPERTY() TObjectPtr<ACameraActor> Cam;
	UPROPERTY() TObjectPtr<AHaykPreview> Preview;
	TWeakObjectPtr<AHaykArrow> Arrow;

	EHaykState State = EHaykState::Menu;
	bool bVsBot = true;
	bool bNight = false;
	int32 Difficulty = 1;
	bool bBelTurn = false;
	int32 Turn = 0;
	float StateTime = 0.f;
	float TurnLeft = 25.f;
	float Power = 0.f;
	bool bDrawing = false;
	bool bSpecialArmed = false;
	int32 SpecialsHayk = 1, SpecialsBel = 1;
	int32 HitsHayk = 0, HitsBel = 0, HeadsHayk = 0, HeadsBel = 0;
	int32 StreakHayk = 0, StreakBel = 0;
	FVector Wind = FVector::ZeroVector;
	bool bHaykWon = false;
	bool bSlowMo = false;

	// bot
	float BotYaw = 0.f, BotPitch = 0.f, BotPower = 0.9f;
	float BotTimer = 0.f;
	int32 BotMisses = 0;
	bool bBotSolved = false;

	// camera
	FVector CamPos = FVector::ZeroVector;
	FRotator CamRot = FRotator::ZeroRotator;
	float Orbit = 0.f;
	float CamFov = 72.f;

	FText AnnTitle, AnnSub;
	float AnnTime = -100.f;
	FTwTestHarness Test;
	bool bAutoBoth = false;
};
