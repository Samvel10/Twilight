#include "VahagnGameMode.h"
#include "Twilight.h"
#include "TwFx.h"
#include "Vishap.h"
#include "VahagnCharacter.h"
#include "VahagnPlayerController.h"
#include "VahagnWorld.h"

#include "Kismet/GameplayStatics.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/App.h"
#include "HAL/PlatformMisc.h"
#include "Engine/Engine.h"
#include "UnrealClient.h"

#define LOCTEXT_NAMESPACE "Vahagn"

static FString BestScorePath() { return FPaths::ProjectSavedDir() / TEXT("TwVahagnBest.txt"); }

AVahagnGameMode::AVahagnGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = false;
	DefaultPawnClass = AVahagnCharacter::StaticClass();
	PlayerControllerClass = AVahagnPlayerController::StaticClass();
	HUDClass = nullptr;
}

void AVahagnGameMode::StartPlay()
{
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	World = GetWorld()->SpawnActor<AVahagnWorld>(FVector::ZeroVector, FRotator::ZeroRotator, P);

	Super::StartPlay();

	FString Best;
	if (FFileHelper::LoadFileToString(Best, *BestScorePath())) BestScore = FCString::Atoi(*Best);

	if (UGameplayStatics::HasOption(OptionsString, TEXT("TwDiff")))
	{
		Difficulty = (EVahagnDifficulty)FMath::Clamp(UGameplayStatics::GetIntOption(OptionsString, TEXT("TwDiff"), 1), 0, 2);
	}
	FParse::Value(FCommandLine::Get(), TEXT("TwAutoPlay="), AutoTestSeconds);
	if (AutoTestSeconds > 0.f)
	{
		UE_LOG(LogTwilight, Display, TEXT("[TwTest] Auto play-test for %.0f s"), AutoTestSeconds);
		StartMatch();
		if (AVahagnCharacter* H = Hero()) H->SetAutopilot(true);
	}
	else if (UGameplayStatics::HasOption(OptionsString, TEXT("TwSkipMenu")))
	{
		StartMatch();
	}
}

void AVahagnGameMode::RestartPlayer(AController* NewPlayer)
{
	// no PlayerStart in the procedural level: hover above the purple sea, facing the sunset
	RestartPlayerAtTransform(NewPlayer, FTransform(FRotator(0.f, 200.f, 0.f), FVector(0.f, 0.f, 2600.f)));
}

AVahagnCharacter* AVahagnGameMode::Hero() const
{
	return Cast<AVahagnCharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
}

float AVahagnGameMode::DamageToPlayerMultiplier() const
{
	switch (Difficulty) { case EVahagnDifficulty::Easy: return 0.5f; case EVahagnDifficulty::Hard: return 1.25f; default: return 0.8f; }
}

float AVahagnGameMode::HealthMultiplier() const
{
	switch (Difficulty) { case EVahagnDifficulty::Easy: return 0.7f; case EVahagnDifficulty::Hard: return 1.35f; default: return 1.f; }
}

int32 AVahagnGameMode::AliveVishaps() const
{
	int32 N = 0;
	for (TActorIterator<AVishap> It(GetWorld()); It; ++It) if (It->IsAlive()) ++N;
	return N;
}

bool AVahagnGameMode::GetAnnouncement(FText& Title, FText& Sub, float& Age) const
{
	Age = GetWorld()->GetRealTimeSeconds() - AnnTime;
	Title = AnnTitle; Sub = AnnSub;
	return Age < 3.2f;
}

void AVahagnGameMode::Announce(const FText& Title, const FText& Sub)
{
	AnnTitle = Title; AnnSub = Sub; AnnTime = GetWorld()->GetRealTimeSeconds();
}

