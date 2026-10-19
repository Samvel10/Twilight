#include "AralezGame.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "TwUi.h"
#include "AralezField.h"
#include "AralezSpirit.h"
#include "AralezActors.h"

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
#include "Fonts/FontMeasure.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Widgets/SWeakWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "Framework/Application/SlateApplication.h"
#include "EngineUtils.h"
#include "Misc/App.h"

#define LOCTEXT_NAMESPACE "Aralez"

using namespace TwUi;

// ================================================================== game mode
AAralezGameMode::AAralezGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	DefaultPawnClass = nullptr;
	PlayerControllerClass = AAralezController::StaticClass();
	HUDClass = nullptr;
}

void AAralezGameMode::StartPlay()
{
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Field = GetWorld()->SpawnActor<AAralezField>(FVector::ZeroVector, FRotator::ZeroRotator, P);
	Super::StartPlay();
	if (Test.Init()) { if (PlayerSpirit) PlayerSpirit->SetBotDriven(true); StartRace(); }
	else if (UGameplayStatics::HasOption(OptionsString, TEXT("TwStart"))) StartRace();
}

void AAralezGameMode::RestartPlayer(AController* NewPlayer)
{
	// the player and two sister Aralez come down out of the clouds
	const struct { FLinearColor Col; const TCHAR* Name; } Pack[2] = {
		{ FLinearColor(1.f, 0.78f, 0.4f), TEXT("Ոսկեթև") },
		{ FLinearColor(0.8f, 0.85f, 1.f), TEXT("Լուսնակ") },
	};
	// west of the field, facing east: the battlefield ahead, Masis on the horizon, the sun low on the left
	const FVector Start(-26000.f, 0.f, AAralezField::GroundZ(-26000.f, 0.f) + 5200.f);
	const FVector Fwd(1.f, 0.f, 0.f);
	const FVector Right(0.f, 1.f, 0.f);
	auto Spawn = [&](const FVector& Off, bool bBot, const FLinearColor& C, const FText& Name, int32 Skill) -> AAralezSpirit*
	{
		FActorSpawnParameters S;
		S.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		S.bDeferConstruction = true;
		const FTransform T(FRotator(-12.f, 0.f, 0.f), Start + Off);
		AAralezSpirit* A = GetWorld()->SpawnActor<AAralezSpirit>(AAralezSpirit::StaticClass(), T, S);
		if (!A) return nullptr;
		A->Setup(bBot, C, Name, Skill);
		A->SetField(true);
		UGameplayStatics::FinishSpawningActor(A, T);
		A->SetControlEnabled(false);
		RacerRefs.Add(A);
		Racers.Add(A);
		return A;
	};
	PlayerSpirit = Spawn(FVector::ZeroVector, false, FLinearColor(0.55f, 0.85f, 1.f), LOCTEXT("You", "Դու"), 1);
	for (int32 i = 0; i < 2; ++i) Spawn(Right * (i == 0 ? -900.f : 900.f) + Fwd * -500.f + FVector(0, 0, 300.f), true, Pack[i].Col, FText::FromString(Pack[i].Name), i);
	if (PlayerSpirit && NewPlayer)
	{
		NewPlayer->Possess(PlayerSpirit);
		NewPlayer->SetControlRotation(FRotator(-14.f, 0.f, 0.f));
	}
}

void AAralezGameMode::SpawnBattlefield()
{
	FRandomStream R(1937);
	FActorSpawnParameters S;
	S.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	S.bDeferConstruction = true;
	auto SpawnWarrior = [&](const FVector2D& XY, float Yaw, bool bIsAra) -> AFallenWarrior*
	{
		const FTransform T(FRotator(0.f, Yaw, 0.f), FVector(XY.X, XY.Y, AAralezField::GroundZ(XY.X, XY.Y) + 2.f));
		AFallenWarrior* W = GetWorld()->SpawnActor<AFallenWarrior>(AFallenWarrior::StaticClass(), T, S);
		if (!W) return nullptr;
		W->Setup(bIsAra);
		UGameplayStatics::FinishSpawningActor(W, T);
		Warriors.Add(W);
		return W;
	};
	auto SpawnGuard = [&](const FVector2D& XY)
	{
		const FTransform T(FRotator(0.f, R.FRandRange(0.f, 360.f), 0.f), FVector(XY.X, XY.Y, AAralezField::GroundZ(XY.X, XY.Y)));
		if (AShamiramSoldier* G = GetWorld()->SpawnActor<AShamiramSoldier>(AShamiramSoldier::StaticClass(), T, S))
		{
			G->SetPost(T.GetLocation());
			UGameplayStatics::FinishSpawningActor(G, T);
		}
	};
	// the fallen lie in knots where the fighting was hardest, spread around Ara's last stand
	const FVector2D Knots[5] = { {-9000.f, -14000.f}, {11000.f, -9000.f}, {-15000.f, 4000.f}, {14000.f, 9000.f}, {-2000.f, 17000.f} };
	const int32 PerKnot[5] = { 2, 3, 2, 3, 2 };
	for (int32 k = 0; k < 5; ++k)
	{
		for (int32 i = 0; i < PerKnot[k]; ++i)
			SpawnWarrior(Knots[k] + FVector2D(R.FRandRange(-1400.f, 1400.f), R.FRandRange(-1400.f, 1400.f)), R.FRandRange(0.f, 360.f), false);
		// one or two of Shamiram's spearmen stand watch over each knot
		for (int32 g = 0; g < (k % 2 == 0 ? 1 : 2); ++g)
			SpawnGuard(Knots[k] + FVector2D(R.FRandRange(-1800.f, 1800.f), R.FRandRange(-1800.f, 1800.f)));
	}
	// Ara in the middle, guarded by four
	Ara = SpawnWarrior(FVector2D(0.f, 0.f), 30.f, true);
	if (Ara) Ara->SetLocked(true);
	for (int32 g = 0; g < 4; ++g)
	{
		const float A = g * PI * 0.5f + 0.4f;
		SpawnGuard(FVector2D(FMath::Cos(A), FMath::Sin(A)) * 1500.f);
	}
	Need = FMath::Min(8, Warriors.Num() - 1);
}

