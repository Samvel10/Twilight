#include "HaykPlayerController.h"
#include "Twilight.h"
#include "TwFx.h"
#include "HaykGameMode.h"
#include "HaykHud.h"

#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputMappingContext.h"
#include "InputAction.h"
#include "InputModifiers.h"
#include "InputActionValue.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Widgets/SWeakWidget.h"
#include "Framework/Application/SlateApplication.h"

AHaykPlayerController::AHaykPlayerController()
{
	PrimaryActorTick.bTickEvenWhenPaused = true;
	bAutoManageActiveCameraTarget = false;
}

AHaykGameMode* AHaykPlayerController::Mode() const { return GetWorld() ? GetWorld()->GetAuthGameMode<AHaykGameMode>() : nullptr; }

void AHaykPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	Context = NewObject<UInputMappingContext>(this, TEXT("IMC_Hayk"));
	auto Make = [this](const TCHAR* N, EInputActionValueType T) { UInputAction* A = NewObject<UInputAction>(this, N); A->ValueType = T; return A; };
	IA_Look = Make(TEXT("IA_HLook"), EInputActionValueType::Axis2D);
	IA_Draw = Make(TEXT("IA_HDraw"), EInputActionValueType::Boolean);
	IA_Special = Make(TEXT("IA_HSpecial"), EInputActionValueType::Boolean);
	IA_Pause = Make(TEXT("IA_HPause"), EInputActionValueType::Boolean);
	IA_Pause->bTriggerWhenPaused = true;
	IA_Keys = Make(TEXT("IA_HKeys"), EInputActionValueType::Axis2D);
	{
		FEnhancedActionKeyMapping& M = Context->MapKey(IA_Look, EKeys::Mouse2D);
		UInputModifierNegate* N = NewObject<UInputModifierNegate>(this); N->bX = false; N->bY = false; N->bZ = false; M.Modifiers.Add(N);
	}
	{
		FEnhancedActionKeyMapping& M = Context->MapKey(IA_Look, EKeys::Gamepad_Right2D);
		UInputModifierDeadZone* D = NewObject<UInputModifierDeadZone>(this); D->LowerThreshold = 0.2f; M.Modifiers.Add(D);
		UInputModifierScalar* S = NewObject<UInputModifierScalar>(this); S->Scalar = FVector(3.f, 3.f, 1.f); M.Modifiers.Add(S);
	}
	// keyboard fine aim / steering: arrows and WASD
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Keys, EKeys::D); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Keys, EKeys::A); UInputModifierNegate* N = NewObject<UInputModifierNegate>(this); M.Modifiers.Add(N); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Keys, EKeys::W); UInputModifierSwizzleAxis* S = NewObject<UInputModifierSwizzleAxis>(this); M.Modifiers.Add(S); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Keys, EKeys::S); UInputModifierSwizzleAxis* S = NewObject<UInputModifierSwizzleAxis>(this); M.Modifiers.Add(S); UInputModifierNegate* N = NewObject<UInputModifierNegate>(this); M.Modifiers.Add(N); }
	Context->MapKey(IA_Draw, EKeys::LeftMouseButton);
	Context->MapKey(IA_Draw, EKeys::SpaceBar);
	Context->MapKey(IA_Draw, EKeys::Gamepad_RightTrigger);
	Context->MapKey(IA_Special, EKeys::RightMouseButton);
	Context->MapKey(IA_Special, EKeys::Q);
	Context->MapKey(IA_Special, EKeys::Gamepad_FaceButton_Top);
	Context->MapKey(IA_Pause, EKeys::Escape);
	Context->MapKey(IA_Pause, EKeys::P);
	Context->MapKey(IA_Pause, EKeys::Gamepad_Special_Right);

	if (UEnhancedInputComponent* EI = Cast<UEnhancedInputComponent>(InputComponent))
	{
		EI->BindAction(IA_Look, ETriggerEvent::Triggered, this, &AHaykPlayerController::OnLook);
		EI->BindAction(IA_Keys, ETriggerEvent::Triggered, this, &AHaykPlayerController::OnSteerKeys);
		EI->BindAction(IA_Draw, ETriggerEvent::Started, this, &AHaykPlayerController::OnDraw);
		EI->BindAction(IA_Draw, ETriggerEvent::Completed, this, &AHaykPlayerController::OnDrawDone);
		EI->BindAction(IA_Special, ETriggerEvent::Started, this, &AHaykPlayerController::OnSpecial);
		EI->BindAction(IA_Pause, ETriggerEvent::Started, this, &AHaykPlayerController::OnPause);
	}
}

