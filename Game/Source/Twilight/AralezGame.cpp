#include "AralezGame.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "TwUi.h"
#include "AralezWorld.h"
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
	World = GetWorld()->SpawnActor<AAralezWorld>(FVector::ZeroVector, FRotator::ZeroRotator, P);
	Super::StartPlay();
	if (UGameplayStatics::HasOption(OptionsString, TEXT("TwStart"))) StartRace();
}

void AAralezGameMode::RestartPlayer(AController* NewPlayer)
{
	// player + three rival spirits at the cave mouth
	const struct { FLinearColor Col; const TCHAR* Name; } Rivals[3] = {
		{ FLinearColor(1.f, 0.75f, 0.3f), TEXT("Ոսկեթև") },
		{ FLinearColor(0.75f, 0.45f, 1.f), TEXT("Լուսնակ") },
		{ FLinearColor(0.45f, 1.f, 0.55f), TEXT("Զմրուխտ") },
	};
	const FVector Start = AAralezWorld::PathPoint(0.005f);
	const FVector Fwd = AAralezWorld::PathTangent(0.005f);
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
	auto Spawn = [&](const FVector& Off, bool bBot, const FLinearColor& C, const FText& Name, int32 Skill) -> AAralezSpirit*
	{
		FActorSpawnParameters S;
		S.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		S.bDeferConstruction = true;
		const FTransform T(Fwd.Rotation(), Start + Off);
		AAralezSpirit* A = GetWorld()->SpawnActor<AAralezSpirit>(AAralezSpirit::StaticClass(), T, S);
		if (!A) return nullptr;
		A->Setup(bBot, C, Name, Skill);
		UGameplayStatics::FinishSpawningActor(A, T);
		A->SetControlEnabled(false);
		RacerRefs.Add(A);
		Racers.Add(A);
		return A;
	};
	PlayerSpirit = Spawn(FVector::ZeroVector, false, FLinearColor(0.55f, 0.9f, 1.f), LOCTEXT("You", "Դու"), 1);
	for (int32 i = 0; i < 3; ++i) Spawn(Right * (i - 1) * 350.f + FVector(0, 0, 250.f), true, Rivals[i].Col, FText::FromString(Rivals[i].Name), i);
	if (PlayerSpirit && NewPlayer)
	{
		NewPlayer->Possess(PlayerSpirit);
		NewPlayer->SetControlRotation(Fwd.Rotation());
	}
}

void AAralezGameMode::SpawnLightsAndWraiths()
{
	FRandomStream R(321);
	FActorSpawnParameters S;
	S.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	// clusters of lights along the whole descent
	for (int32 c = 0; c < 44; ++c)
	{
		const float T = 0.03f + 0.95f * c / 44.f + R.FRandRange(-0.006f, 0.006f);
		const FVector P = AAralezWorld::PathPoint(T);
		const FVector Fwd = AAralezWorld::PathTangent(T);
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd).GetSafeNormal();
		const FVector Up = FVector::CrossProduct(Fwd, Right).GetSafeNormal();
		const float Rad = AAralezWorld::TunnelRadius(T) * 0.55f;
		const float A = R.FRandRange(0.f, 2.f * PI);
		const FVector Center = P + (Right * FMath::Cos(A) + Up * FMath::Sin(A)) * Rad * R.FRandRange(0.f, 1.f);
		const int32 N = R.RandRange(3, 6);
		for (int32 i = 0; i < N; ++i) GetWorld()->SpawnActor<ASoulLight>(Center + R.VRand() * 260.f + Fwd * i * 160.f, FRotator::ZeroRotator, S);
	}
	// Shamiram's shadows, more of them deeper down
	const float WraithT[7] = { 0.18f, 0.3f, 0.45f, 0.56f, 0.66f, 0.78f, 0.9f };
	for (float T : WraithT)
	{
		if (AShadowWraith* W = GetWorld()->SpawnActor<AShadowWraith>(AAralezWorld::PathPoint(T), FRotator::ZeroRotator, S)) W->SetPatrol(T);
	}
}

void AAralezGameMode::Announce(const FText& T, const FText& S) { AnnTitle = T; AnnSub = S; AnnTime = GetWorld()->GetRealTimeSeconds(); }
bool AAralezGameMode::GetAnnouncement(FText& Title, FText& Sub, float& Age) const
{
	Age = GetWorld()->GetRealTimeSeconds() - AnnTime; Title = AnnTitle; Sub = AnnSub; return Age < 3.f;
}

