#include "HaykGameMode.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwFx.h"
#include "HaykArcher.h"
#include "HaykArrow.h"
#include "HaykWorld.h"
#include "HaykPlayerController.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "Misc/App.h"

#define LOCTEXT_NAMESPACE "Hayk"

// ------------------------------------------------------------------ preview dots
AHaykPreview::AHaykPreview()
{
	Dots = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Dots"));
	RootComponent = Dots;
	Dots->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Dots->SetCastShadow(false);
	Dots->SetMobility(EComponentMobility::Movable);
}

void AHaykPreview::Show(const TArray<FVector>& Points)
{
	if (!bInit)
	{
		bInit = true;
		Dots->SetStaticMesh(TwAssets::Sphere());
		if (UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this))
		{
			M->SetVectorParameterValue(TEXT("Color"), FLinearColor(1.f, 0.85f, 0.5f));
			M->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
			M->SetScalarParameterValue(TEXT("Intensity"), 6.f);
			Dots->SetMaterial(0, M);
		}
	}
	SetActorHiddenInGame(false);
	TArray<FTransform> T;
	for (int32 i = 0; i < Points.Num(); ++i)
	{
		const float S = FMath::Lerp(0.07f, 0.025f, i / float(FMath::Max(1, Points.Num() - 1)));
		T.Add(FTransform(FRotator::ZeroRotator, Points[i], FVector(S)));
	}
	if (Dots->GetInstanceCount() != T.Num())
	{
		Dots->ClearInstances();
		Dots->AddInstances(T, false, true);
	}
	else
	{
		Dots->BatchUpdateInstancesTransforms(0, T, true, true, true);
	}
}

void AHaykPreview::Hide() { SetActorHiddenInGame(true); }

// ------------------------------------------------------------------ game mode
AHaykGameMode::AHaykGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	DefaultPawnClass = nullptr;
	PlayerControllerClass = AHaykPlayerController::StaticClass();
	HUDClass = nullptr;
}

void AHaykGameMode::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage)
{
	Super::InitGame(MapName, Options, ErrorMessage);
	bNight = UGameplayStatics::GetIntOption(Options, TEXT("TwNight"), 0) != 0;
	Difficulty = FMath::Clamp(UGameplayStatics::GetIntOption(Options, TEXT("TwDiff"), 1), 0, 2);
}

void AHaykGameMode::StartPlay()
{
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	P.bDeferConstruction = true;
	World = GetWorld()->SpawnActor<AHaykWorld>(FVector::ZeroVector, FRotator::ZeroRotator, P);
	if (World) { World->SetNight(bNight); UGameplayStatics::FinishSpawningActor(World, FTransform::Identity); }

	auto SpawnArcher = [this](bool bIsBel) -> AHaykArcher*
	{
		const float X = bIsBel ? AHaykWorld::BelX : AHaykWorld::HaykX;
		const FVector Loc(X, 0.f, AHaykWorld::TerrainZ(X, 0.f) + 2.f);
		FActorSpawnParameters S;
		S.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		S.bDeferConstruction = true;
		AHaykArcher* A = GetWorld()->SpawnActor<AHaykArcher>(Loc, FRotator(0.f, bIsBel ? 180.f : 0.f, 0.f), S);
		if (A)
		{
			A->Setup(bIsBel, 100.f);
			UGameplayStatics::FinishSpawningActor(A, FTransform(FRotator(0.f, bIsBel ? 180.f : 0.f, 0.f), Loc));
		}
		return A;
	};
	Hayk = SpawnArcher(false);
	Bel = SpawnArcher(true);

	FActorSpawnParameters C;
	C.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	Cam = GetWorld()->SpawnActor<ACameraActor>(FVector(-6000.f, -3000.f, 1200.f), FRotator(-8.f, 30.f, 0.f), C);
	if (Cam)
	{
		Cam->GetCameraComponent()->SetFieldOfView(72.f);
		Cam->GetCameraComponent()->bConstrainAspectRatio = false;
	}
	Preview = GetWorld()->SpawnActor<AHaykPreview>(FVector::ZeroVector, FRotator::ZeroRotator, C);
	if (Preview) Preview->Hide();

	Super::StartPlay();

	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		PC->SetViewTarget(Cam);
	}
	if (UGameplayStatics::HasOption(OptionsString, TEXT("TwStart")))
	{
		StartDuel(UGameplayStatics::GetIntOption(OptionsString, TEXT("TwStart"), 1) == 1);
	}
}