AFallenWarrior* AAralezGameMode::NearestFallen(const FVector& P) const
{
	AFallenWarrior* Best = nullptr;
	float BD = TNumericLimits<float>::Max();
	for (AFallenWarrior* W : Warriors)
	{
		if (!W || W->IsRevived() || W->IsLocked()) continue;
		const float D = FVector::Dist2D(W->GetActorLocation(), P);
		if (D < BD) { BD = D; Best = W; }
	}
	return Best;
}

void AAralezGameMode::Announce(const FText& T, const FText& S) { AnnTitle = T; AnnSub = S; AnnTime = GetWorld()->GetRealTimeSeconds(); }
bool AAralezGameMode::GetAnnouncement(FText& Title, FText& Sub, float& Age) const
{
	Age = GetWorld()->GetRealTimeSeconds() - AnnTime; Title = AnnTitle; Sub = AnnSub; return Age < 3.5f;
}

void AAralezGameMode::StartRace()
{
	if (State != EAralezState::Menu) return;
	SpawnBattlefield();
	State = EAralezState::Intro;
	IntroLeft = 3.f;
	TimeLeft = RaceLength;
	if (Field) Field->PlayMusic(TEXT("music_aralez"));
	TwFx::Sound2D(GetWorld(), TEXT("sfx_wind_loop"), 0.5f);
	Announce(LOCTEXT("Intro", "Իջի՛ր Արայի դաշտը"), LOCTEXT("IntroSub", "Գտի՛ր ընկած քաջերին, իջի՛ր նրանց մոտ և կենդանացրո՛ւ նրանց"));
	if (AAralezController* PC = Cast<AAralezController>(UGameplayStatics::GetPlayerController(this, 0))) PC->SetScreen(EAralezScreen::None);
}

void AAralezGameMode::Restart() { UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true, TEXT("TwStart=1")); }
void AAralezGameMode::ToMenu() { UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true); }

void AAralezGameMode::TickHealing(float Dt)
{
	PlayerPatient = nullptr;
	for (AAralezSpirit* Sp : Racers)
	{
		if (!Sp || Sp->GetStun() > 0.f) continue;
		const FVector P = Sp->GetActorLocation();
		AFallenWarrior* W = NearestFallen(P);
		if (!W) continue;
		const float D = FVector::Dist2D(W->GetActorLocation(), P);
		if (D > AAralezGameMode::HealRadius || Sp->GetAltitude() > AAralezGameMode::HealAltitude) continue;
		if (Sp->GetVel().Size() > 1100.f) continue; // a hurried pass heals nothing
		if (Sp == PlayerSpirit) PlayerPatient = W;
		// Ara needs the whole pack; a lone bot is slow
		float Rate = (Sp->IsBot() ? 1.f / 4.5f : 1.f / 2.4f);
		if (W->IsAra()) Rate *= 0.45f;
		if (W->Heal(Rate * Dt))
		{
			if (W->IsAra())
			{
				bWon = true;
				EndRace();
				return;
			}
			++Revived;
			if (Sp == PlayerSpirit) ++PlayerRevived;
			if (!bAraOpen && Revived >= Need)
			{
				bAraOpen = true;
				if (Ara) Ara->SetLocked(false);
				TwFx::Sound2D(GetWorld(), TEXT("sfx_gate_open"), 0.8f);
				Announce(LOCTEXT("AraOpen", "Արան սպասում է"), LOCTEXT("AraOpenSub", "Քաջերը ոտքի են։ Թռի՛ր դաշտի կենտրոն և կենդանացրո՛ւ թագավորին"));
			}
			else if (Sp == PlayerSpirit)
				Announce(LOCTEXT("Rose", "Քաջը ոտքի կանգնեց"), FText::Format(LOCTEXT("RoseSub", "Կենդանացած՝ {0} / {1}"), FText::AsNumber(Revived), FText::AsNumber(Need)));
		}
	}
}

