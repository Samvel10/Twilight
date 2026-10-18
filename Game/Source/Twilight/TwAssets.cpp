#include "TwAssets.h"
#include "Twilight.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "NiagaraSystem.h"
#include "Particles/ParticleSystem.h"
#include "Animation/AnimSequence.h"
#include "Fonts/CompositeFont.h"
#include "Misc/Paths.h"

namespace TwAssets
{
	UStaticMesh* Sphere()   { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = Load<UStaticMesh>(TEXT("/Engine/BasicShapes/Sphere.Sphere")); return M.Get(); }
	UStaticMesh* Cube()     { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = Load<UStaticMesh>(TEXT("/Engine/BasicShapes/Cube.Cube")); return M.Get(); }
	UStaticMesh* Cone()     { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = Load<UStaticMesh>(TEXT("/Engine/BasicShapes/Cone.Cone")); return M.Get(); }
	UStaticMesh* Cylinder() { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = Load<UStaticMesh>(TEXT("/Engine/BasicShapes/Cylinder.Cylinder")); return M.Get(); }
	UStaticMesh* Plane()    { static TWeakObjectPtr<UStaticMesh> M; if (!M.IsValid()) M = Load<UStaticMesh>(TEXT("/Engine/BasicShapes/Plane.Plane")); return M.Get(); }

	UMaterialInterface* BasicMaterial()
	{
		static TWeakObjectPtr<UMaterialInterface> M;
		if (!M.IsValid()) M = Load<UMaterialInterface>(TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		return M.Get();
	}

	UMaterialInterface* Material(const TCHAR* Name)
	{
		const FString P = FString::Printf(TEXT("/Game/Twilight/Materials/%s.%s"), Name, Name);
		if (UMaterialInterface* M = Load<UMaterialInterface>(*P)) return M;
		UE_LOG(LogTwilight, Warning, TEXT("Material %s missing, using basic material"), Name);
		return BasicMaterial();
	}

	UMaterialInstanceDynamic* MakeColored(UObject* Outer, const FLinearColor& Color, const TCHAR* PreferredMaterial)
	{
		UMaterialInterface* Base = PreferredMaterial ? Material(PreferredMaterial) : BasicMaterial();
		UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(Base, Outer);
		if (MID)
		{
			MID->SetVectorParameterValue(TEXT("Color"), Color);
			MID->SetVectorParameterValue(TEXT("BaseColor"), Color);
		}
		return MID;
	}

	USoundBase* Sound(const TCHAR* Name)
	{
		const FString P = FString::Printf(TEXT("/Game/Twilight/Audio/%s.%s"), Name, Name);
		USoundBase* S = Load<USoundBase>(*P);
		if (!S) UE_LOG(LogTwilight, Verbose, TEXT("Sound %s missing"), Name);
		return S;
	}

	UNiagaraSystem* Niagara(const TCHAR* Path) { return Load<UNiagaraSystem>(Path); }

	UParticleSystem* Cascade(const TCHAR* Name)
	{
		const FString P = FString::Printf(TEXT("/Game/StarterContent/Particles/%s.%s"), Name, Name);
		return Load<UParticleSystem>(*P);
	}

	UAnimSequence* Anim(const TCHAR* Path) { return Load<UAnimSequence>(Path); }

	USkeletalMesh* Manny()
	{
		return Load<USkeletalMesh>(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	}

	FSlateFontInfo Font(float Size, bool bSerif, bool bBold)
	{
		static TSharedPtr<const FCompositeFont> Fonts[4];
		const int32 Idx = (bSerif ? 2 : 0) + (bBold ? 1 : 0);
		if (!Fonts[Idx].IsValid())
		{
			const TCHAR* File = bSerif ? (bBold ? TEXT("NotoSerifArmenian-Black.ttf") : TEXT("NotoSerifArmenian-Bold.ttf"))
			                           : (bBold ? TEXT("NotoSansArmenian-Bold.ttf") : TEXT("NotoSansArmenian-Regular.ttf"));
			const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir() / TEXT("Fonts") / File);
			Fonts[Idx] = MakeShared<FStandaloneCompositeFont>(NAME_None, Path, EFontHinting::Default, EFontLoadingPolicy::LazyLoad);
		}
		return FSlateFontInfo(Fonts[Idx], Size);
	}
}