void AHaykGameMode::Announce(const FText& T, const FText& S)
{
	AnnTitle = T; AnnSub = S; AnnTime = GetWorld()->GetRealTimeSeconds();
}

bool AHaykGameMode::GetAnnouncement(FText& Title, FText& Sub, float& Age) const
{
	Age = GetWorld()->GetRealTimeSeconds() - AnnTime;
	Title = AnnTitle; Sub = AnnSub;
	return Age < 2.8f;
}

void AHaykGameMode::StartDuel(bool bInVsBot)
{
	bVsBot = bInVsBot;
	const float BelHp = bVsBot ? (Difficulty == 0 ? 110.f : (Difficulty == 2 ? 160.f : 140.f)) : 100.f;
	if (Hayk) Hayk->Setup(false, 100.f);
	if (Bel) Bel->Setup(true, BelHp);
	Turn = 0;
	SpecialsHayk = SpecialsBel = 1;
	HitsHayk = HitsBel = HeadsHayk = HeadsBel = 0;
	StreakHayk = StreakBel = 0;
	BotMisses = 0;
	bBelTurn = true; // BeginTurn flips to Hayk first
	State = EHaykState::Intro;
	StateTime = 0.f;
	if (World) World->PlayMusic(TEXT("music_battle"));
	Announce(LOCTEXT("Intro", "Հայոց ձոր"), LOCTEXT("IntroSub", "Հայկը կանգնեց Բելի դեմ։ Մեկ նետ կարող է որոշել ազգի ճակատագիրը։"));
	if (AHaykPlayerController* PC = Cast<AHaykPlayerController>(UGameplayStatics::GetPlayerController(this, 0))) PC->OnDuelStarted();
}

void AHaykGameMode::Restart()
{
	UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 1.f);
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true,
		FString::Printf(TEXT("TwStart=%d?TwNight=%d?TwDiff=%d"), bVsBot ? 1 : 2, bNight ? 1 : 0, Difficulty));
}

void AHaykGameMode::ToMenu()
{
	UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 1.f);
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true, FString::Printf(TEXT("TwNight=%d?TwDiff=%d"), bNight ? 1 : 0, Difficulty));
}

void AHaykGameMode::ToggleNight()
{
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true, FString::Printf(TEXT("TwNight=%d?TwDiff=%d"), bNight ? 0 : 1, Difficulty));
}

float AHaykGameMode::BaseYawFor(AHaykArcher* A) const
{
	AHaykArcher* O = A == Hayk ? Bel : Hayk;
	if (!A || !O) return 0.f;
	return (O->GetActorLocation() - A->GetActorLocation()).Rotation().Yaw;
}

void AHaykGameMode::BeginTurn()
{
	bBelTurn = !bBelTurn;
	++Turn;
	State = EHaykState::Aim;
	StateTime = 0.f;
	TurnLeft = 25.f;
	Power = 0.f;
	bDrawing = false;
	bSpecialArmed = false;
	bBotSolved = false;
	BotTimer = 0.f;
	// new wind every turn: mostly sideways, sometimes along the valley
	const float Strength = FMath::FRandRange(0.f, Difficulty == 0 ? 3.f : 6.f);
	const float Dir = FMath::FRandRange(0.f, 360.f);
	Wind = FVector(FMath::Cos(FMath::DegreesToRadians(Dir)) * 0.5f, FMath::Sin(FMath::DegreesToRadians(Dir)), 0.f).GetSafeNormal() * Strength;
	AHaykArcher* S = Shooter();
	if (S) S->SetAim(BaseYawFor(S), 12.f);
	if (Bel && Hayk)
	{
		if (!bBelTurn) Bel->SetAim(BaseYawFor(Bel), 5.f); else Hayk->SetAim(BaseYawFor(Hayk), 5.f);
	}
	const FText Who = bBelTurn ? (bVsBot ? LOCTEXT("BelTurn", "Բելի հերթն է") : LOCTEXT("P2Turn", "Խաղացող 2 · Բել")) : (bVsBot ? LOCTEXT("YourTurn", "Քո հերթն է") : LOCTEXT("P1Turn", "Խաղացող 1 · Հայկ"));
	Announce(Who, FText::Format(LOCTEXT("WindSub", "Քամի՝ {0} մ/վ"), FText::AsNumber(FMath::RoundToInt(Wind.Size()))));
}

