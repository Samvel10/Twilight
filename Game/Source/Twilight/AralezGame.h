#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "Widgets/SCompoundWidget.h"
#include "TwTestHarness.h"
#include "AralezGame.generated.h"

class AAralezSpirit;
class AAralezWorld;
class SAralezHud;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

UENUM()
enum class EAralezState : uint8 { Menu, Intro, Race, End };

/** «Արալեզ»: race down to the abyss collecting Ara's soul-lights; most lights wins, finishing order gives a bonus. */
UCLASS()
class TWILIGHT_API AAralezGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	AAralezGameMode();
	virtual void StartPlay() override;
	virtual void Tick(float Dt) override;
	virtual void RestartPlayer(AController* NewPlayer) override;

	void StartRace();
	void Restart();
	void ToMenu();

	EAralezState GetState() const { return State; }
	float GetTimeLeft() const { return TimeLeft; }
	float GetIntroLeft() const { return IntroLeft; }
	const TArray<AAralezSpirit*>& GetRacers() const { return Racers; }
	AAralezSpirit* GetPlayerSpirit() const { return PlayerSpirit; }
	int32 ScoreOf(const AAralezSpirit* S) const;
	int32 RankOf(const AAralezSpirit* S) const;
	bool DidPlayerWin() const { return RankOf(PlayerSpirit) == 1; }
	bool GetAnnouncement(FText& Title, FText& Sub, float& Age) const;
	int32 GetZone() const { return Zone; }

	static constexpr float RaceLength = 300.f;

private:
	void SpawnLightsAndWraiths();
	void EndRace();
	void Announce(const FText& T, const FText& S);

	UPROPERTY() TObjectPtr<AAralezWorld> World;
	UPROPERTY() TArray<TObjectPtr<AAralezSpirit>> RacerRefs;
	TArray<AAralezSpirit*> Racers;
	AAralezSpirit* PlayerSpirit = nullptr;
	EAralezState State = EAralezState::Menu;
	float TimeLeft = RaceLength;
	float IntroLeft = 3.f;
	float RaceTime = 0.f;
	int32 Finished = 0;
	int32 Zone = 0;
	TMap<const AAralezSpirit*, int32> FinishBonus;
	TMap<const AAralezSpirit*, int32> FrozenScore;
	FText AnnTitle, AnnSub;
	float AnnTime = -100.f;
	FTwTestHarness Test;
};

UENUM()
enum class EAralezScreen : uint8 { None, Menu, Pause, End };

UCLASS()
class TWILIGHT_API AAralezController : public APlayerController
{
	GENERATED_BODY()
public:
	AAralezController();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void SetupInputComponent() override;
	void SetScreen(EAralezScreen S);
	EAralezScreen GetScreen() const { return Screen; }
	AAralezGameMode* Mode() const;
	AAralezSpirit* Spirit() const;
private:
	void OnMove(const FInputActionValue& V);
	void OnMoveDone(const FInputActionValue& V);
	void OnLook(const FInputActionValue& V);
	void OnUp(const FInputActionValue& V);
	void OnUpDone(const FInputActionValue& V);
	void OnDash(const FInputActionValue& V);
	void OnHowl(const FInputActionValue& V);
	void OnPause(const FInputActionValue& V);

	UPROPERTY() TObjectPtr<UInputMappingContext> Context;
	UPROPERTY() TObjectPtr<UInputAction> IA_Move;
	UPROPERTY() TObjectPtr<UInputAction> IA_Look;
	UPROPERTY() TObjectPtr<UInputAction> IA_Up;
	UPROPERTY() TObjectPtr<UInputAction> IA_Dash;
	UPROPERTY() TObjectPtr<UInputAction> IA_Howl;
	UPROPERTY() TObjectPtr<UInputAction> IA_Pause;
	TSharedPtr<SAralezHud> Hud;
	EAralezScreen Screen = EAralezScreen::Menu;
};

class SAralezHud : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SAralezHud) {}
		SLATE_ARGUMENT(TWeakObjectPtr<AAralezController>, Owner)
	SLATE_END_ARGS()
	void Construct(const FArguments& Args);
	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geo, const FSlateRect& Cull, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const override;
	virtual bool SupportsKeyboardFocus() const override { return true; }
private:
	EVisibility VisFor(uint8 S) const;
	TWeakObjectPtr<AAralezController> Owner;
};