void AAralezGameMode::EndRace()
{
	if (State == EAralezState::End) return;
	AnnTime = -100.f;
	State = EAralezState::End;
	for (AAralezSpirit* S : Racers) S->SetControlEnabled(false);
	if (Field) Field->PlayMusic(TEXT("music_menu"));
	TwFx::Sound2D(GetWorld(), bWon ? TEXT("sfx_victory") : TEXT("sfx_defeat"), 1.f);
	if (bWon && Ara)
	{
		const FVector G = Ara->GetActorLocation();
		TwFx::Sound2D(GetWorld(), TEXT("sfx_gate_open"), 1.f);
		for (int32 i = 0; i < 6; ++i) TwFx::Burst(GetWorld(), TwFx::EFx::Nova, G + FVector(0, 0, 200.f + i * 700.f), 2.5f);
		TwFx::LightFlash(GetWorld(), G + FVector(0, 0, 300.f), FLinearColor(1.f, 0.85f, 0.55f), 200000.f, 9000.f, 4.f);
	}
	if (AAralezController* PC = Cast<AAralezController>(UGameplayStatics::GetPlayerController(this, 0))) PC->SetScreen(EAralezScreen::End);
	StartEndCamera();
}

void AAralezGameMode::StartEndCamera()
{
	if (!Ara || EndCam) return;
	EndCamAge = 0.f;
	EndCam = GetWorld()->SpawnActor<ACameraActor>(Ara->GetActorLocation() + FVector(0, -900.f, 300.f), FRotator::ZeroRotator);
	if (!EndCam) return;
	EndCam->GetCameraComponent()->SetFieldOfView(60.f);
	EndCam->GetCameraComponent()->bConstrainAspectRatio = false;
	TickEndCamera(0.f);
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
		PC->SetViewTargetWithBlend(EndCam, 2.2f, VTBlend_EaseInOut, 2.f);
}

void AAralezGameMode::TickEndCamera(float Dt)
{
	if (!EndCam || !Ara) return;
	EndCamAge += Dt;
	// slow orbit around the king (risen, or still lying while Shamiram's men close in)
	const float A = -1.2f + EndCamAge * 0.08f;
	const FVector C = Ara->GetActorLocation() + FVector(0, 0, bWon ? 120.f : 30.f);
	// low and wide: the king against the dusk sky, the field and Masis behind him
	const FVector Loc = C + FVector(FMath::Cos(A), FMath::Sin(A), 0.f) * 1500.f + FVector(0, 0, bWon ? 20.f : 380.f);
	EndCam->SetActorLocationAndRotation(Loc, (C + FVector(0, 0, bWon ? 260.f : -120.f) - Loc).Rotation());
}

void AAralezGameMode::Tick(float Dt)
{
	Super::Tick(Dt);
	if (Test.IsActive())
	{
		Test.Tick(GetWorld(), FApp::GetDeltaTime(), FString::Printf(TEXT("state=%d time=%.0f revived=%d/%d mine=%d ara_open=%d won=%d alt=%.0f"), (int32)State, TimeLeft, Revived, Need, PlayerRevived, bAraOpen ? 1 : 0, bWon ? 1 : 0, PlayerSpirit ? PlayerSpirit->GetAltitude() : -1.f), TEXT("Aralez"));
	}
	if (State == EAralezState::End) TickEndCamera(FApp::GetDeltaTime());
	switch (State)
	{
	case EAralezState::Intro:
		IntroLeft -= Dt;
		if (IntroLeft <= 0.f)
		{
			State = EAralezState::Race;
			for (AAralezSpirit* S : Racers) S->SetControlEnabled(true);
			TwFx::Sound2D(GetWorld(), TEXT("sfx_wave_start"), 0.8f);
		}
		break;
	case EAralezState::Race:
	{
		RaceTime += Dt;
		TimeLeft = FMath::Max(0.f, TimeLeft - Dt);
		TickHealing(Dt);
		if (State != EAralezState::Race) break;
		if (!bDuskWarned && TimeLeft < 60.f)
		{
			bDuskWarned = true;
			Announce(LOCTEXT("Dusk", "Արևը մայր է մտնում"), bAraOpen ? LOCTEXT("DuskA", "Շտապի՛ր Արայի մոտ") : LOCTEXT("DuskB", "Շամիրամն արդեն պատրաստում է իր խաբեությունը"));
		}
		if (TimeLeft <= 0.f) { bWon = false; EndRace(); }
		break;
	}
	default: break;
	}
}

// ================================================================== controller
AAralezController::AAralezController() { PrimaryActorTick.bTickEvenWhenPaused = true; }
AAralezGameMode* AAralezController::Mode() const { return GetWorld() ? GetWorld()->GetAuthGameMode<AAralezGameMode>() : nullptr; }
AAralezSpirit* AAralezController::Spirit() const { return Cast<AAralezSpirit>(GetPawn()); }