void AVahagnGameMode::StartMatch()
{
	// clean slate
	for (TActorIterator<AVishap> It(GetWorld()); It; ++It) It->Destroy();
	MatchState = EVahagnMatch::Intro;
	IntroLeft = 3.f;
	TimeLeft = MatchLength;
	MatchTime = 0.f;
	Wave = 0;
	WaveTime = 0.f;
	NextWaveDelay = -1.f;
	bBossSpawned = false;
	Boss = nullptr;
	Score = 0;
	Kills = 0;
	UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 1.f);
	if (AVahagnPlayerController* PC = Cast<AVahagnPlayerController>(UGameplayStatics::GetPlayerController(this, 0))) PC->OnMatchStarted();
	IntroLeft = 4.2f;
	if (AVahagnCharacter* H = Hero()) { if (AutoTestSeconds > 0.f) { IntroLeft = 1.f; H->SetControlEnabled(true); } else H->BeginBirth(FVector(0.f, 0.f, 700.f), IntroLeft); }
	if (World) World->PlayMusic(TEXT("music_battle"));
	Announce(LOCTEXT("Ready", "«Երկնէր երկին, երկնէր երկիր, երկնէր և ծովն ծիրանի…»"), LOCTEXT("ReadySub", "Ծիրանի ծովի եղեգից ծնվում է Վահագնը"));
}

void AVahagnGameMode::RestartMatch()
{
	UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 1.f);
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true, FString::Printf(TEXT("TwSkipMenu=1?TwDiff=%d"), (int32)Difficulty));
}

void AVahagnGameMode::ReturnToMenu()
{
	UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 1.f);
	UGameplayStatics::OpenLevel(this, FName(*UGameplayStatics::GetCurrentLevelName(this)), true, FString::Printf(TEXT("TwDiff=%d"), (int32)Difficulty));
}

void AVahagnGameMode::BeginWave(int32 Index)
{
	Wave = Index;
	WaveTime = 0.f;
	NextWaveDelay = -1.f;
	const float Base = FMath::FRandRange(0.f, 360.f);
	switch (Index)
	{
	case 1:
		Announce(LOCTEXT("W1", "Ալիք 1"), LOCTEXT("W1s", "Երեք վիշապ բարձրանում է ծիրանի ծովից"));
		for (int32 i = 0; i < 4; ++i) SpawnVishap(false, 0, 7500.f, Base + i * 90.f);
		break;
	case 2:
		Announce(LOCTEXT("W2", "Ալիք 2"), LOCTEXT("W2s", "Կարմիր վիշապը ավելի արագ է"));
		for (int32 i = 0; i < 4; ++i) SpawnVishap(false, 0, 8000.f, Base + i * 72.f);
		SpawnVishap(false, 1, 9000.f, Base + 288.f);
		break;
	case 3:
		Announce(LOCTEXT("W3", "Ալիք 3"), LOCTEXT("W3s", "Ծովը եռում է"));
		for (int32 i = 0; i < 4; ++i) SpawnVishap(false, 0, 8000.f, Base + i * 60.f);
		SpawnVishap(false, 1, 9000.f, Base + 240.f);
		SpawnVishap(false, 1, 9000.f, Base + 288.f);
		break;
	default:
		break;
	}
	TwFx::Sound2D(GetWorld(), TEXT("sfx_wave_start"), 0.8f);
}

void AVahagnGameMode::SpawnVishap(bool bBoss, int32 Tier, float Dist, float AngleDeg)
{
	AVahagnCharacter* H = Hero();
	const FVector C = H ? H->GetActorLocation() : FVector(0, 0, 3000.f);
	const float A = FMath::DegreesToRadians(AngleDeg);
	FVector P = FVector(C.X + FMath::Cos(A) * Dist, C.Y + FMath::Sin(A) * Dist, bBoss ? -6000.f : -2500.f);
	// keep spawn inside the arena
	const float R = FVector2D(P.X, P.Y).Size();
	const float MaxR = AVahagnCharacter::ArenaRadius * 0.8f;
	if (R > MaxR) { P.X *= MaxR / R; P.Y *= MaxR / R; }
	FActorSpawnParameters S;
	S.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	S.bDeferConstruction = true;
	AVishap* V = GetWorld()->SpawnActor<AVishap>(P, FRotator::ZeroRotator, S);
	if (!V) return;
	V->Setup(bBoss, Tier, HealthMultiplier());
	UGameplayStatics::FinishSpawningActor(V, FTransform(P));
	if (bBoss) Boss = V;
}

