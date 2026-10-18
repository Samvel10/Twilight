#include "TwTestHarness.h"
#include "Twilight.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/PlatformMisc.h"
#include "UnrealClient.h"

bool FTwTestHarness::Init()
{
	FParse::Value(FCommandLine::Get(), TEXT("TwAutoPlay="), Seconds);
	return Seconds > 0.f;
}

bool FTwTestHarness::Tick(UWorld* World, float RealDt, const FString& Status, const TCHAR* Name)
{
	if (Seconds <= 0.f) return false;
	Elapsed += RealDt;
	Frames.Add(RealDt);
	StatTimer += RealDt;
	ShotTimer += RealDt;
	if (StatTimer >= 10.f)
	{
		StatTimer = 0.f;
		float Sum = 0.f;
		const int32 N0 = FMath::Max(0, Frames.Num() - 600);
		for (int32 i = N0; i < Frames.Num(); ++i) Sum += Frames[i];
		UE_LOG(LogTwilight, Display, TEXT("[TwTest] %s t=%.0f fps=%.1f %s"), Name, Elapsed, (Frames.Num() - N0) / FMath::Max(Sum, 0.001f), *Status);
	}
	if (ShotTimer >= 15.f)
	{
		ShotTimer = 0.f;
		FScreenshotRequest::RequestScreenshot(FString::Printf(TEXT("Tw%s_%03d"), Name, ShotIndex++), false, false);
	}
	if (Elapsed < Seconds) return false;

	TArray<float> Sorted = Frames;
	Sorted.Sort();
	float Sum = 0.f;
	for (float F : Sorted) Sum += F;
	const int32 N = FMath::Max(1, Sorted.Num());
	const FString Summary = FString::Printf(TEXT("game=%s frames=%d avg_fps=%.1f p95_fps=%.1f p99_fps=%.1f %s\n"), Name, N, N / FMath::Max(Sum, 0.001f),
		Sorted.Num() ? 1.f / Sorted[FMath::Min(N - 1, int32(N * 0.95f))] : 0.f, Sorted.Num() ? 1.f / Sorted[FMath::Min(N - 1, int32(N * 0.99f))] : 0.f, *Status);
	FFileHelper::SaveStringToFile(Summary, *(FPaths::ProjectSavedDir() / TEXT("TwTestSummary.txt")));
	UE_LOG(LogTwilight, Display, TEXT("[TwTest] DONE %s"), *Summary);
	Seconds = 0.f;
	FPlatformMisc::RequestExit(false);
	return true;
}