void AAralezController::SetupInputComponent()
{
	Super::SetupInputComponent();
	Context = NewObject<UInputMappingContext>(this, TEXT("IMC_Aralez"));
	auto Make = [this](const TCHAR* N, EInputActionValueType T) { UInputAction* A = NewObject<UInputAction>(this, N); A->ValueType = T; return A; };
	IA_Move = Make(TEXT("IA_AMove"), EInputActionValueType::Axis2D);
	IA_Look = Make(TEXT("IA_ALook"), EInputActionValueType::Axis2D);
	IA_Up = Make(TEXT("IA_AUp"), EInputActionValueType::Axis1D);
	IA_Dash = Make(TEXT("IA_ADash"), EInputActionValueType::Boolean);
	IA_Howl = Make(TEXT("IA_AHowl"), EInputActionValueType::Boolean);
	IA_Pause = Make(TEXT("IA_APause"), EInputActionValueType::Boolean);
	IA_Pause->bTriggerWhenPaused = true;
	IA_FreeLook = Make(TEXT("IA_AFreeLook"), EInputActionValueType::Boolean);
	IA_Front = Make(TEXT("IA_AFront"), EInputActionValueType::Boolean);
	IA_Spin = Make(TEXT("IA_ASpin"), EInputActionValueType::Boolean);
	auto Neg = [this](FEnhancedActionKeyMapping& M) { M.Modifiers.Add(NewObject<UInputModifierNegate>(this)); };
	auto Swz = [this](FEnhancedActionKeyMapping& M) { M.Modifiers.Add(NewObject<UInputModifierSwizzleAxis>(this)); };
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Move, EKeys::W); Swz(M); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Move, EKeys::S); Swz(M); Neg(M); }
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Move, EKeys::A); Neg(M); }
	Context->MapKey(IA_Move, EKeys::D);
	Context->MapKey(IA_Move, EKeys::Gamepad_Left2D);
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Look, EKeys::Mouse2D); UInputModifierNegate* N = NewObject<UInputModifierNegate>(this); N->bX = false; N->bZ = false; M.Modifiers.Add(N); }
	Context->MapKey(IA_Up, EKeys::SpaceBar);
	{ FEnhancedActionKeyMapping& M = Context->MapKey(IA_Up, EKeys::LeftControl); Neg(M); }
	Context->MapKey(IA_Dash, EKeys::LeftShift);
	Context->MapKey(IA_Dash, EKeys::Gamepad_FaceButton_Bottom);
	Context->MapKey(IA_Howl, EKeys::Q);
	Context->MapKey(IA_Howl, EKeys::RightMouseButton);
	Context->MapKey(IA_Howl, EKeys::Gamepad_FaceButton_Top);
	Context->MapKey(IA_Pause, EKeys::Escape);
	Context->MapKey(IA_Pause, EKeys::P);
	Context->MapKey(IA_FreeLook, EKeys::LeftAlt);
	Context->MapKey(IA_FreeLook, EKeys::MiddleMouseButton);
	Context->MapKey(IA_FreeLook, EKeys::Gamepad_RightThumbstick);
	Context->MapKey(IA_Front, EKeys::F);
	Context->MapKey(IA_Front, EKeys::Gamepad_DPad_Down);
	Context->MapKey(IA_Spin, EKeys::R);
	Context->MapKey(IA_Spin, EKeys::Gamepad_DPad_Up);
	if (UEnhancedInputComponent* EI = Cast<UEnhancedInputComponent>(InputComponent))
	{
		EI->BindAction(IA_Move, ETriggerEvent::Triggered, this, &AAralezController::OnMove);
		EI->BindAction(IA_Move, ETriggerEvent::Completed, this, &AAralezController::OnMoveDone);
		EI->BindAction(IA_Look, ETriggerEvent::Triggered, this, &AAralezController::OnLook);
		EI->BindAction(IA_Up, ETriggerEvent::Triggered, this, &AAralezController::OnUp);
		EI->BindAction(IA_Up, ETriggerEvent::Completed, this, &AAralezController::OnUpDone);
		EI->BindAction(IA_Dash, ETriggerEvent::Started, this, &AAralezController::OnDash);
		EI->BindAction(IA_Howl, ETriggerEvent::Started, this, &AAralezController::OnHowl);
		EI->BindAction(IA_Pause, ETriggerEvent::Started, this, &AAralezController::OnPause);
		EI->BindAction(IA_FreeLook, ETriggerEvent::Started, this, &AAralezController::OnFreeLook);
		EI->BindAction(IA_FreeLook, ETriggerEvent::Completed, this, &AAralezController::OnFreeLookDone);
		EI->BindAction(IA_Front, ETriggerEvent::Started, this, &AAralezController::OnFrontView);
		EI->BindAction(IA_Spin, ETriggerEvent::Started, this, &AAralezController::OnSpin);
	}
}

void AAralezController::BeginPlay()
{
	Super::BeginPlay();
	if (ULocalPlayer* LP = GetLocalPlayer())
		if (UEnhancedInputLocalPlayerSubsystem* Sub = LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
			Sub->AddMappingContext(Context, 0);
	if (GEngine && GEngine->GameViewport && IsLocalController())
	{
		Hud = SNew(SAralezHud).Owner(this);
		GEngine->GameViewport->AddViewportWidgetContent(SNew(SWeakWidget).PossiblyNullContent(Hud.ToSharedRef()), 10);
	}
	const AAralezGameMode* GM = Mode();
	SetScreen(GM && GM->GetState() != EAralezState::Menu ? EAralezScreen::None : EAralezScreen::Menu);
}

void AAralezController::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Hud.IsValid() && GEngine && GEngine->GameViewport) GEngine->GameViewport->RemoveViewportWidgetContent(Hud.ToSharedRef());
	Hud.Reset();
	Super::EndPlay(Reason);
}