void AVahagnGameMode::OnVishapKilled(AVishap* V)
{
	if (MatchState != EVahagnMatch::Playing) return;
	++Kills;
	Score += V->IsBoss() ? 3000 : (V->GetTier() > 0 ? 250 : 150);
	if (V->IsBoss())
	{
		// slow-motion finale
		UGameplayStatics::SetGlobalTimeDilation(GetWorld(), 0.25f);
		FTimerHandle H;
		TWeakObjectPtr<AVahagnGameMode> Self(this);
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateLambda([Self]()
		{
			if (Self.IsValid()) { UGameplayStatics::SetGlobalTimeDilation(Self->GetWorld(), 1.f); Self->EndMatch(true); }
		}), 0.6f, false);
		TwFx::Sound2D(GetWorld(), TEXT("sfx_big_explosion"), 1.f, 0.6f);
	}
}

void AVahagnGameMode::OnBossPhase(AVishap* B, int32 Phase)
{
	if (Phase == 1)
	{
		Announce(LOCTEXT("P1", "Մեծ վիշապը կանչում է օգնության"), LOCTEXT("P1s", "Խոցի՛ր գլուխը՝ կրկնակի վնաս"));
		SpawnVishap(false, 0, 6000.f, FMath::FRandRange(0.f, 360.f));
		SpawnVishap(false, 0, 6000.f, FMath::FRandRange(0.f, 360.f));
	}
	else if (Phase == 2)
	{
		Announce(LOCTEXT("P2", "Մեծ վիշապը կատաղել է"), LOCTEXT("P2s", "Օգտագործի՛ր Արևի պոռթկումը (Q)"));
		SpawnVishap(false, 1, 6000.f, FMath::FRandRange(0.f, 360.f));
	}
}

void AVahagnGameMode::EndMatch(bool bVictory)
{
	if (MatchState == EVahagnMatch::Victory || MatchState == EVahagnMatch::Defeat) return;
	MatchState = bVictory ? EVahagnMatch::Victory : EVahagnMatch::Defeat;
	EndTime = GetWorld()->GetRealTimeSeconds();
	if (bVictory)
	{
		Score += FMath::RoundToInt(TimeLeft) * 10;
		if (AVahagnCharacter* H = Hero()) Score += FMath::RoundToInt(H->GetHealth()) * 15;
		TwFx::Sound2D(GetWorld(), TEXT("sfx_victory"), 1.f);
		if (World) World->PlayMusic(TEXT("music_menu"));
	}
	else
	{
		TwFx::Sound2D(GetWorld(), TEXT("sfx_defeat"), 1.f);
		if (World) World->PlayMusic(TEXT("music_menu"));
	}
	if (Score > BestScore)
	{
		BestScore = Score;
		FFileHelper::SaveStringToFile(FString::FromInt(BestScore), *BestScorePath());
	}
	if (AVahagnCharacter* H = Hero()) H->SetControlEnabled(false);
	if (AVahagnPlayerController* PC = Cast<AVahagnPlayerController>(UGameplayStatics::GetPlayerController(this, 0))) PC->OnMatchEnded(bVictory);
	UE_LOG(LogTwilight, Display, TEXT("[TwTest] Match ended: %s score=%d kills=%d time=%.1f"), bVictory ? TEXT("VICTORY") : TEXT("DEFEAT"), Score, Kills, MatchTime);
}

