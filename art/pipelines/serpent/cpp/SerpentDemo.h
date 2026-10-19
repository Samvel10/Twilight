// Proto-only demo: flies a serpent along an analytic path (follow-the-leader sampling of the head trajectory),
// frames it with its own camera, logs perf and takes screenshots. Driven by command-line switches:
//  -SerpMode=sky|rise|coil  -SerpT=<sec, freeze time; <0 = live>  -SerpScale=4  -SerpJaw=0..1
//  -SerpCamDist=2000 -SerpCamYaw=deg -SerpCamPitch=deg -SerpCamAt=0.3 (body alpha looked at) -SerpFov=55
//  -SerpShotAt=<sec> -SerpShot=<file.png>  -SerpQuitAt=<sec>  -SerpHide (perf A/B)  -SerpChase (camera follows head)
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/GameModeBase.h"
#include "SerpentDemo.generated.h"

class USerpentBodyComponent;
class UCameraComponent;

UCLASS()
class ASerpentDemo : public AActor
{
	GENERATED_BODY()
public:
	ASerpentDemo();
	virtual void BeginPlay() override;
	virtual void Tick(float Dt) override;

	UPROPERTY(VisibleAnywhere) TObjectPtr<USerpentBodyComponent> Body;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Cam;
	UPROPERTY(EditAnywhere) FVector Center = FVector(0, 0, 0);
	UPROPERTY(EditAnywhere) float Altitude = 6000.f;
	UPROPERTY(EditAnywhere) float Speed = 2200.f;    // cm/s along the path (approx.)
	UPROPERTY(EditAnywhere) float Radius = 9000.f;

	FVector HeadAt(float T) const;
private:
	FString Mode = TEXT("sky");
	float FreezeT = -1.f, CamDist = 2000.f, CamYaw = 0.f, CamPitch = 5.f, CamAt = 0.3f, Fov = 55.f;
	float ShotAt = -1.f, QuitAt = -1.f, Jaw = 0.f, Clock = 0.f;
	FString ShotFile;
	bool bShotDone = false, bChase = false, bRefPose = false;
	double PerfAcc = 0, GpuAcc = 0, CpuAcc = 0; int32 PerfN = 0; float PerfT = 0;
	TArray<FVector> Path;
	// -SerpToggle=<sec>: alternate serpent visible/hidden, log per-phase GPU (in-process A/B, robust to other GPU users)
	float TogglePeriod = 0.f, ToggleT = 0.f; bool bToggleVis = true; int32 ToggleN = 0; double ToggleGpu = 0; int32 TogglePhase = 0;
	TArray<double> GpuVis, GpuHid;
	int32 ProfStep = 0; float ProfPending = 0.f;
	float ExecAt = -1.f; FString ExecCmd; bool bExecDone = false;
};

UCLASS()
class ASerpentGameMode : public AGameModeBase
{
	GENERATED_BODY()
public:
	ASerpentGameMode() { DefaultPawnClass = nullptr; }
};
