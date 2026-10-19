#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "Widgets/SCompoundWidget.h"
#include "TwTestHarness.h"
#include "AralezGame.generated.h"

class AAralezSpirit;
class AAralezField;
class AFallenWarrior;
class SAralezHud;
class UInputAction;
class UInputMappingContext;
struct FInputActionValue;

UENUM()
enum class EAralezState : uint8 { Menu, Intro, Race, End };

/** «Արալեզ. Արայի դաշտը»: the Aralez fly down from the clouds onto Ara's battlefield, lick the fallen back to life
 *  while Shamiram's spearmen guard them, and at last raise Ara himself before the sun sets. */
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
	bool DidPlayerWin() const { return bWon; }
	bool GetAnnouncement(FText& Title, FText& Sub, float& Age) const;
	int32 GetRevived() const { return Revived; }
	int32 GetNeed() const { return Need; }
	int32 GetFallenTotal() const { return Warriors.Num() - 1; }
	int32 GetPlayerRevived() const { return PlayerRevived; }
	bool IsAraOpen() const { return bAraOpen; }
	AFallenWarrior* GetAra() const { return Ara; }
	/** Warrior the player is tending right now (null if none) and the nearest one still lying. */
	AFallenWarrior* GetPlayerPatient() const { return PlayerPatient; }
	AFallenWarrior* NearestFallen(const FVector& P) const;
	float GetRealPlayTime() const { return RaceTime; }

	static constexpr float RaceLength = 210.f;
	static constexpr float HealRadius = 480.f;
	static constexpr float HealAltitude = 520.f;

private:
	void SpawnBattlefield();
	void EndRace();
	void TickHealing(float Dt);
	UPROPERTY() TObjectPtr<class ACameraActor> EndCam;
	float EndCamAge = 0.f;
	void StartEndCamera();
	void TickEndCamera(float Dt);
	void Announce(const FText& T, const FText& S);

	UPROPERTY() TObjectPtr<AAralezField> Field;
	UPROPERTY() TArray<TObjectPtr<AAralezSpirit>> RacerRefs;
	UPROPERTY() TArray<TObjectPtr<AFallenWarrior>> Warriors;
	UPROPERTY() TObjectPtr<AFallenWarrior> Ara;
	UPROPERTY() TObjectPtr<AFallenWarrior> PlayerPatient;
	TArray<AAralezSpirit*> Racers;
	AAralezSpirit* PlayerSpirit = nullptr;
	EAralezState State = EAralezState::Menu;
	float TimeLeft = RaceLength;
	float IntroLeft = 3.f;
	float RaceTime = 0.f;
	int32 Revived = 0;
	int32 PlayerRevived = 0;
	int32 Need = 7;
	bool bAraOpen = false;
	bool bWon = false;
	bool bDuskWarned = false;
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
	void OnFreeLook(const FInputActionValue& V);
	void OnFreeLookDone(const FInputActionValue& V);
	void OnFrontView(const FInputActionValue& V);
	void OnSpin(const FInputActionValue& V);

	UPROPERTY() TObjectPtr<UInputMappingContext> Context;
	UPROPERTY() TObjectPtr<UInputAction> IA_Move;
	UPROPERTY() TObjectPtr<UInputAction> IA_Look;
	UPROPERTY() TObjectPtr<UInputAction> IA_Up;
	UPROPERTY() TObjectPtr<UInputAction> IA_Dash;
	UPROPERTY() TObjectPtr<UInputAction> IA_Howl;
	UPROPERTY() TObjectPtr<UInputAction> IA_Pause;
	UPROPERTY() TObjectPtr<UInputAction> IA_FreeLook;
	UPROPERTY() TObjectPtr<UInputAction> IA_Front;
	UPROPERTY() TObjectPtr<UInputAction> IA_Spin;
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