void AHaykGameMode::AimDelta(const FVector2D& D)
{
	if (State != EHaykState::Aim || !IsHumanTurn()) return;
	AHaykArcher* S = Shooter();
	if (!S) return;
	const float Base = BaseYawFor(S);
	float Yaw = S->GetAimYaw() + D.X;
	const float Rel = FMath::Clamp(FMath::FindDeltaAngleDegrees(Base, Yaw), -40.f, 40.f);
	S->SetAim(Base + Rel, S->GetAimPitch() + D.Y);
}

void AHaykGameMode::DrawStart()
{
	if (State != EHaykState::Aim || !IsHumanTurn()) return;
	bDrawing = true;
	Power = 0.f;
}

void AHaykGameMode::DrawRelease()
{
	if (State != EHaykState::Aim || !IsHumanTurn() || !bDrawing) return;
	bDrawing = false;
	if (Power < 0.12f) { Power = 0.f; if (Shooter()) Shooter()->SetDraw(0.f); return; }
	Shoot(Power);
}

void AHaykGameMode::ToggleSpecial()
{
	if (State != EHaykState::Aim || !IsHumanTurn()) return;
	const int32 Have = bBelTurn ? SpecialsBel : SpecialsHayk;
	if (!bSpecialArmed && Have <= 0) { TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_hover"), 0.6f, 0.6f); return; }
	bSpecialArmed = !bSpecialArmed;
	TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click"), 0.8f, bSpecialArmed ? 1.3f : 0.8f);
}

void AHaykGameMode::SteerArrow(const FVector2D& In)
{
	if (State == EHaykState::Flight && Arrow.IsValid() && Arrow->IsSpecial() && IsHumanTurn()) Arrow->Steer(In);
}

void AHaykGameMode::Shoot(float InPower)
{
	AHaykArcher* S = Shooter();
	if (!S) return;
	const FVector Start = S->GetArrowSpawn();
	const FVector Dir = FRotator(S->GetAimPitch(), S->GetAimYaw(), 0.f).Vector();
	S->Release();
	if (Preview) Preview->Hide();
	if (bSpecialArmed)
	{
		if (bBelTurn) --SpecialsBel; else --SpecialsHayk;
	}
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	P.Owner = S;
	AHaykArrow* A = GetWorld()->SpawnActor<AHaykArrow>(Start, Dir.Rotation(), P);
	if (A) A->Launch(S, Dir, InPower, Wind, bSpecialArmed);
	Arrow = A;
	State = EHaykState::Flight;
	StateTime = 0.f;
	bSlowMo = false;
	if (bSpecialArmed)
	{
		UGameplayStatics::SetGlobalTimeDilation(GetWorld(), IsHumanTurn() ? 0.4f : 0.6f);
		Announce(LOCTEXT("Special", "Եռաթև նետ"), IsHumanTurn() ? LOCTEXT("SpecialSub", "Ուղղորդի՛ր նետը մկնիկով") : FText::GetEmpty());
		TwFx::Sound2D(GetWorld(), TEXT("sfx_special_nova"), 0.6f, 1.3f);
	}
	TwFx::Sound(GetWorld(), TEXT("sfx_fireball_cast"), Start, 0.5f, 1.6f);
}

void AHaykGameMode::FinishImpact()
{
	UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 1.f);
	if (Hayk && Hayk->IsDead() || Bel && Bel->IsDead())
	{
		bHaykWon = Bel && Bel->IsDead();
		State = EHaykState::End;
		StateTime = 0.f;
		AHaykArcher* Winner = bHaykWon ? Hayk : Bel;
		if (Winner) Winner->Celebrate();
		if (World) World->PlayMusic(TEXT("music_menu"));
		const bool bPlayerWon = bVsBot ? bHaykWon : true;
		TwFx::Sound2D(GetWorld(), bPlayerWon ? TEXT("sfx_victory") : TEXT("sfx_defeat"), 1.f);
		if (AHaykPlayerController* PC = Cast<AHaykPlayerController>(UGameplayStatics::GetPlayerController(this, 0))) PC->OnDuelEnded();
		return;
	}
	BeginTurn();
}

