#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "Widgets/SCompoundWidget.h"
#include "TwHub.generated.h"

class ACameraActor;
class AVahagnWorld;
class STwHubWidget;

/** Main menu: three chapters + the codex of Armenian mythology, over a slowly orbiting purple sea. */
UCLASS()
class TWILIGHT_API ATwHubGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	ATwHubGameMode();
	virtual void StartPlay() override;
	virtual void Tick(float Dt) override;
	virtual APawn* SpawnDefaultPawnFor_Implementation(AController* NewPlayer, AActor* StartSpot) override { return nullptr; }
	virtual void RestartPlayer(AController* NewPlayer) override {}
private:
	UPROPERTY() TObjectPtr<ACameraActor> Cam;
	UPROPERTY() TObjectPtr<AVahagnWorld> World;
	float T = 0.f;
};

UCLASS()
class TWILIGHT_API ATwHubController : public APlayerController
{
	GENERATED_BODY()
public:
	ATwHubController();
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;
	void Open(const TCHAR* Map);
	void Quit();
private:
	TSharedPtr<STwHubWidget> Ui;
};

class STwHubWidget : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(STwHubWidget) {}
		SLATE_ARGUMENT(TWeakObjectPtr<ATwHubController>, Owner)
	SLATE_END_ARGS()
	void Construct(const FArguments& Args);
	virtual bool SupportsKeyboardFocus() const override { return true; }
private:
	TSharedRef<SWidget> Card(const FText& Chapter, const FText& Title, const FText& Genre, const FText& Text, const TCHAR* Map, bool bReady);
	TSharedRef<SWidget> Codex();
	TWeakObjectPtr<ATwHubController> Owner;
	bool bCodex = false;
};
