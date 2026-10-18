#pragma once

#include "CoreMinimal.h"

class UWorld;
class USceneComponent;
class UFXSystemComponent;
class USoundBase;

/** Visual/audio effect helpers. Every call is safe if an asset is missing. */
namespace TwFx
{
	enum class EFx : uint8
	{
		FireballImpact,
		BigExplosion,
		VishapDeath,
		Splash,
		Sparks,
		Smoke,
		Nova,
		MuzzleFlash,
	};

	/** One-shot effect at a location. */
	void Burst(UWorld* World, EFx Type, const FVector& Location, float Scale = 1.f, const FRotator& Rot = FRotator::ZeroRotator);

	/** Attached looping flame (hero aura, fireball core, vishap breath). */
	UFXSystemComponent* AttachFlame(USceneComponent* Parent, FName Socket, const FVector& Offset, float Scale);
	/** Attached trail-ish smoke/sparks. */
	UFXSystemComponent* AttachSparks(USceneComponent* Parent, FName Socket, const FVector& Offset, float Scale);

	void Sound(UWorld* World, const TCHAR* Name, const FVector& Location, float Volume = 1.f, float Pitch = 1.f);
	void Sound2D(UWorld* World, const TCHAR* Name, float Volume = 1.f, float Pitch = 1.f);

	/** A transient short-lived point light flash. */
	void LightFlash(UWorld* World, const FVector& Location, const FLinearColor& Color, float Intensity, float Radius, float Duration);
}
