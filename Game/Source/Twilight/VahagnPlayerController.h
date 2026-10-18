#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "VahagnPlayerController.generated.h"

class UInputAction;
class UInputMappingContext;
class SVahagnHud;
class AVahagnCharacter;
class AVahagnGameMode;
struct FInputActionValue;

UENUM()
enum class EVahagnScreen : uint8 { None, Menu, Controls, Pause, End };

/** Builds input at runtime (no assets), owns the Slate HUD and menu screens. */
UCLASS()
class TWILIGHT_API AVahagnPlayerController : public APlayerController
{
	GENERATED_BODY()
public:
	AVahagnPlayerController();

	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void SetupInputComponent() override;
	virtual void PlayerTick(float Dt) override;

	void OnMatchStarted();
	void OnMatchEnded(bool bVictory);

	// menu actions (called by the HUD)
	void UiPlay();
	void UiControls();
	void UiBack();
	void UiResume();
	void UiRestart();
	void UiMenu();
	void UiQuit();
	void UiCycleDifficulty();

	EVahagnScreen GetScreen() const { return Screen; }
	bool WasVictory() const { return bVictory; }
	AVahagnCharacter* Hero() const;
	AVahagnGameMode* Mode() const;
	float GetMouseSensitivity() const { return MouseSens; }

private:
	void BuildInput();
	void SetScreen(EVahagnScreen S);
	void TogglePause();

	void OnMove(const FInputActionValue& V);
	void OnMoveDone(const FInputActionValue& V);
	void OnLook(const FInputActionValue& V);
	void OnUpDown(const FInputActionValue& V);
	void OnUpDownDone(const FInputActionValue& V);
	void OnFire(const FInputActionValue& V);
	void OnFireDone(const FInputActionValue& V);
	void OnCharge(const FInputActionValue& V);
	void OnChargeDone(const FInputActionValue& V);
	void OnBoost(const FInputActionValue& V);
	void OnBoostDone(const FInputActionValue& V);
	void OnNova(const FInputActionValue& V);
	void OnPause(const FInputActionValue& V);

	UPROPERTY() TObjectPtr<UInputMappingContext> Context;
	UPROPERTY() TObjectPtr<UInputAction> IA_Move;
	UPROPERTY() TObjectPtr<UInputAction> IA_Look;
	UPROPERTY() TObjectPtr<UInputAction> IA_UpDown;
	UPROPERTY() TObjectPtr<UInputAction> IA_Fire;
	UPROPERTY() TObjectPtr<UInputAction> IA_Charge;
	UPROPERTY() TObjectPtr<UInputAction> IA_Boost;
	UPROPERTY() TObjectPtr<UInputAction> IA_Nova;
	UPROPERTY() TObjectPtr<UInputAction> IA_Pause;

	TSharedPtr<SVahagnHud> Hud;
	EVahagnScreen Screen = EVahagnScreen::Menu;
	bool bVictory = false;
	float MouseSens = 0.35f;
	float MenuOrbit = 0.f;
};
