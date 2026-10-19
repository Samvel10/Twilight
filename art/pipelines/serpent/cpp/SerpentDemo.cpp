#include "SerpentDemo.h"
#include "SerpentBodyComponent.h"
#include "Camera/CameraComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInterface.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "UnrealClient.h"
#include "RHI.h"
#include "Engine/Engine.h"
#include "HAL/PlatformTime.h"

ASerpentDemo::ASerpentDemo()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	Body = CreateDefaultSubobject<USerpentBodyComponent>(TEXT("Body"));
	Body->SetupAttachment(RootComponent);
	Cam = CreateDefaultSubobject<UCameraComponent>(TEXT("Cam"));
	Cam->SetupAttachment(RootComponent);
	Cam->SetUsingAbsoluteLocation(true);
	Cam->SetUsingAbsoluteRotation(true);
	Cam->bConstrainAspectRatio = false;
}

FVector ASerpentDemo::HeadAt(float T) const
{
	const float W = Speed / Radius;   // rad/s for the base loop
	if (Mode == TEXT("line")) return Center + FVector(Speed * T, 0.f, Altitude);   // debug: straight path
	if (Mode == TEXT("rise"))
	{
		// vertical arch out of a lake (surface z = Center.Z): circle in the XZ plane, centre slightly above water
		const float R = Radius * 0.45f;
		const float A = W * 2.2f * T;
		return Center + FVector(R * FMath::Sin(A), 0.12f * R * FMath::Sin(0.5f * A), -R * FMath::Cos(A) + R * 0.55f);
	}
	if (Mode == TEXT("coil"))
	{
		// tight climbing helix (storm coil)
		const float A = W * 2.5f * T;
		return Center + FVector(Radius * 0.35f * FMath::Cos(A), Radius * 0.35f * FMath::Sin(A), Altitude + 900.f * T);
	}
	// sky: wide figure-eight with gentle climbs and dives
	const float A = W * T;
	return Center + FVector(Radius * FMath::Sin(A), Radius * 0.55f * FMath::Sin(2.f * A), Altitude + 1400.f * FMath::Sin(1.5f * A + 0.6f));
}

void ASerpentDemo::BeginPlay()
{
	Super::BeginPlay();
	const TCHAR* C = FCommandLine::Get();
	FParse::Value(C, TEXT("SerpMode="), Mode);
	FParse::Value(C, TEXT("SerpT="), FreezeT);
	float Scale = 4.f; FParse::Value(C, TEXT("SerpScale="), Scale);
	FParse::Value(C, TEXT("SerpJaw="), Jaw);
	FParse::Value(C, TEXT("SerpCamDist="), CamDist);
	FParse::Value(C, TEXT("SerpCamYaw="), CamYaw);
	FParse::Value(C, TEXT("SerpCamPitch="), CamPitch);
	FParse::Value(C, TEXT("SerpCamAt="), CamAt);
	FParse::Value(C, TEXT("SerpFov="), Fov);
	FParse::Value(C, TEXT("SerpShotAt="), ShotAt);
	FParse::Value(C, TEXT("SerpShot="), ShotFile);
	FParse::Value(C, TEXT("SerpQuitAt="), QuitAt);
	FParse::Value(C, TEXT("SerpSpeed="), Speed);
	FParse::Value(C, TEXT("SerpAlt="), Altitude);
	bChase = FParse::Param(C, TEXT("SerpChase"));
	bRefPose = FParse::Param(C, TEXT("SerpRef"));
	FParse::Value(C, TEXT("SerpHead="), Body->HeadScale);
	FParse::Value(C, TEXT("SerpWave="), Body->WaveAmplitude);
	FParse::Value(C, TEXT("SerpWaveLen="), Body->WaveLength);
	FParse::Value(C, TEXT("SerpRadius="), Radius);
	FParse::Value(C, TEXT("SerpCenterX="), Center.X);
	FParse::Value(C, TEXT("SerpCenterY="), Center.Y);
	{
		FString MatPath;   // e.g. -SerpMat=/Game/Twilight/Vishap/Materials/MI_Vishap_Bronze.MI_Vishap_Bronze
		if (FParse::Value(C, TEXT("SerpMat="), MatPath))
			if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, *MatPath)) Body->SetMaterial(0, M);
	}
	FParse::Value(C, TEXT("SerpToggle="), TogglePeriod);
	FParse::Value(C, TEXT("SerpExecAt="), ExecAt);
	FParse::Value(C, TEXT("SerpExec="), ExecCmd);   // e.g. -SerpExec=ProfileGPU
	if (FParse::Param(C, TEXT("SerpHorns")))
		Body->HeadAttachment = LoadObject<UStaticMesh>(nullptr, TEXT("/Game/Twilight/Vishap/Mesh/Horns/SM_VishapHorns/StaticMeshes/SM_VishapHorns.SM_VishapHorns"));
	if (FParse::Param(C, TEXT("SerpHide"))) Body->SetVisibility(false, true);
	if (Mode == TEXT("rise")) Center.Z = 0.f;
	Body->SetWorldScale3D(FVector(Scale));
	Cam->SetFieldOfView(Fov);
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0)) PC->SetViewTarget(this);
	UE_LOG(LogTemp, Warning, TEXT("SERP begin mode=%s scale=%.2f mesh=%s"), *Mode, Scale, Body->GetSkinnedAsset() ? *Body->GetSkinnedAsset()->GetName() : TEXT("none"));
}