void AAralezController::SetScreen(EAralezScreen S)
{
	Screen = S;
	const bool bUi = S != EAralezScreen::None;
	bShowMouseCursor = bUi;
	if (bUi) { FInputModeGameAndUI M; M.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock); M.SetHideCursorDuringCapture(false); SetInputMode(M); }
	else { SetInputMode(FInputModeGameOnly()); FSlateApplication::Get().SetAllUserFocusToGameViewport(); }
	SetPause(S == EAralezScreen::Pause);
}

void AAralezController::OnMove(const FInputActionValue& V) { if (AAralezSpirit* S = Spirit()) S->InMove(V.Get<FVector2D>()); }
void AAralezController::OnMoveDone(const FInputActionValue& V) { if (AAralezSpirit* S = Spirit()) S->InMove(FVector2D::ZeroVector); }
void AAralezController::OnLook(const FInputActionValue& V) { if (Screen == EAralezScreen::None) if (AAralezSpirit* S = Spirit()) S->InLook(V.Get<FVector2D>() * 0.35f); }
void AAralezController::OnUp(const FInputActionValue& V) { if (AAralezSpirit* S = Spirit()) S->InUp(V.Get<float>()); }
void AAralezController::OnUpDone(const FInputActionValue& V) { if (AAralezSpirit* S = Spirit()) S->InUp(0.f); }
void AAralezController::OnDash(const FInputActionValue& V) { if (Screen == EAralezScreen::None) if (AAralezSpirit* S = Spirit()) S->InDash(); }
void AAralezController::OnHowl(const FInputActionValue& V) { if (Screen == EAralezScreen::None) if (AAralezSpirit* S = Spirit()) S->InHowl(); }
void AAralezController::OnFreeLook(const FInputActionValue& V) { if (Screen == EAralezScreen::None) if (AAralezSpirit* S = Spirit()) S->InFreeLook(true); }
void AAralezController::OnFreeLookDone(const FInputActionValue& V) { if (AAralezSpirit* S = Spirit()) S->InFreeLook(false); }
void AAralezController::OnFrontView(const FInputActionValue& V) { if (Screen == EAralezScreen::None) if (AAralezSpirit* S = Spirit()) S->InFrontView(); }
void AAralezController::OnSpin(const FInputActionValue& V) { if (Screen == EAralezScreen::None) if (AAralezSpirit* S = Spirit()) S->InSpin(); }
void AAralezController::OnPause(const FInputActionValue& V)
{
	const AAralezGameMode* GM = Mode();
	if (Screen == EAralezScreen::Pause) SetScreen(EAralezScreen::None);
	else if (Screen == EAralezScreen::None && GM && GM->GetState() == EAralezState::Race) SetScreen(EAralezScreen::Pause);
}

// ================================================================== HUD
static const FSlateBrush* AWB() { return FCoreStyle::Get().GetBrush("WhiteBrush"); }

EVisibility SAralezHud::VisFor(uint8 S) const
{
	const AAralezController* PC = Owner.Get();
	return PC && (uint8)PC->GetScreen() == S ? EVisibility::Visible : EVisibility::Collapsed;
}