void AVahagnGameMode::Tick(float Dt)
{
	Super::Tick(Dt);
	const float RealDt = FApp::GetDeltaTime();
	if (AutoTestSeconds > 0.f) TickAutoTest(RealDt);

	switch (MatchState)
	{
	case EVahagnMatch::Intro:
		IntroLeft -= Dt;
		if (IntroLeft <= 0.f) { MatchState = EVahagnMatch::Playing; if (AVahagnCharacter* H = Hero()) H->SetControlEnabled(true); BeginWave(1); }
		break;
	case EVahagnMatch::Playing:
	{
		MatchTime += Dt;
		TimeLeft = FMath::Max(0.f, TimeLeft - Dt);
		WaveTime += Dt;
		AVahagnCharacter* H = Hero();
		if (H && H->IsDead()) { EndMatch(false); break; }
		if (TimeLeft <= 0.f) { Announce(LOCTEXT("TimeUp", "Ժամանակը սպառվեց"), FText::GetEmpty()); EndMatch(false); break; }

		const int32 Alive = AliveVishaps();
		if (!bBossSpawned)
		{
			const bool bCleared = Alive == 0;
			const bool bOverdue = WaveTime > 110.f;
			if ((bCleared || bOverdue) && NextWaveDelay < 0.f) NextWaveDelay = bCleared ? 3.5f : 0.f;
			if (NextWaveDelay >= 0.f)
			{
				NextWaveDelay -= Dt;
				if (NextWaveDelay <= 0.f)
				{
					NextWaveDelay = -1.f;
					if (Wave < 3) BeginWave(Wave + 1);
					else
					{
						bBossSpawned = true;
						Wave = 4;
						Announce(LOCTEXT("Boss", "Մեծ վիշապը"), LOCTEXT("BossSub", "Արթնացավ ծովի ամենախոր հատակից"));
						SpawnVishap(true, 0, 11000.f, H ? H->GetControlRotation().Yaw : 0.f);
						if (World) World->PlayMusic(TEXT("music_boss"));
						TwFx::Sound2D(GetWorld(), TEXT("sfx_vishap_roar"), 1.f, 0.55f);
					}
				}
			}
		}
		break;
	}
	default: break;
	}
}

void AVahagnGameMode::TickAutoTest(float RealDt)
{
	AutoTestElapsed += RealDt;
	FrameTimes.Add(RealDt);
	StatTimer += RealDt;
	AutoShotTimer += RealDt;
	AVahagnCharacter* H = Hero();
	if (StatTimer >= 10.f)
	{
		StatTimer = 0.f;
		float Sum = 0.f; int32 N = 0;
		for (int32 i = FrameTimes.Num() - 1; i >= 0 && Sum < 10.f; --i) { Sum += FrameTimes[i]; ++N; }
		N = FMath::Max(1, N);
		UE_LOG(LogTwilight, Display, TEXT("[TwTest] t=%.0f fps=%.1f actors=%d state=%d wave=%d alive=%d hp=%.0f score=%d kills=%d"),
			AutoTestElapsed, N / FMath::Max(Sum, 0.001f), GetWorld()->GetActorCount(), (int32)MatchState, Wave, AliveVishaps(), H ? H->GetHealth() : -1.f, Score, Kills);
	}
	if (AutoShotTimer >= 15.f)
	{
		AutoShotTimer = 0.f;
		FScreenshotRequest::RequestScreenshot(FString::Printf(TEXT("TwShot_%03d"), AutoShotIndex++), false, false);
	}
	// invulnerable-ish test pilot so the test reaches the boss: heal when low
	if (H && H->GetHealth() < 35.f && FParse::Param(FCommandLine::Get(), TEXT("TwGodPilot"))) H->Heal(60.f);

	if (AutoTestElapsed >= AutoTestSeconds)
	{
		TArray<float> Sorted = FrameTimes; Sorted.Sort();
		float Sum = 0.f; for (float F : Sorted) Sum += F;
		const int32 N = FMath::Max(1, Sorted.Num());
		const float Avg = N / FMath::Max(Sum, 0.001f);
		const float P95 = Sorted.Num() ? 1.f / Sorted[FMath::Min(N - 1, int32(N * 0.95f))] : 0.f;
		const float P99 = Sorted.Num() ? 1.f / Sorted[FMath::Min(N - 1, int32(N * 0.99f))] : 0.f;
		const FString Summary = FString::Printf(TEXT("frames=%d avg_fps=%.1f p95_fps=%.1f p99_fps=%.1f state=%d wave=%d kills=%d score=%d hp=%.0f boss=%s\n"),
			N, Avg, P95, P99, (int32)MatchState, Wave, Kills, Score, H ? H->GetHealth() : -1.f, Boss.IsValid() ? TEXT("alive") : (bBossSpawned ? TEXT("dead") : TEXT("none")));
		FFileHelper::SaveStringToFile(Summary, *(FPaths::ProjectSavedDir() / TEXT("TwTestSummary.txt")));
		UE_LOG(LogTwilight, Display, TEXT("[TwTest] DONE %s"), *Summary);
		AutoTestSeconds = 0.f;
		FPlatformMisc::RequestExit(false);
	}
}

#undef LOCTEXT_NAMESPACE