void ASerpentDemo::Tick(float Dt)
{
	Super::Tick(Dt);
	Clock += Dt;
	const float T = FreezeT >= 0.f ? FreezeT : Clock;
	// follow-the-leader: the body lies on the head's past trajectory
	const float Len = Body->GetBodyLength() > 1.f ? Body->GetBodyLength() : 4000.f;
	const float Step = FMath::Max(Len / 160.f, 5.f);
	Path.Reset();
	float Acc = 0.f, Tk = T;
	Path.Add(HeadAt(Tk));
	for (int32 k = 0; k < 2000 && Acc < Len * 1.05f; ++k)
	{
		Tk -= Step / Speed;
		const FVector P = HeadAt(Tk);
		Acc += FVector::Dist(P, Path.Last());
		Path.Add(P);
	}
	Body->JawOpen = Jaw;
	const double T0 = FPlatformTime::Seconds();
	if (!bRefPose) Body->ApplyPath(Path, FVector::UpVector, T);
	CpuAcc += (FPlatformTime::Seconds() - T0) * 1e6;

	const FVector Target = bRefPose ? Body->GetComponentLocation() : Body->GetBodyPoint(CamAt);
	if (bChase)
	{
		const FVector HeadP = Body->GetBodyPoint(0.f), Behind = Body->GetBodyPoint(0.08f);
		const FVector Back = (Behind - HeadP).GetSafeNormal();
		const FVector CamP = HeadP + Back * CamDist + FVector(0, 0, CamDist * 0.25f);
		Cam->SetWorldLocationAndRotation(CamP, (HeadP - CamP).Rotation());
	}
	else
	{
		const FRotator R(CamPitch, CamYaw, 0.f);
		const FVector CamP = Target - R.Vector() * CamDist;
		Cam->SetWorldLocationAndRotation(CamP, R);
	}

	if (TogglePeriod > 0.f && Clock > 8.f)
	{
		ToggleT += Dt;
		if (ToggleT > 0.6f) { ToggleGpu += FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles()); ++ToggleN; }   // skip the switch frames
		if (ToggleT >= TogglePeriod)
		{
			const double Avg = ToggleN ? ToggleGpu / ToggleN : 0.0;
			(bToggleVis ? GpuVis : GpuHid).Add(Avg);
			UE_LOG(LogTemp, Warning, TEXT("SERP toggle phase=%d visible=%d gpu=%.2fms frames=%d"), TogglePhase++, bToggleVis ? 1 : 0, Avg, ToggleN);
			bToggleVis = !bToggleVis;
			Body->SetVisibility(bToggleVis, true);
			ToggleT = 0.f; ToggleGpu = 0; ToggleN = 0;
			if (GpuVis.Num() >= 2 && GpuHid.Num() >= 2)
			{
				TArray<double> A = GpuVis, B = GpuHid; A.Sort(); B.Sort();
				UE_LOG(LogTemp, Warning, TEXT("SERP toggle median vis=%.2f hid=%.2f delta=%.2fms (n=%d/%d)"), A[A.Num() / 2], B[B.Num() / 2], A[A.Num() / 2] - B[B.Num() / 2], A.Num(), B.Num());
			}
		}
	}
	if (ExecAt >= 0.f && !bExecDone && Clock >= ExecAt && GEngine)
	{
		bExecDone = true;
		GEngine->Exec(GetWorld(), *ExecCmd);
		UE_LOG(LogTemp, Warning, TEXT("SERP exec %s"), *ExecCmd);
	}
	// -SerpProfAB: ProfileGPU with the serpent visible at 14 s, hidden at 17 s, visible again at 20 s, hidden at 23 s
	if (FParse::Param(FCommandLine::Get(), TEXT("SerpProfAB")) && GEngine)
	{
		static const float Times[4] = { 14.f, 17.f, 20.f, 23.f };
		for (int32 k = 0; k < 4; ++k)
			if (ProfStep == k && Clock >= Times[k])
			{
				const bool bVis = (k % 2) == 0;
				Body->SetVisibility(bVis, true);
				ProfPending = 0.5f;   // let the visibility change settle before profiling
				++ProfStep;
			}
		if (ProfPending > 0.f && (ProfPending -= Dt) <= 0.f)
		{
			UE_LOG(LogTemp, Warning, TEXT("SERP profab step=%d visible=%d"), ProfStep, Body->IsVisible() ? 1 : 0);
			GEngine->Exec(GetWorld(), TEXT("ProfileGPU"));
		}
	}
	// perf log
	PerfAcc += Dt; GpuAcc += FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles()); ++PerfN; PerfT += Dt;
	if (PerfT > 3.f)
	{
		UE_LOG(LogTemp, Warning, TEXT("SERP perf t=%.1f fps=%.1f frame=%.2fms gpu=%.2fms lod=%d applypath=%.1fus"), Clock, PerfN / PerfAcc, 1000.0 * PerfAcc / PerfN, GpuAcc / PerfN, Body->GetPredictedLODLevel(), CpuAcc / PerfN);
		PerfAcc = GpuAcc = 0; CpuAcc = 0; PerfN = 0; PerfT = 0;
	}
	if (ShotAt >= 0.f && !bShotDone && Clock >= ShotAt)
	{
		bShotDone = true;
		FScreenshotRequest::RequestScreenshot(ShotFile.IsEmpty() ? FString(TEXT("serp.png")) : ShotFile, false, false);
		UE_LOG(LogTemp, Warning, TEXT("SERP shot %s"), *ShotFile);
	}
	if (QuitAt >= 0.f && Clock >= QuitAt)
	{
		UE_LOG(LogTemp, Warning, TEXT("SERP quit"));
		FPlatformMisc::RequestExit(false, TEXT("SerpQuit"));
	}
}
