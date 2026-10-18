#include "TwFlash.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "TwAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

ATwFlash::ATwFlash()
{
	PrimaryActorTick.bCanEverTick = true;
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetCastShadow(false);
	Mesh->SetGenerateOverlapEvents(false);
}

void ATwFlash::Init(const FLinearColor& Color, float InSize, float Duration)
{
	Size = InSize;
	Dur = FMath::Max(0.05f, Duration);
	Mesh->SetStaticMesh(TwAssets::Sphere());
	Mat = UMaterialInstanceDynamic::Create(TwAssets::Material(TEXT("M_Additive")), this);
	if (Mat)
	{
		Mat->SetVectorParameterValue(TEXT("Color"), Color);
		Mat->SetScalarParameterValue(TEXT("GlowMode"), 1.f);
		Mat->SetScalarParameterValue(TEXT("Intensity"), PeakIntensity);
		Mat->SetScalarParameterValue(TEXT("Falloff"), 3.f); // soft edge: a glow, not a solid disc
		Mesh->SetMaterial(0, Mat);
	}
	Mesh->SetWorldScale3D(FVector(Size * 0.3f));
	SetLifeSpan(Dur + 0.05f);
}

void ATwFlash::Tick(float Dt)
{
	Super::Tick(Dt);
	Age += Dt;
	const float A = FMath::Clamp(Age / Dur, 0.f, 1.f);
	Mesh->SetWorldScale3D(FVector(Size * (0.3f + 0.9f * FMath::Sqrt(A))));
	// never flash across the whole lens
	float CamFade = 1.f;
	if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
		if (PC->PlayerCameraManager)
		{
			const float Near = Size * 60.f + 150.f;
			CamFade = FMath::SmoothStep(Near, Near * 3.f, (float)FVector::Dist(GetActorLocation(), PC->PlayerCameraManager->GetCameraLocation()));
		}
	if (Mat) Mat->SetScalarParameterValue(TEXT("Intensity"), PeakIntensity * (1.f - A) * (1.f - A) * CamFade);
}