void SAralezHud::Construct(const FArguments& Args)
{
	Owner = Args._Owner;
	TWeakObjectPtr<AAralezController> O = Owner;
	auto Mode = [O]() { return O.IsValid() ? O->Mode() : nullptr; };

	TSharedRef<SWidget> Menu =
		SNew(SBorder).BorderImage(AWB()).BorderBackgroundColor(FLinearColor(0.f, 0.01f, 0.03f, 0.6f)).Padding(FMargin(90, 50)).HAlign(HAlign_Left)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().FillHeight(1.f)[ SNew(SSpacer) ]
			+ SVerticalBox::Slot().AutoHeight()[ SNew(STextBlock).Text(LOCTEXT("Ch", "ԳԼՈՒԽ III · ԹՌԻՉՔ ԴԵՊԻ ԴԻՑԱԲԱՆՈՒԹՅԱՆ ԽՈՐՔԵՐԸ")).Font(TwAssets::Font(16.f, false, true)).ColorAndOpacity(FLinearColor(1, 1, 1, 0.6f)) ]
			+ SVerticalBox::Slot().AutoHeight()
			[
				Title(LOCTEXT("T", "ԱՐԱԼԵԶ"), LOCTEXT("S", "Ա Ր Ա Յ Ի   Դ Ա Շ Տ Ը"),
					LOCTEXT("B", "Արա Գեղեցիկը մերժեց Շամիրամին և ընկավ նրա զորքի դեմ մարտում։ Մայրամուտին երկնքից իջնում են Արալեզները՝ թևավոր շնանման աստվածները, որոնք լիզելով բուժում են զոհվածների վերքերը։ Իջի՛ր ամպերից, գտի՛ր ընկած քաջերին և կենդանացրո՛ւ նրանց, իսկ հետո՝ հենց Արային, մինչև արևը մայր մտնի։ Թե չհասցնես, Շամիրամը կխաբի ժողովրդին։"),
					FLinearColor(0.65f, 0.92f, 1.f))
			]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Play", "ԻՋՆԵԼ ԴԱՇՏ"), [Mode]() { if (AAralezGameMode* GM = Mode()) GM->StartRace(); }, true) ]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 10)
			[
				SNew(SBox).WidthOverride(560.f)
				[
					SNew(STextBlock).AutoWrapText(true).Font(TwAssets::Font(16.f, false, false)).ColorAndOpacity(Cream)
					.Text(LOCTEXT("Ctl", "Մկնիկ՝ ուղղություն · WASD՝ թռիչք · Space/Ctrl՝ վեր/վար · Shift՝ պոռթկում · Q՝ ոռնոց (հետ է մղում Շամիրամի նիզակավորներին) · Alt+մկնիկ՝ 360° տեսախցիկ · F՝ դիմացից · R՝ պտույտ · Բուժելու համար իջի՛ր քաջի մոտ և դանդաղի՛ր · Esc՝ դադար"))
				]
			]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Hub", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) UGameplayStatics::OpenLevel(O.Get(), TEXT("/Game/Twilight/Maps/L_Menu")); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Quit", "ԵԼՔ"), [O]() { if (O.IsValid()) UKismetSystemLibrary::QuitGame(O.Get(), O.Get(), EQuitPreference::Quit, false); }) ]
			+ SVerticalBox::Slot().FillHeight(1.f)[ SNew(SSpacer) ]
		];

	TSharedRef<SWidget> Pause =
		SNew(SBorder).BorderImage(AWB()).BorderBackgroundColor(FLinearColor(0, 0, 0, 0.6f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 20)[ SNew(STextBlock).Text(LOCTEXT("P", "ԴԱԴԱՐ")).Font(TwAssets::Font(64.f, true, true)).ColorAndOpacity(Gold) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Res", "ՇԱՐՈՒՆԱԿԵԼ"), [O]() { if (O.IsValid()) O->SetScreen(EAralezScreen::None); }, true) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Rst", "ՍԿՍԵԼ ՆՈՐԻՑ"), [Mode, O]() { if (O.IsValid()) O->SetPause(false); if (AAralezGameMode* GM = Mode()) GM->Restart(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Hub2", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) { O->SetPause(false); UGameplayStatics::OpenLevel(O.Get(), TEXT("/Game/Twilight/Maps/L_Menu")); } }) ]
		];

	TSharedRef<SWidget> End =
		SNew(SBorder).BorderImage(AWB()).BorderBackgroundColor(FLinearColor(0, 0, 0, 0.45f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
			[
				SNew(STextBlock).Font(TwAssets::Font(64.f, true, true))
				.Text_Lambda([Mode]()
				{
					AAralezGameMode* GM = Mode();
					if (!GM) return FText::GetEmpty();
					return GM->DidPlayerWin() ? LOCTEXT("Win", "ԱՐԱՆ ՎԵՐԱԴԱՐՁԱՎ") : LOCTEXT("Lose", "ՇԱՄԻՐԱՄԻ ԽԱԲԵՈՒԹՅՈՒՆԸ");
				})
				.ColorAndOpacity_Lambda([Mode]()
				{
					AAralezGameMode* GM = Mode();
					return FSlateColor(GM && GM->DidPlayerWin() ? Gold : Blood);
				})
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 10, 0, 24)
			[
				SNew(SBox).WidthOverride(900.f)
				[
					SNew(STextBlock).Font(TwAssets::Font(22.f, false, false)).ColorAndOpacity(Cream).Justification(ETextJustify::Center).AutoWrapText(true)
					.Text_Lambda([Mode]()
					{
						AAralezGameMode* GM = Mode();
						if (!GM) return FText::GetEmpty();
						const FText Story = GM->DidPlayerWin()
							? LOCTEXT("WinStory", "Արալեզները լիզեցին թագավորի վերքերը, և Արա Գեղեցիկը բացեց աչքերը։ Շամիրամի զորքը նահանջեց։")
							: LOCTEXT("LoseStory", "Արևը մայր մտավ։ Շամիրամը Արայի հանդերձը հագցրեց իր սիրեկաններից մեկին և հայտարարեց, թե Արալեզները կենդանացրել են թագավորին։");
						return FText::Format(LOCTEXT("EndStats", "{0}\n\nԿենդանացած քաջեր՝ {1} · Քո ձեռքով՝ {2}"), Story, FText::AsNumber(GM->GetRevived()), FText::AsNumber(GM->GetPlayerRevived()));
					})
				]
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(8, 0)[ Button(LOCTEXT("Again", "ԿՐԿԻՆ"), [Mode]() { if (AAralezGameMode* GM = Mode()) GM->Restart(); }, true, 300.f) ]
				+ SHorizontalBox::Slot().AutoWidth().Padding(8, 0)[ Button(LOCTEXT("Hub3", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) UGameplayStatics::OpenLevel(O.Get(), TEXT("/Game/Twilight/Maps/L_Menu")); }, false, 300.f) ]
			]
		];

	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SAralezHud::VisFor, (uint8)EAralezScreen::Menu)[ Menu ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SAralezHud::VisFor, (uint8)EAralezScreen::Pause)[ Pause ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SAralezHud::VisFor, (uint8)EAralezScreen::End)[ End ] ]
	];
}

