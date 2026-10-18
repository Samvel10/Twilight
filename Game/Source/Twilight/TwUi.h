#pragma once

#include "CoreMinimal.h"
#include "Widgets/SWidget.h"

class FSlateWindowElementList;
struct FGeometry;
struct FSlateFontInfo;

/** Small shared UI kit: painted HUD primitives + styled menu buttons/titles. */
namespace TwUi
{
	extern const FLinearColor Ember;
	extern const FLinearColor Gold;
	extern const FLinearColor Blood;
	extern const FLinearColor Cream;

	void Box(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FVector2D& Size, const FLinearColor& C);
	void Text(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FText& T, const FSlateFontInfo& F, const FLinearColor& C, float Align = 0.f, bool bShadow = true);
	void Lines(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const TArray<FVector2f>& Pts, const FLinearColor& C, float Thick);
	void Bar(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FVector2D& Size, float Frac, const FLinearColor& A, const FLinearColor& B, bool bRightToLeft = false);

	/** Soft coloured vignette fading in from all four screen edges. */
	void EdgeGlow(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Size, const FLinearColor& C, float Width);

	TSharedRef<SWidget> Button(const TAttribute<FText>& Label, TFunction<void()> OnClick, bool bPrimary = false, float Width = 440.f);
	TSharedRef<SWidget> Title(const FText& Main, const FText& Sub, const FText& Blurb, const FLinearColor& Color);
}
