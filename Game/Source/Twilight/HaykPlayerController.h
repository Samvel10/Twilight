#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "HaykPlayerController.generated.h"

class UInputAction;
class UInputMappingContext;
class SHaykHud;
class AHaykGameMode;
struct FInputActionValue;

UENUM()
enum class EHaykScreen : uint8 { None, Menu, Controls, Pause, End };

UCLASS()
class TWILIGHT_API AHaykPlayerController : public APlayerController
{
	GENERATED_BODY()
public:
	AHaykPlayerController();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	virtual void SetupInputComponent() override;

	void OnDuelStarted();
	void OnDuelEnded();
	EHaykScreen GetScreen() const { return Screen; }
	AHaykGameMode* Mode() const;

	void UiVsBot();
	void UiVsFriend();
	void UiControls();
	void UiBack();
	void UiResume();
	void UiRestart();
	void UiMenu();
	void UiHub();
	void UiQuit();

private:
	void SetScreen(EHaykScreen S);
	void OnLook(const FInputActionValue& V);
	void OnDraw(const FInputActionValue& V);
	void OnDrawDone(const FInputActionValue& V);
	void OnSpecial(const FInputActionValue& V);
	void OnPause(const FInputActionValue& V);
	void OnSteerKeys(const FInputActionValue& V);

	UPROPERTY() TObjectPtr<UInputMappingContext> Context;
	UPROPERTY() TObjectPtr<UInputAction> IA_Look;
	UPROPERTY() TObjectPtr<UInputAction> IA_Draw;
	UPROPERTY() TObjectPtr<UInputAction> IA_Special;
	UPROPERTY() TObjectPtr<UInputAction> IA_Pause;
	UPROPERTY() TObjectPtr<UInputAction> IA_Keys;

	TSharedPtr<SHaykHud> Hud;
	EHaykScreen Screen = EHaykScreen::Menu;
};