void AAralezGameMode::StartRace()
{
	SpawnLightsAndWraiths();
	State = EAralezState::Intro;
	IntroLeft = 3.f;
	TimeLeft = RaceLength;
	if (World) World->PlayMusic(TEXT("music_battle"));
	Announce(LOCTEXT("Intro", "Իջի՛ր խորքերը"), LOCTEXT("IntroSub", "Հավաքի՛ր Արայի հոգու լույսերը և հասի՛ր անդունդի դարպասին"));
	if (AAralezController* PC = Cast<AAralezController>(UGameplayStatics::GetPlayerController(this, 0))) PC->SetScreen(EAralezScreen::None);
}

void AAralezGameMode::Restart() { UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true, TEXT("TwStart=1")); }
void AAralezGameMode::ToMenu() { UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true); }

int32 AAralezGameMode::ScoreOf(const AAralezSpirit* S) const
{
	if (!S) return 0;
	const int32* B = FinishBonus.Find(S);
	return S->GetLights() + (B ? *B : 0);
}

int32 AAralezGameMode::RankOf(const AAralezSpirit* S) const
{
	if (!S) return 4;
	int32 Rank = 1;
	const int32 Mine = ScoreOf(S);
	for (const AAralezSpirit* O : Racers)
	{
		if (O == S) continue;
		const int32 Their = ScoreOf(O);
		if (Their > Mine || (Their == Mine && O->GetProgress() > S->GetProgress())) ++Rank;
	}
	return Rank;
}

void AAralezGameMode::EndRace()
{
	if (State == EAralezState::End) return;
	State = EAralezState::End;
	for (AAralezSpirit* S : Racers) S->SetControlEnabled(false);
	const bool bWin = DidPlayerWin();
	if (World) World->PlayMusic(TEXT("music_menu"));
	TwFx::Sound2D(GetWorld(), bWin ? TEXT("sfx_victory") : TEXT("sfx_defeat"), 1.f);
	if (bWin && World)
	{
		// Ara returns: a pillar of light from the gate
		const FVector G = World->GetGate();
		for (int32 i = 0; i < 8; ++i) TwFx::Burst(GetWorld(), TwFx::EFx::Nova, G + FVector(0, 0, i * 900.f), 4.f);
		TwFx::LightFlash(GetWorld(), G, FLinearColor(1.f, 0.85f, 0.55f), 600000.f, 20000.f, 4.f);
	}
	if (AAralezController* PC = Cast<AAralezController>(UGameplayStatics::GetPlayerController(this, 0))) PC->SetScreen(EAralezScreen::End);
}