void AHaykPlayerController::BeginPlay()
{
	Super::BeginPlay();
	if (ULocalPlayer* LP = GetLocalPlayer())
		if (UEnhancedInputLocalPlayerSubsystem* Sub = LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
			Sub->AddMappingContext(Context, 0);
	if (GEngine && GEngine->GameViewport && IsLocalController())
	{
		Hud = SNew(SHaykHud).Owner(this);
		GEngine->GameViewport->AddViewportWidgetContent(SNew(SWeakWidget).PossiblyNullContent(Hud.ToSharedRef()), 10);
	}
	const AHaykGameMode* GM = Mode();
	SetScreen(GM && GM->GetState() != EHaykState::Menu ? EHaykScreen::None : EHaykScreen::Menu);
}

void AHaykPlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Hud.IsValid() && GEngine && GEngine->GameViewport) GEngine->GameViewport->RemoveViewportWidgetContent(Hud.ToSharedRef());
	Hud.Reset();
	Super::EndPlay(Reason);
}

void AHaykPlayerController::SetScreen(EHaykScreen S)
{
	Screen = S;
	const bool bUi = S != EHaykScreen::None;
	bShowMouseCursor = bUi;
	if (bUi)
	{
		FInputModeGameAndUI M;
		M.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		M.SetHideCursorDuringCapture(false);
		SetInputMode(M);
	}
	else
	{
		SetInputMode(FInputModeGameOnly());
		FSlateApplication::Get().SetAllUserFocusToGameViewport();
	}
	SetPause(S == EHaykScreen::Pause);
}

void AHaykPlayerController::OnDuelStarted() { SetScreen(EHaykScreen::None); }
void AHaykPlayerController::OnDuelEnded() { SetScreen(EHaykScreen::End); }

void AHaykPlayerController::UiVsBot() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); if (AHaykGameMode* GM = Mode()) GM->StartDuel(true); }
void AHaykPlayerController::UiVsFriend() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); if (AHaykGameMode* GM = Mode()) GM->StartDuel(false); }
void AHaykPlayerController::UiControls() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); SetScreen(EHaykScreen::Controls); }
void AHaykPlayerController::UiBack() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); SetScreen(EHaykScreen::Menu); }
void AHaykPlayerController::UiResume() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); SetScreen(EHaykScreen::None); }
void AHaykPlayerController::UiRestart() { SetPause(false); if (AHaykGameMode* GM = Mode()) GM->Restart(); }
void AHaykPlayerController::UiMenu() { SetPause(false); if (AHaykGameMode* GM = Mode()) GM->ToMenu(); }
void AHaykPlayerController::UiHub() { SetPause(false); UGameplayStatics::OpenLevel(this, TEXT("/Game/Twilight/Maps/L_Menu")); }
void AHaykPlayerController::UiQuit() { UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false); }

void AHaykPlayerController::OnLook(const FInputActionValue& V)
{
	if (Screen != EHaykScreen::None) return;
	AHaykGameMode* GM = Mode();
	if (!GM) return;
	const FVector2D D = V.Get<FVector2D>();
	if (GM->GetState() == EHaykState::Aim) GM->AimDelta(FVector2D(D.X * 0.12f, D.Y * 0.1f));
	else if (GM->GetState() == EHaykState::Flight) GM->SteerArrow(FVector2D(FMath::Clamp(D.X * 0.25f, -1.f, 1.f), FMath::Clamp(D.Y * 0.25f, -1.f, 1.f)));
}

void AHaykPlayerController::OnSteerKeys(const FInputActionValue& V)
{
	if (Screen != EHaykScreen::None) return;
	AHaykGameMode* GM = Mode();
	if (!GM) return;
	const FVector2D D = V.Get<FVector2D>();
	const float Dt = GetWorld()->GetDeltaSeconds();
	if (GM->GetState() == EHaykState::Aim) GM->AimDelta(D * 25.f * Dt);
	else if (GM->GetState() == EHaykState::Flight) GM->SteerArrow(D);
}

void AHaykPlayerController::OnDraw(const FInputActionValue& V) { if (Screen == EHaykScreen::None) if (AHaykGameMode* GM = Mode()) GM->DrawStart(); }
void AHaykPlayerController::OnDrawDone(const FInputActionValue& V) { if (AHaykGameMode* GM = Mode()) GM->DrawRelease(); }
void AHaykPlayerController::OnSpecial(const FInputActionValue& V) { if (Screen == EHaykScreen::None) if (AHaykGameMode* GM = Mode()) GM->ToggleSpecial(); }
void AHaykPlayerController::OnPause(const FInputActionValue& V)
{
	const AHaykGameMode* GM = Mode();
	if (Screen == EHaykScreen::Pause) { UiResume(); return; }
	if (Screen == EHaykScreen::Controls) { UiBack(); return; }
	if (Screen == EHaykScreen::None && GM && GM->GetState() != EHaykState::End) SetScreen(EHaykScreen::Pause);
}
