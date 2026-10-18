#include "TwFx.h"
#include "TwAssets.h"
#include "Twilight.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/PointLight.h"
#include "Engine/World.h"
#include "TimerManager.h"

namespace TwFx
{
	// Niagara systems we build ourselves (see Tools/build_assets.py). Missing -> Cascade fallback.
	static UNiagaraSystem* Ns(const TCHAR* Name)
	{
		const FString P = FString::Printf(TEXT("/Game/Twilight/FX/%s.%s"), Name, Name);
		return TwAssets::Niagara(*P);
	}

	void Burst(UWorld* World, EFx Type, const FVector& Loc, float Scale, const FRotator& Rot)
	{
		if (!World) return;
		const TCHAR* NsName = nullptr;
		const TCHAR* Cascade = nullptr;
		switch (Type)
		{
		case EFx::FireballImpact: NsName = TEXT("NS_FireImpact"); Cascade = TEXT("P_Explosion"); break;
		case EFx::BigExplosion:   NsName = TEXT("NS_BigExplosion"); Cascade = TEXT("P_Explosion"); break;
		case EFx::VishapDeath:    NsName = TEXT("NS_BigExplosion"); Cascade = TEXT("P_Explosion"); break;
		case EFx::Splash:         NsName = TEXT("NS_Splash"); Cascade = TEXT("P_Steam_Lit"); break;
		case EFx::Sparks:         NsName = TEXT("NS_Sparks"); Cascade = TEXT("P_Sparks"); break;
		case EFx::Smoke:          NsName = TEXT("NS_Smoke"); Cascade = TEXT("P_Smoke"); break;
		case EFx::Nova:           NsName = TEXT("NS_Nova"); Cascade = TEXT("P_Explosion"); break;
		case EFx::MuzzleFlash:    NsName = TEXT("NS_Muzzle"); Cascade = TEXT("P_Sparks"); break;
		}
		if (UNiagaraSystem* S = NsName ? Ns(NsName) : nullptr)
		{
			UNiagaraFunctionLibrary::SpawnSystemAtLocation(World, S, Loc, Rot, FVector(Scale), true, true, ENCPoolMethod::AutoRelease);
			return;
		}
		if (UParticleSystem* P = Cascade ? TwAssets::Cascade(Cascade) : nullptr)
		{
			UGameplayStatics::SpawnEmitterAtLocation(World, P, Loc, Rot, FVector(Scale), true, EPSCPoolMethod::AutoRelease);
		}
	}

	UFXSystemComponent* AttachFlame(USceneComponent* Parent, FName Socket, const FVector& Offset, float Scale)
	{
		if (!Parent) return nullptr;
		if (UNiagaraSystem* S = Ns(TEXT("NS_FlameAura")))
		{
			UNiagaraComponent* C = UNiagaraFunctionLibrary::SpawnSystemAttached(S, Parent, Socket, Offset, FRotator::ZeroRotator, FVector(Scale), EAttachLocation::KeepRelativeOffset, false, ENCPoolMethod::None, true, true);
			return C;
		}
		if (UParticleSystem* P = TwAssets::Cascade(TEXT("P_Fire")))
		{
			return UGameplayStatics::SpawnEmitterAttached(P, Parent, Socket, Offset, FRotator::ZeroRotator, FVector(Scale), EAttachLocation::KeepRelativeOffset, false, EPSCPoolMethod::None, true);
		}
		return nullptr;
	}

	UFXSystemComponent* AttachSparks(USceneComponent* Parent, FName Socket, const FVector& Offset, float Scale)
	{
		if (!Parent) return nullptr;
		if (UNiagaraSystem* S = Ns(TEXT("NS_EmberTrail")))
		{
			return UNiagaraFunctionLibrary::SpawnSystemAttached(S, Parent, Socket, Offset, FRotator::ZeroRotator, FVector(Scale), EAttachLocation::KeepRelativeOffset, false, ENCPoolMethod::None, true, true);
		}
		if (UParticleSystem* P = TwAssets::Cascade(TEXT("P_Sparks")))
		{
			return UGameplayStatics::SpawnEmitterAttached(P, Parent, Socket, Offset, FRotator::ZeroRotator, FVector(Scale), EAttachLocation::KeepRelativeOffset, false, EPSCPoolMethod::None, true);
		}
		return nullptr;
	}

	void Sound(UWorld* World, const TCHAR* Name, const FVector& Loc, float Volume, float Pitch)
	{
		if (USoundBase* S = TwAssets::Sound(Name))
		{
			UGameplayStatics::PlaySoundAtLocation(World, S, Loc, Volume, Pitch);
		}
	}

	void Sound2D(UWorld* World, const TCHAR* Name, float Volume, float Pitch)
	{
		if (USoundBase* S = TwAssets::Sound(Name))
		{
			UGameplayStatics::PlaySound2D(World, S, Volume, Pitch);
		}
	}

	void LightFlash(UWorld* World, const FVector& Loc, const FLinearColor& Color, float Intensity, float Radius, float Duration)
	{
		if (!World) return;
		FActorSpawnParameters P;
		P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		APointLight* L = World->SpawnActor<APointLight>(Loc, FRotator::ZeroRotator, P);
		if (!L) return;
		L->SetMobility(EComponentMobility::Movable);
		UPointLightComponent* C = L->PointLightComponent;
		C->SetIntensityUnits(ELightUnits::Unitless);
		C->SetIntensity(Intensity);
		C->SetLightColor(Color);
		C->SetAttenuationRadius(Radius);
		C->SetCastShadows(false);
		L->SetLifeSpan(Duration);
		// fade out
		TWeakObjectPtr<UPointLightComponent> Weak(C);
		const float Start = World->GetTimeSeconds();
		TSharedRef<FTimerHandle> H = MakeShared<FTimerHandle>();
		TWeakObjectPtr<UWorld> WeakWorld(World);
		World->GetTimerManager().SetTimer(*H, FTimerDelegate::CreateLambda([Weak, Start, Duration, Intensity, WeakWorld, H]()
		{
			UWorld* W = WeakWorld.Get();
			if (!W) return;
			const float A = FMath::Clamp((W->GetTimeSeconds() - Start) / Duration, 0.f, 1.f);
			if (!Weak.IsValid() || A >= 1.f) { W->GetTimerManager().ClearTimer(*H); return; }
			Weak->SetIntensity(Intensity * (1.f - A) * (1.f - A));
		}), 0.03f, true);
	}
}