void AHaykGameMode::SolveBot()
{
	// search pitch/yaw/power that brings the arrow closest to Hayk's chest, then add human-like error
	AHaykArcher* S = Bel;
	AHaykArcher* T = Hayk;
	if (!S || !T) return;
	const FVector Start = S->GetArrowSpawn();
	const FVector Aim = FMath::FRand() < 0.18f + 0.1f * Difficulty ? T->GetHeadTarget() : T->GetChestTarget();
	const float Base = BaseYawFor(S);
	float BestMiss = TNumericLimits<float>::Max();
	const float Powers[3] = { 0.82f, 0.92f, 1.f };
	for (float Pw : Powers)
	{
		for (float Pitch = -4.f; Pitch <= 40.f; Pitch += 0.5f)
		{
			for (float DY = -9.f; DY <= 9.f; DY += 0.75f)
			{
				const FVector V0 = FRotator(Pitch, Base + DY, 0.f).Vector() * AHaykArrow::MaxSpeed * Pw;
				float Tm = 0.f;
				const float Miss = AHaykArrow::SimulateMiss(GetWorld(), Start, V0, Wind, Aim, Tm, S);
				if (Miss < BestMiss) { BestMiss = Miss; BotPitch = Pitch; BotYaw = Base + DY; BotPower = Pw; }
			}
		}
	}
	// error shrinks after misses (Bel "learns" the wind)
	const float Sigma[3] = { 2.4f, 1.25f, 0.55f };
	const float Err = Sigma[Difficulty] * FMath::Pow(0.72f, (float)BotMisses);
	BotPitch += FMath::FRandRange(-1.f, 1.f) * Err;
	BotYaw += FMath::FRandRange(-1.f, 1.f) * Err;
	bBotSolved = true;
}

void AHaykGameMode::ThinkBot(float Dt)
{
	if (!Bel) return;
	BotTimer += Dt;
	if (!bBotSolved && BotTimer > 0.6f) SolveBot();
	if (!bBotSolved) return;
	// smooth aim toward the solution, then draw and release
	const float A = FMath::Clamp((BotTimer - 0.6f) / 1.3f, 0.f, 1.f);
	const float Sm = A * A * (3.f - 2.f * A);
	const float Yaw = FMath::Lerp(BaseYawFor(Bel), BotYaw, Sm);
	const float Pitch = FMath::Lerp(5.f, BotPitch, Sm);
	Bel->SetAim(Yaw, Pitch);
	if (BotTimer > 1.9f)
	{
		Power = FMath::Clamp((BotTimer - 1.9f) / 0.9f, 0.f, 1.f) * BotPower;
		Bel->SetDraw(Power);
		if (BotTimer > 2.9f)
		{
			// Bel uses his special when he is losing
			bSpecialArmed = SpecialsBel > 0 && Bel->GetHealth() < Bel->GetMaxHealth() * 0.45f && FMath::FRand() < 0.6f;
			Shoot(BotPower);
		}
	}
}

void AHaykGameMode::UpdatePreview()
{
	AHaykArcher* S = Shooter();
	if (!Preview || !S || !IsHumanTurn()) { if (Preview) Preview->Hide(); return; }
	const float Pw = bDrawing ? FMath::Max(Power, 0.25f) : 0.7f;
	FVector P = S->GetArrowSpawn();
	FVector V = FRotator(S->GetAimPitch(), S->GetAimYaw(), 0.f).Vector() * AHaykArrow::MaxSpeed * Pw;
	TArray<FVector> Pts;
	const float Dt = 1.f / 60.f;
	// only the first third of the arc (no wind): skill still matters
	const int32 Steps = 26;
	for (int32 i = 0; i < Steps * 2; ++i)
	{
		V += FVector(0, 0, -AHaykArrow::Gravity) * Dt;
		P += V * Dt;
		if (i % 2 == 0) Pts.Add(P);
	}
	Preview->Show(Pts);
}

