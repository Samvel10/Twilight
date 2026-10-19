#pragma once

#include "CoreMinimal.h"

class AActor;

/** Scatters the highlands kit's grass tufts and wild flowers (CC-BY scans/cards) over a rectangle as HISMs. */
namespace TwGrass
{
	/** Density in clumps per m^2; HeightFn returns world Z (cm) at X,Y; Keep(X,Y) may veto spots (paths, the lake). Returns instance count. */
	int32 Scatter(AActor* Owner, const FVector2D& Center, const FVector2D& HalfSize, float Density, TFunctionRef<float(float, float)> HeightFn,
		int32 Seed, float FlowerShare = 0.04f, TFunction<bool(float, float)> Keep = nullptr, float CullEnd = 4500.f);
}
