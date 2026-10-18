#include "VahagnPlayerController.h"
#include "Twilight.h"
#include "VahagnCharacter.h"
#include "VahagnGameMode.h"
#include "VahagnHud.h"
#include "TwFx.h"

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

AVahagnPlayerController::AVahagnPlayerController()
{
	bShowMouseCursor = false;
	PrimaryActorTick.bTickEvenWhenPaused = true;
}

AVahagnCharacter* AVahagnPlayerController::Hero() const { return Cast<AVahagnCharacter>(GetPawn()); }
AVahagnGameMode* AVahagnPlayerController::Mode() const { return GetWorld() ? GetWorld()->GetAuthGameMode<AVahagnGameMode>() : nullptr; }

static UInputAction* MakeAction(UObject* Outer, const TCHAR* Name, EInputActionValueType Type)
{
	UInputAction* A = NewObject<UInputAction>(Outer, Name);
	A->ValueType = Type;
	return A;
}

static void AddNegate(FEnhancedActionKeyMapping& M, bool bX, bool bY, bool bZ, UObject* Outer)
{
	UInputModifierNegate* N = NewObject<UInputModifierNegate>(Outer);
	N->bX = bX; N->bY = bY; N->bZ = bZ;
	M.Modifiers.Add(N);
}

static void AddSwizzle(FEnhancedActionKeyMapping& M, UObject* Outer)
{
	UInputModifierSwizzleAxis* S = NewObject<UInputModifierSwizzleAxis>(Outer);
	S->Order = EInputAxisSwizzle::YXZ;
	M.Modifiers.Add(S);
}

static void AddScale(FEnhancedActionKeyMapping& M, const FVector& Scale, UObject* Outer)
{
	UInputModifierScalar* S = NewObject<UInputModifierScalar>(Outer);
	S->Scalar = Scale;
	M.Modifiers.Add(S);
}

static void AddDeadZone(FEnhancedActionKeyMapping& M, UObject* Outer)
{
	UInputModifierDeadZone* D = NewObject<UInputModifierDeadZone>(Outer);
	D->LowerThreshold = 0.2f;
	M.Modifiers.Add(D);
}

void AVahagnPlayerController::BuildInput()
{
	if (Context) return;
	Context = NewObject<UInputMappingContext>(this, TEXT("IMC_Vahagn"));
	IA_Move = MakeAction(this, TEXT("IA_Move"), EInputActionValueType::Axis2D);
	IA_Look = MakeAction(this, TEXT("IA_Look"), EInputActionValueType::Axis2D);
	IA_UpDown = MakeAction(this, TEXT("IA_UpDown"), EInputActionValueType::Axis1D);
	IA_Fire = MakeAction(this, TEXT("IA_Fire"), EInputActionValueType::Boolean);
	IA_Charge = MakeAction(this, TEXT("IA_Charge"), EInputActionValueType::Boolean);
	IA_Boost = MakeAction(this, TEXT("IA_Boost"), EInputActionValueType::Boolean);
	IA_Nova = MakeAction(this, TEXT("IA_Nova"), EInputActionValueType::Boolean);
	IA_Pause = MakeAction(this, TEXT("IA_Pause"), EInputActionValueType::Boolean);
	IA_Pause->bTriggerWhenPaused = true;

	// move: W/S -> Y, A/D -> X
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Move, EKeys::W); AddSwizzle(M, this); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Move, EKeys::S); AddSwizzle(M, this); AddNegate(M, true, true, true, this); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Move, EKeys::A); AddNegate(M, true, true, true, this); }
	Context->MapKey(IA_Move, EKeys::D);
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Move, EKeys::Gamepad_Left2D); AddDeadZone(M, this); }

	// look: mouse (y inverted to screen convention), right stick
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Look, EKeys::Mouse2D); AddNegate(M, false, true, false, this); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Look, EKeys::Gamepad_Right2D); AddDeadZone(M, this); AddNegate(M, false, true, false, this); M.Modifiers.Add(NewObject<UInputModifierScaleByDeltaTime>(this)); AddScale(M, FVector(130.f, 90.f, 1.f), this); }

	// up/down
	Context->MapKey(IA_UpDown, EKeys::SpaceBar);
	Context->MapKey(IA_UpDown, EKeys::E);
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_UpDown, EKeys::LeftControl); AddNegate(M, true, true, true, this); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_UpDown, EKeys::C); AddNegate(M, true, true, true, this); }
	Context->MapKey(IA_UpDown, EKeys::Gamepad_FaceButton_Bottom);
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_UpDown, EKeys::Gamepad_FaceButton_Right); AddNegate(M, true, true, true, this); }

	Context->MapKey(IA_Fire, EKeys::LeftMouseButton);
	Context->MapKey(IA_Fire, EKeys::Gamepad_RightTrigger);
	Context->MapKey(IA_Charge, EKeys::RightMouseButton);
	Context->MapKey(IA_Charge, EKeys::Gamepad_LeftTrigger);
	Context->MapKey(IA_Boost, EKeys::LeftShift);
	Context->MapKey(IA_Boost, EKeys::Gamepad_LeftShoulder);
	Context->MapKey(IA_Nova, EKeys::Q);
	Context->MapKey(IA_Nova, EKeys::Gamepad_FaceButton_Top);
	Context->MapKey(IA_Pause, EKeys::Escape);
	Context->MapKey(IA_Pause, EKeys::P);
	Context->MapKey(IA_Pause, EKeys::Gamepad_Special_Right);
}

void AVahagnPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	BuildInput();
	UEnhancedInputComponent* EI = Cast<UEnhancedInputComponent>(InputComponent);
	if (!EI) { UE_LOG(LogTwilight, Error, TEXT("Enhanced input component missing")); return; }
	EI->BindAction(IA_Move, ETriggerEvent::Triggered, this, &AVahagnPlayerController::OnMove);
	EI->BindAction(IA_Move, ETriggerEvent::Completed, this, &AVahagnPlayerController::OnMoveDone);
	EI->BindAction(IA_Look, ETriggerEvent::Triggered, this, &AVahagnPlayerController::OnLook);
	EI->BindAction(IA_UpDown, ETriggerEvent::Triggered, this, &AVahagnPlayerController::OnUpDown);
	EI->BindAction(IA_UpDown, ETriggerEvent::Completed, this, &AVahagnPlayerController::OnUpDownDone);
	EI->BindAction(IA_Fire, ETriggerEvent::Started, this, &AVahagnPlayerController::OnFire);
	EI->BindAction(IA_Fire, ETriggerEvent::Completed, this, &AVahagnPlayerController::OnFireDone);
	EI->BindAction(IA_Charge, ETriggerEvent::Started, this, &AVahagnPlayerController::OnCharge);
	EI->BindAction(IA_Charge, ETriggerEvent::Completed, this, &AVahagnPlayerController::OnChargeDone);
	EI->BindAction(IA_Boost, ETriggerEvent::Started, this, &AVahagnPlayerController::OnBoost);
	EI->BindAction(IA_Boost, ETriggerEvent::Completed, this, &AVahagnPlayerController::OnBoostDone);
	EI->BindAction(IA_Nova, ETriggerEvent::Started, this, &AVahagnPlayerController::OnNova);
	EI->BindAction(IA_Pause, ETriggerEvent::Started, this, &AVahagnPlayerController::OnPause);
}

void AVahagnPlayerController::BeginPlay()
{
	Super::BeginPlay();
	BuildInput();
	if (ULocalPlayer* LP = GetLocalPlayer())
	{
		if (UEnhancedInputLocalPlayerSubsystem* Sub = LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
		{
			Sub->AddMappingContext(Context, 0);
		}
	}
	if (GEngine && GEngine->GameViewport && IsLocalController())
	{
		Hud = SNew(SVahagnHud).Owner(this);
		GEngine->GameViewport->AddViewportWidgetContent(SNew(SWeakWidget).PossiblyNullContent(Hud.ToSharedRef()), 10);
	}
	const AVahagnGameMode* GM = Mode();
	const bool bMenu = !GM || GM->GetMatchState() == EVahagnMatch::Menu;
	SetScreen(bMenu ? EVahagnScreen::Menu : EVahagnScreen::None);
	if (bMenu)
	{
		if (AVahagnCharacter* H = Hero()) { H->SetControlEnabled(false); H->SetMenuFraming(true); }
	}
}

void AVahagnPlayerController::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Hud.IsValid() && GEngine && GEngine->GameViewport)
	{
		GEngine->GameViewport->RemoveAllViewportWidgets();
	}
	Hud.Reset();
	Super::EndPlay(Reason);
}

void AVahagnPlayerController::SetScreen(EVahagnScreen S)
{
	Screen = S;
	const bool bUi = S != EVahagnScreen::None;
	bShowMouseCursor = bUi;
	if (bUi)
	{
		FInputModeGameAndUI Mode;
		Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
		Mode.SetHideCursorDuringCapture(false);
		if (Hud.IsValid()) Mode.SetWidgetToFocus(Hud);
		SetInputMode(Mode);
	}
	else
	{
		SetInputMode(FInputModeGameOnly());
		if (GEngine && GEngine->GameViewport) FSlateApplication::Get().SetAllUserFocusToGameViewport();
	}
	SetPause(S == EVahagnScreen::Pause);
}