void AHaykGameMode::Tick(float Dt)
{
	Super::Tick(Dt);
	StateTime += Dt;
	const float RealDt = FApp::GetDeltaTime();

	switch (State)
	{
	case EHaykState::Intro:
		if (StateTime > 3.5f) BeginTurn();
		break;
	case EHaykState::Aim:
	{
		AHaykArcher* S = Shooter();
		if (IsHumanTurn())
		{
			TurnLeft -= Dt;
			if (bDrawing)
			{
				Power = FMath::Min(1.f, Power + Dt / 1.1f);
				if (S) S->SetDraw(Power);
				// holding a full draw too long makes the arms tremble
				if (Power >= 1.f && S && StateTime > 0.f)
				{
					const float T = GetWorld()->GetTimeSeconds();
					S->SetAim(S->GetAimYaw() + FMath::Sin(T * 13.f) * 0.04f, S->GetAimPitch() + FMath::Sin(T * 9.f) * 0.04f);
				}
			}
			UpdatePreview();
			if (TurnLeft <= 0.f) { bDrawing = false; Shoot(FMath::Max(Power, 0.65f)); }
		}
		else
		{
			if (Preview) Preview->Hide();
			ThinkBot(Dt);
		}
		break;
	}
	case EHaykState::Flight:
	{
		AHaykArrow* A = Arrow.Get();
		if (!A) { FinishImpact(); break; }
		// cinematic slow-motion right before a hit
		if (!bSlowMo && A->GetResult() == EArrowResult::Flying && Target())
		{
			const FVector To = Target()->GetChestTarget() - A->GetActorLocation();
			const float Dist = To.Size();
			const float Along = FVector::DotProduct(To, A->GetVelocity().GetSafeNormal());
			const float Perp = FMath::Sqrt(FMath::Max(0.f, Dist * Dist - Along * Along));
			if (Along > 0.f && Along < 1400.f && Perp < 160.f)
			{
				bSlowMo = true;
				UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 0.22f);
			}
		}
		if (A->GetResult() != EArrowResult::Flying)
		{
			State = EHaykState::Impact;
			StateTime = 0.f;
			UGameplayStatics::SetGlobalTimeDilation(GetWorld(), A->GetResult() == EArrowResult::HitArcher ? 0.35f : 1.f);
			const bool bByBel = bBelTurn;
			if (A->GetResult() == EArrowResult::HitArcher)
			{
				int32& Hits = bByBel ? HitsBel : HitsHayk;
				int32& Heads = bByBel ? HeadsBel : HeadsHayk;
				int32& Streak = bByBel ? StreakBel : StreakHayk;
				int32& Spec = bByBel ? SpecialsBel : SpecialsHayk;
				++Hits; ++Streak;
				if (A->WasHeadshot()) ++Heads;
				if (Streak % 2 == 0) Spec = FMath::Min(2, Spec + 1);
				if (bByBel) BotMisses = 0;
				Announce(A->WasHeadshot() ? LOCTEXT("Head", "Գլխին") : LOCTEXT("Hit", "Դիպուկ է"), FText::Format(LOCTEXT("Dmg", "−{0}"), FText::AsNumber(FMath::RoundToInt(A->GetDamageDealt()))));
			}
			else
			{
				(bByBel ? StreakBel : StreakHayk) = 0;
				if (bByBel) ++BotMisses;
				Announce(A->GetResult() == EArrowResult::HitShield ? LOCTEXT("Shield", "Վահանին") : LOCTEXT("Miss", "Վրիպեց"), FText::GetEmpty());
			}
		}
		break;
	}
	case EHaykState::Impact:
		// StateTime is game time (dilated); use real time for the pause length
		if (GetWorld()->GetRealTimeSeconds() - (AnnTime) > 1.8f) FinishImpact();
		break;
	default: break;
	}
	UpdateCamera(RealDt);
}