void AAralezGameMode::Tick(float Dt)
{
	Super::Tick(Dt);
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
		// zone announcements follow the player
		if (PlayerSpirit)
		{
			const int32 Z = AAralezWorld::ZoneAt(PlayerSpirit->GetProgress());
			if (Z != Zone)
			{
				Zone = Z;
				if (Z == 1) Announce(LOCTEXT("Z1", "Ստորերկրյա գետ"), LOCTEXT("Z1s", "Ջրերի խորքում ստվերները ավելի շատ են"));
				if (Z == 2) Announce(LOCTEXT("Z2", "Անդունդ"), LOCTEXT("Z2s", "Դարպասը մոտ է. Արան սպասում է"));
			}
		}
		// finishing at the gate
		for (AAralezSpirit* S : Racers)
		{
			if (S->IsFinished()) continue;
			if (S->GetProgress() > 0.985f)
			{
				S->MarkFinished(RaceTime);
				const int32 Bonus[4] = { 6, 4, 2, 1 };
				FinishBonus.Add(S, Bonus[FMath::Clamp(Finished, 0, 3)]);
				++Finished;
				S->SetControlEnabled(false);
				if (S == PlayerSpirit) Announce(FText::Format(LOCTEXT("Fin", "Դարպաս՝ {0}-րդ"), FText::AsNumber(Finished)), FText::Format(LOCTEXT("FinB", "+{0} բոնուս"), FText::AsNumber(Bonus[FMath::Clamp(Finished - 1, 0, 3)])));
			}
		}
		if (TimeLeft <= 0.f || (PlayerSpirit && PlayerSpirit->IsFinished()) || Finished >= Racers.Num()) EndRace();
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
				Title(LOCTEXT("T", "ԱՐԱԼԵԶ"), LOCTEXT("S", "Հ Ո Գ Ո Ւ   Վ Ե Ր Ա Դ Ա Ր Ձ Ը"),
					LOCTEXT("B", "Արա Գեղեցիկն ընկավ Շամիրամի դեմ մարտում։ Թագուհին կանչեց Արալեզներին՝ շնանման ոգիներին, որոնք լիզելով կենդանացնում են զոհվածներին։ Իջի՛ր քարանձավների, ստորերկրյա գետի և անդունդի միջով, հավաքի՛ր Արայի հոգու լույսերը և հասի՛ր դարպասին ավելի շուտ, քան մյուս Արալեզները։"),
					FLinearColor(0.65f, 0.92f, 1.f))
			]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Play", "ՍԿՍԵԼ ՄՐՑԱՎԱԶՔԸ"), [Mode]() { if (AAralezGameMode* GM = Mode()) GM->StartRace(); }, true) ]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 10)
			[
				SNew(SBox).WidthOverride(540.f)
				[
					SNew(STextBlock).AutoWrapText(true).Font(TwAssets::Font(16.f, false, false)).ColorAndOpacity(Cream)
					.Text(LOCTEXT("Ctl", "Մկնիկ՝ ուղղություն · WASD՝ թռիչք · Space/Ctrl՝ վեր/վար · Shift՝ պոռթկում · Q՝ ոռնոց (վանում է ստվերներին և ձգում լույսերը) · Esc՝ դադար"))
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
				SNew(STextBlock).Font(TwAssets::Font(80.f, true, true))
				.Text_Lambda([Mode]() { AAralezGameMode* GM = Mode(); return GM && GM->DidPlayerWin() ? LOCTEXT("Win", "ԱՐԱՆ ՎԵՐԱԴԱՐՁԱՎ") : LOCTEXT("Lose", "ՍՏՎԵՐՆԵՐԸ ՀԱՂԹԵՑԻՆ"); })
				.ColorAndOpacity_Lambda([Mode]() { AAralezGameMode* GM = Mode(); return FSlateColor(GM && GM->DidPlayerWin() ? Gold : Blood); })
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 10, 0, 24)
			[
				SNew(STextBlock).Font(TwAssets::Font(22.f, false, false)).ColorAndOpacity(Cream).Justification(ETextJustify::Center)
				.Text_Lambda([Mode]()
				{
					AAralezGameMode* GM = Mode();
					if (!GM) return FText::GetEmpty();
					TArray<AAralezSpirit*> R = GM->GetRacers();
					R.Sort([GM](const AAralezSpirit& A, const AAralezSpirit& B) { return GM->RankOf(&A) < GM->RankOf(&B); });
					FString S;
					for (int32 i = 0; i < R.Num(); ++i)
						S += FString::Printf(TEXT("%d. %s — %d\n"), i + 1, *R[i]->GetRacerName().ToString(), GM->ScoreOf(R[i]));
					return FText::FromString(S);
				})
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
	if (GM && PC->GetScreen() != EAralezScreen::Menu && GM->GetState() != EAralezState::Menu)
	{
		const FVector2D Size = FVector2D(Geo.GetLocalSize());
		const float S = Size.Y / 1080.f;
		const FVector2D C = Size * 0.5f;
		AAralezSpirit* Me = GM->GetPlayerSpirit();
		const int32 Secs = FMath::CeilToInt(GM->GetTimeLeft());
		Text(Out, L + 4, Geo, FVector2D(C.X, 22 * S), FText::FromString(FString::Printf(TEXT("%02d:%02d"), Secs / 60, Secs % 60)), TwAssets::Font(34 * S, false, true), Secs < 45 ? Blood : Cream, 0.5f);
		const FText ZoneName = GM->GetZone() == 0 ? LOCTEXT("Z0n", "ՔԱՐԱՆՁԱՎ") : (GM->GetZone() == 1 ? LOCTEXT("Z1n", "ՍՏՈՐԵՐԿՐՅԱ ԳԵՏ") : LOCTEXT("Z2n", "ԱՆԴՈՒՆԴ"));
		Text(Out, L + 4, Geo, FVector2D(C.X, 70 * S), ZoneName, TwAssets::Font(16 * S, false, true), FLinearColor(0.7f, 0.9f, 1.f, 0.85f), 0.5f);

		// standings + depth bars
		TArray<AAralezSpirit*> R = GM->GetRacers();
		R.Sort([GM](const AAralezSpirit& A, const AAralezSpirit& B) { return GM->RankOf(&A) < GM->RankOf(&B); });
		for (int32 i = 0; i < R.Num(); ++i)
		{
			const FVector2D P(40 * S, (40 + i * 46) * S);
			const FLinearColor Col = R[i]->GetColor();
			Text(Out, L + 4, Geo, P, FText::FromString(FString::Printf(TEXT("%d. %s  ✦ %d"), i + 1, *R[i]->GetRacerName().ToString(), GM->ScoreOf(R[i]))), TwAssets::Font((R[i] == Me ? 20 : 17) * S, false, true), Col);
			Bar(Out, L + 4, Geo, P + FVector2D(0, 30 * S), FVector2D(220 * S, 5 * S), R[i]->GetProgress(), Col, FLinearColor(1, 1, 1, 0.6f));
		}
		if (Me)
		{
			const FVector2D V0(48 * S, Size.Y - 110 * S);
			Text(Out, L + 4, Geo, V0 + FVector2D(0, -26 * S), LOCTEXT("Dash", "ՊՈՌԹԿՈՒՄ · Shift"), TwAssets::Font(13 * S, false, true), FLinearColor(1, 1, 1, 0.75f));
			Bar(Out, L + 4, Geo, V0, FVector2D(220 * S, 8 * S), 1.f - Me->GetDashCooldown() / 2.5f, FLinearColor(0.5f, 0.85f, 1.f), FLinearColor(1, 1, 1, 0.7f));
			Text(Out, L + 4, Geo, V0 + FVector2D(0, 22 * S), LOCTEXT("Howl", "ՈՌՆՈՑ · Q"), TwAssets::Font(13 * S, false, true), FLinearColor(1, 1, 1, 0.75f));
			Bar(Out, L + 4, Geo, V0 + FVector2D(0, 48 * S), FVector2D(220 * S, 8 * S), 1.f - Me->GetHowlCooldown() / 12.f, FLinearColor(1.f, 0.8f, 0.4f), FLinearColor(1, 1, 1, 0.7f));
			Text(Out, L + 4, Geo, FVector2D(Size.X - 48 * S, Size.Y - 120 * S), FText::Format(LOCTEXT("Mine", "Արայի լույսեր՝ {0}"), FText::AsNumber(Me->GetLights())), TwAssets::Font(28 * S, true, true), Gold, 1.f);
			if (Me->GetStun() > 0.f) Text(Out, L + 6, Geo, FVector2D(C.X, C.Y + 120 * S), LOCTEXT("Stun", "Ստվերը խլեց լույսերդ"), TwAssets::Font(24 * S, false, true), Blood, 0.5f);
		}
		if (GM->GetState() == EAralezState::Intro)
			Text(Out, L + 8, Geo, FVector2D(C.X, C.Y - 160 * S), FText::AsNumber(FMath::Max(1, FMath::CeilToInt(GM->GetIntroLeft()))), TwAssets::Font(110 * S, true, true), Gold, 0.5f);
		FText At, As; float Age = 0.f;
		if (GM->GetAnnouncement(At, As, Age))
		{
			const float A = FMath::Clamp(Age / 0.2f, 0.f, 1.f) * FMath::Clamp((3.f - Age) / 0.5f, 0.f, 1.f);
			Text(Out, L + 8, Geo, FVector2D(C.X, C.Y - 280 * S), At, TwAssets::Font(52 * S, true, true), FLinearColor(0.75f, 0.95f, 1.f, A), 0.5f);
			if (!As.IsEmpty()) Text(Out, L + 8, Geo, FVector2D(C.X, C.Y - 205 * S), As, TwAssets::Font(21 * S, false, false), FLinearColor(Cream.R, Cream.G, Cream.B, A * 0.9f), 0.5f);
		}
	}
	return SCompoundWidget::OnPaint(Args, Geo, Cull, Out, L + 40, Style, bParentEnabled);
}

#undef LOCTEXT_NAMESPACE
