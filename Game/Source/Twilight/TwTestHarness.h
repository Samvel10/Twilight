#pragma once

#include "CoreMinimal.h"

class UWorld;

/** Shared automated play-test helper: -TwAutoPlay=<seconds>. Logs FPS, takes screenshots, writes a summary, quits. */
struct FTwTestHarness
{
	float Seconds = 0.f;
	float Elapsed = 0.f;
	float StatTimer = 0.f;
	float ShotTimer = 0.f;
	int32 ShotIndex = 0;
	TArray<float> Frames;

	/** Reads -TwAutoPlay= from the command line; returns true when a test is active. */
	bool Init();
	bool IsActive() const { return Seconds > 0.f; }
	/** Call every frame with the real (undilated) delta. Status is a short line appended to the periodic log. Returns true when the test just finished. */
	bool Tick(UWorld* World, float RealDt, const FString& Status, const TCHAR* Name);
};