void AHaykGameMode::UpdateCamera(float Dt)
{
	if (!Cam) return;
	FVector WantPos = CamPos;
	FRotator WantRot = CamRot;
	float Speed = 4.f;
	Orbit += Dt;

	auto OverShoulder = [](AHaykArcher* S, float Back, float Side, float Up, FVector& OutPos, FRotator& OutRot)
	{
		const FRotator Aim(0.f, S->GetAimYaw(), 0.f);
		const float Sc = S->IsBel() ? 1.45f : 1.f;
		OutPos = S->GetActorLocation() + Aim.RotateVector(FVector(-Back * Sc, Side * Sc, Up * Sc));
		OutRot = FRotator(S->GetAimPitch() * 0.45f - 6.f, S->GetAimYaw(), 0.f);
	};

	switch (State)
	{
	case EHaykState::Menu:
	{
		// slow establishing orbit of the valley
		const float A = Orbit * 0.05f;
		WantPos = FVector(FMath::Cos(A) * 9000.f, FMath::Sin(A) * 9000.f - 2000.f, 2600.f);
		WantRot = (FVector(0, 0, 500.f) - WantPos).Rotation();
		Speed = 1.5f;
		break;
	}
	case EHaykState::Intro:
	{
		const float T = FMath::Clamp(StateTime / 3.5f, 0.f, 1.f);
		WantPos = FMath::Lerp(FVector(-2000.f, -5200.f, 1400.f), FVector(-6500.f, -1500.f, 900.f), T);
		WantRot = (FVector(AHaykWorld::BelX, 0.f, 700.f) - WantPos).Rotation();
		Speed = 2.f;
		break;
	}
	case EHaykState::Aim:
		if (AHaykArcher* S = Shooter()) OverShoulder(S, 330.f, 85.f, 185.f, WantPos, WantRot);
		Speed = 6.f;
		break;
	case EHaykState::Flight:
		if (AHaykArrow* A = Arrow.Get())
		{
			const FVector V = A->GetVelocity().GetSafeNormal();
			const FVector Side = FVector::CrossProduct(FVector::UpVector, V).GetSafeNormal();
			WantPos = A->GetActorLocation() - V * 380.f + FVector(0, 0, 70.f) + Side * 40.f;
			WantRot = (A->GetActorLocation() + V * 400.f - WantPos).Rotation();
			Speed = 12.f;
		}
		break;
	case EHaykState::Impact:
		if (AHaykArrow* A = Arrow.Get())
		{
			const FVector P = A->GetImpactPoint();
			const FVector From = bBelTurn ? FVector(1.f, 0.6f, 0.f) : FVector(-1.f, 0.6f, 0.f);
			WantPos = P + From.GetSafeNormal() * 520.f + FVector(0, 0, 140.f);
			WantRot = (P - WantPos).Rotation();
			Speed = 5.f;
		}
		break;
	case EHaykState::End:
	{
		AHaykArcher* W = bHaykWon ? Hayk : Bel;
		if (W)
		{
			const float A = Orbit * 0.25f;
			const float Sc = W->IsBel() ? 1.45f : 1.f;
			const FVector C = W->GetActorLocation() + FVector(0, 0, 120.f * Sc);
			WantPos = C + FVector(FMath::Cos(A) * 520.f * Sc, FMath::Sin(A) * 520.f * Sc, 60.f * Sc);
			WantRot = (C - WantPos).Rotation();
			Speed = 3.f;
		}
		break;
	}
	}
	if (CamPos.IsNearlyZero()) { CamPos = WantPos; CamRot = WantRot; }
	CamPos = FMath::VInterpTo(CamPos, WantPos, Dt, Speed);
	CamRot = FMath::RInterpTo(CamRot, WantRot, Dt, Speed);
	Cam->SetActorLocationAndRotation(CamPos, CamRot);
}

#undef LOCTEXT_NAMESPACE