void AVahagnPlayerController::PlayerTick(float Dt)
{
	Super::PlayerTick(Dt);
	// slow cinematic orbit behind the menu
	if (Screen == EVahagnScreen::Menu || Screen == EVahagnScreen::Controls)
	{
		MenuOrbit += Dt * 6.f;
		if (AVahagnCharacter* H = Hero()) { H->SetMenuFraming(true); H->SetControlEnabled(false); H->SetActorRotation(FRotator(0.f, GetControlRotation().Yaw + 155.f, 0.f)); }
		SetControlRotation(FRotator(-8.f + 4.f * FMath::Sin(MenuOrbit * 0.05f), 200.f + MenuOrbit, 0.f));
	}
}

void AVahagnPlayerController::OnMatchStarted() { SetScreen(EVahagnScreen::None); if (AVahagnCharacter* H = Hero()) H->SetMenuFraming(false); }
void AVahagnPlayerController::OnMatchEnded(bool bWin) { bVictory = bWin; SetScreen(EVahagnScreen::End); }

void AVahagnPlayerController::UiPlay()
{
	UE_LOG(LogTwilight, Display, TEXT("[TwUi] Play clicked"));
	TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click"));
	if (AVahagnGameMode* GM = Mode()) GM->StartMatch();
}
void AVahagnPlayerController::UiControls() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); SetScreen(EVahagnScreen::Controls); }
void AVahagnPlayerController::UiBack() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); SetScreen(EVahagnScreen::Menu); }
void AVahagnPlayerController::UiResume() { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click")); SetScreen(EVahagnScreen::None); }
void AVahagnPlayerController::UiRestart() { SetPause(false); if (AVahagnGameMode* GM = Mode()) GM->RestartMatch(); }
void AVahagnPlayerController::UiMenu() { SetPause(false); if (AVahagnGameMode* GM = Mode()) GM->ReturnToMenu(); }
void AVahagnPlayerController::UiHub() { SetPause(false); UGameplayStatics::SetGlobalTimeDilation(this, 1.f); UGameplayStatics::OpenLevel(this, TEXT("/Game/Twilight/Maps/L_Menu")); }
void AVahagnPlayerController::UiQuit() { UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false); }
void AVahagnPlayerController::UiCycleDifficulty()
{
	TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_hover"));
	if (AVahagnGameMode* GM = Mode()) GM->SetDifficulty((EVahagnDifficulty)(((int32)GM->GetDifficulty() + 1) % 3));
}

void AVahagnPlayerController::TogglePause()
{
	const AVahagnGameMode* GM = Mode();
	if (!GM) return;
	if (Screen == EVahagnScreen::Pause) { UiResume(); return; }
	if (Screen == EVahagnScreen::None && (GM->GetMatchState() == EVahagnMatch::Playing || GM->GetMatchState() == EVahagnMatch::Intro))
	{
		if (AVahagnCharacter* H = Hero()) { H->InFireStop(); H->InBoostStop(); }
		SetScreen(EVahagnScreen::Pause);
	}
	else if (Screen == EVahagnScreen::Controls) UiBack();
}

// --- input forwarding
void AVahagnPlayerController::OnMove(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InMove(V); }
void AVahagnPlayerController::OnMoveDone(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InMove(FInputActionValue(FVector2D::ZeroVector)); }
void AVahagnPlayerController::OnLook(const FInputActionValue& V)
{
	if (Screen != EVahagnScreen::None) return;
	if (AVahagnCharacter* H = Hero()) H->InLook(FInputActionValue(V.Get<FVector2D>() * MouseSens));
}
void AVahagnPlayerController::OnUpDown(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InUpDown(V); }
void AVahagnPlayerController::OnUpDownDone(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InUpDown(FInputActionValue(0.f)); }
void AVahagnPlayerController::OnFire(const FInputActionValue& V) { if (Screen == EVahagnScreen::None) if (AVahagnCharacter* H = Hero()) H->InFireStart(); }
void AVahagnPlayerController::OnFireDone(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InFireStop(); }
void AVahagnPlayerController::OnCharge(const FInputActionValue& V) { if (Screen == EVahagnScreen::None) if (AVahagnCharacter* H = Hero()) H->InChargeStart(); }
void AVahagnPlayerController::OnChargeDone(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InChargeRelease(); }
void AVahagnPlayerController::OnBoost(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InBoostStart(); }
void AVahagnPlayerController::OnBoostDone(const FInputActionValue& V) { if (AVahagnCharacter* H = Hero()) H->InBoostStop(); }
void AVahagnPlayerController::OnNova(const FInputActionValue& V) { if (Screen == EVahagnScreen::None) if (AVahagnCharacter* H = Hero()) H->InNova(); }
void AVahagnPlayerController::OnPause(const FInputActionValue& V) { TogglePause(); }