int32 SAralezHud::OnPaint(const FPaintArgs& Args, const FGeometry& Geo, const FSlateRect& Cull, FSlateWindowElementList& Out, int32 L, const FWidgetStyle& Style, bool bParentEnabled) const
{
	AAralezController* PC = Owner.Get();
	AAralezGameMode* GM = PC ? PC->Mode() : nullptr;
	if (GM && PC->GetScreen() != EAralezScreen::Menu && PC->GetScreen() != EAralezScreen::End && GM->GetState() != EAralezState::Menu)
	{
		const FVector2D Size = FVector2D(Geo.GetLocalSize());
		const float S = Size.Y / 1080.f;
		const FVector2D C = Size * 0.5f;
		AAralezSpirit* Me = GM->GetPlayerSpirit();
		const int32 Secs = FMath::CeilToInt(GM->GetTimeLeft());
		const float Now = PC->GetWorld()->GetRealTimeSeconds();
		Text(Out, L + 4, Geo, FVector2D(C.X, 22 * S), FText::FromString(FString::Printf(TEXT("%02d:%02d"), Secs / 60, Secs % 60)), TwAssets::Font(34 * S, false, true), Secs < 45 ? Blood : Cream, 0.5f);
		Text(Out, L + 4, Geo, FVector2D(C.X, 70 * S), LOCTEXT("Sunset", "ՄԻՆՉԵՎ ՄԱՅՐԱՄՈՒՏ"), TwAssets::Font(15 * S, false, true), FLinearColor(1.f, 0.8f, 0.6f, 0.8f), 0.5f);

		// revived warriors and Ara
		{
			const FVector2D P(40 * S, 40 * S);
			Text(Out, L + 4, Geo, P, FText::Format(LOCTEXT("Rev", "Կենդանացած քաջեր՝ {0} / {1}"), FText::AsNumber(GM->GetRevived()), FText::AsNumber(GM->GetNeed())), TwAssets::Font(22 * S, false, true), Gold);
			Bar(Out, L + 4, Geo, P + FVector2D(0, 36 * S), FVector2D(300 * S, 7 * S), (float)GM->GetRevived() / FMath::Max(1, GM->GetNeed()), Gold, FLinearColor(1, 1, 1, 0.6f));
			const FText AraT = GM->IsAraOpen() ? LOCTEXT("AraO", "Արան սպասում է քեզ դաշտի կենտրոնում") : LOCTEXT("AraL", "Արան անշարժ է. նախ ոտքի կանգնեցրո՛ւ քաջերին");
			Text(Out, L + 4, Geo, P + FVector2D(0, 52 * S), AraT, TwAssets::Font(16 * S, false, true), GM->IsAraOpen() ? FLinearColor(1.f, 0.85f, 0.5f, 0.6f + 0.4f * FMath::Sin(Now * 4.f)) : FLinearColor(1, 1, 1, 0.7f));
			for (int32 i = 0; i < GM->GetRacers().Num(); ++i)
			{
				const AAralezSpirit* R = GM->GetRacers()[i];
				if (R == Me) continue;
				Text(Out, L + 4, Geo, P + FVector2D(0, (90 + i * 24) * S), FText::Format(LOCTEXT("Sister", "{0}՝ օգնում է"), R->GetRacerName()), TwAssets::Font(14 * S, false, false), R->GetColor());
			}
		}
		// world markers: the nearest fallen warrior and, once he can be raised, Ara
		if (Me)
		{
			int32 VX = 0, VY = 0;
			PC->GetViewportSize(VX, VY);
			auto Mark = [&](const FVector& W, const FText& Label, const FLinearColor& Col)
			{
				FVector2D Scr;
				if (VX <= 0 || !PC->ProjectWorldLocationToScreen(W, Scr, true)) return;
				FVector2D Lp = Scr * (Size.X / VX);
				Lp.X = FMath::Clamp(Lp.X, 60 * S, Size.X - 60 * S);
				Lp.Y = FMath::Clamp(Lp.Y, 120 * S, Size.Y - 160 * S);
				const float Pulse = 0.7f + 0.3f * FMath::Sin(Now * 5.f);
				Box(Out, L + 5, Geo, Lp - FVector2D(7, 7) * S, FVector2D(14, 14) * S, FLinearColor(Col.R, Col.G, Col.B, Pulse));
				const int32 M = FMath::RoundToInt(FVector::Dist(W, Me->GetActorLocation()) / 100.f);
				Text(Out, L + 5, Geo, Lp + FVector2D(0, 12 * S), FText::Format(LOCTEXT("MarkFmt", "{0} · {1} մ"), Label, FText::AsNumber(M)), TwAssets::Font(14 * S, false, true), Col, 0.5f);
			};
			if (AFallenWarrior* W = GM->NearestFallen(Me->GetActorLocation()))
				if (!W->IsAra()) Mark(W->GetActorLocation() + FVector(0, 0, 120.f), LOCTEXT("MkW", "Վիրավոր"), FLinearColor(0.7f, 0.92f, 1.f));
			if (GM->IsAraOpen() && GM->GetAra()) Mark(GM->GetAra()->GetActorLocation() + FVector(0, 0, 160.f), LOCTEXT("MkA", "Արա"), Gold);

			// healing progress under the crosshair, or a hint to come down
			if (AFallenWarrior* Pat = GM->GetPlayerPatient())
			{
				Text(Out, L + 6, Geo, FVector2D(C.X, C.Y + 110 * S), Pat->IsAra() ? LOCTEXT("HealAra", "Արալեզները լիզում են Արայի վերքերը…") : LOCTEXT("Heal", "Լիզում ես վերքերը…"), TwAssets::Font(22 * S, false, true), Gold, 0.5f);
				Bar(Out, L + 6, Geo, FVector2D(C.X - 160 * S, C.Y + 146 * S), FVector2D(320 * S, 8 * S), Pat->GetProgress(), Gold, FLinearColor(1, 1, 1, 0.7f));
			}
			else if (AFallenWarrior* Near = GM->NearestFallen(Me->GetActorLocation()))
			{
				if (FVector::Dist2D(Near->GetActorLocation(), Me->GetActorLocation()) < 1400.f)
					Text(Out, L + 6, Geo, FVector2D(C.X, C.Y + 110 * S), Me->GetAltitude() > AAralezGameMode::HealAltitude ? LOCTEXT("Lower", "Իջի՛ր ավելի ցածր (Ctrl)") : LOCTEXT("Slow", "Դանդաղի՛ր և մոտեցի՛ր նրան"), TwAssets::Font(20 * S, false, true), Cream, 0.5f);
			}

			const FVector2D V0(48 * S, Size.Y - 110 * S);
			Text(Out, L + 4, Geo, V0 + FVector2D(0, -26 * S), LOCTEXT("Dash", "ՊՈՌԹԿՈՒՄ · Shift"), TwAssets::Font(13 * S, false, true), FLinearColor(1, 1, 1, 0.75f));
			Bar(Out, L + 4, Geo, V0, FVector2D(220 * S, 8 * S), 1.f - Me->GetDashCooldown() / 2.5f, FLinearColor(0.5f, 0.85f, 1.f), FLinearColor(1, 1, 1, 0.7f));
			Text(Out, L + 4, Geo, V0 + FVector2D(0, 22 * S), LOCTEXT("Howl", "ՈՌՆՈՑ · Q"), TwAssets::Font(13 * S, false, true), FLinearColor(1, 1, 1, 0.75f));
			Bar(Out, L + 4, Geo, V0 + FVector2D(0, 48 * S), FVector2D(220 * S, 8 * S), 1.f - Me->GetHowlCooldown() / 12.f, FLinearColor(1.f, 0.8f, 0.4f), FLinearColor(1, 1, 1, 0.7f));
			Text(Out, L + 4, Geo, FVector2D(Size.X - 48 * S, Size.Y - 120 * S), FText::Format(LOCTEXT("Mine", "Քո ձեռքով՝ {0}"), FText::AsNumber(GM->GetPlayerRevived())), TwAssets::Font(26 * S, true, true), Gold, 1.f);
			if (Me->GetStun() > 0.f) Text(Out, L + 6, Geo, FVector2D(C.X, C.Y + 180 * S), LOCTEXT("Stun", "Նիզակը խոցեց քեզ"), TwAssets::Font(24 * S, false, true), Blood, 0.5f);

			// red pulse when a spearman is close and you fly low
			float Near = TNumericLimits<float>::Max();
			for (TActorIterator<AShamiramSoldier> It(PC->GetWorld()); It; ++It) Near = FMath::Min(Near, (float)FVector::Dist2D(It->GetActorLocation(), Me->GetActorLocation()));
			if (Near < 1500.f && Me->GetAltitude() < 800.f)
				EdgeGlow(Out, L + 3, Geo, Size, FLinearColor(Blood.R, Blood.G, Blood.B, 0.35f * (1.f - Near / 1500.f) * (0.6f + 0.4f * FMath::Sin(Now * 10.f))), 180 * S);
		}
		if (GM->GetState() == EAralezState::Intro)
			Text(Out, L + 8, Geo, FVector2D(C.X, C.Y + 40 * S), FText::AsNumber(FMath::Max(1, FMath::CeilToInt(GM->GetIntroLeft()))), TwAssets::Font(110 * S, true, true), Gold, 0.5f);
		FText At, As; float Age = 0.f;
		if (GM->GetAnnouncement(At, As, Age))
		{
			const float A = FMath::Clamp(Age / 0.2f, 0.f, 1.f) * FMath::Clamp((3.f - Age) / 0.5f, 0.f, 1.f);
			const FSlateFontInfo TF = TwAssets::Font(52 * S, true, true);
			const float TitleH = FSlateApplication::Get().GetRenderer()->GetFontMeasureService()->Measure(At, TF).Y;
			Box(Out, L + 7, Geo, FVector2D(0, C.Y - 300 * S), FVector2D(Size.X, TitleH + 70 * S), FLinearColor(0, 0, 0, 0.35f * A));
			Text(Out, L + 8, Geo, FVector2D(C.X, C.Y - 288 * S), At, TF, FLinearColor(0.75f, 0.95f, 1.f, A), 0.5f);
			if (!As.IsEmpty()) Text(Out, L + 8, Geo, FVector2D(C.X, C.Y - 288 * S + TitleH + 2 * S), As, TwAssets::Font(22 * S, false, false), FLinearColor(Cream.R, Cream.G, Cream.B, A * 0.9f), 0.5f);
		}
	}
	return SCompoundWidget::OnPaint(Args, Geo, Cull, Out, L + 40, Style, bParentEnabled);
}

#undef LOCTEXT_NAMESPACE
