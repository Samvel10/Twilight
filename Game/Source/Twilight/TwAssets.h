#pragma once

#include "CoreMinimal.h"
#include "Fonts/SlateFontInfo.h"

class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class USoundBase;
class UNiagaraSystem;
class UParticleSystem;
class UAnimSequence;
class USkeletalMesh;
class UObject;

/** Central place for asset paths + safe loading with fallbacks (so a missing asset never crashes the game). */
namespace TwAssets
{
	/** Paths that already failed once (avoid repeated synchronous LoadPackage + flush). */
	TSet<FString>& MissingPaths();

	template<typename T>
	T* Load(const TCHAR* Path)
	{
		TSet<FString>& Missing = MissingPaths();
		if (Missing.Contains(Path)) return nullptr;
		T* Obj = LoadObject<T>(nullptr, Path, nullptr, LOAD_NoWarn | LOAD_Quiet);
		if (!Obj) Missing.Add(Path);
		return Obj;
	}

	UStaticMesh* Sphere();
	UStaticMesh* Cube();
	UStaticMesh* Cone();
	UStaticMesh* Cylinder();
	UStaticMesh* Plane();

	/** Our material by short name (e.g. "MI_VishapSkin"), falling back to the engine basic shape material. */
	UMaterialInterface* Material(const TCHAR* Name);
	/** Basic shape material that has a "Color" vector parameter. */
	UMaterialInterface* BasicMaterial();
	UMaterialInstanceDynamic* MakeColored(UObject* Outer, const FLinearColor& Color, const TCHAR* PreferredMaterial = nullptr);

	USoundBase* Sound(const TCHAR* Name);
	UNiagaraSystem* Niagara(const TCHAR* Path);
	UParticleSystem* Cascade(const TCHAR* Name);
	UAnimSequence* Anim(const TCHAR* Path);
	USkeletalMesh* Manny();

	/** Armenian-capable fonts (Noto) loaded straight from the TTF files in Content/Fonts. */
	FSlateFontInfo Font(float Size, bool bSerif = false, bool bBold = true);
}
