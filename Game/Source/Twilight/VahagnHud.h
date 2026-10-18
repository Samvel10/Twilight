#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class AVahagnPlayerController;

/** Whole UI for the Vahagn game: painted in-game HUD + Slate menus (Armenian text, Noto fonts). */
class SVahagnHud : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SVahagnHud) {}
		SLATE_ARGUMENT(TWeakObjectPtr<AVahagnPlayerController>, Owner)
	SLATE_END_ARGS()

	void Construct(const FArguments& Args);

	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geo, const FSlateRect& Cull, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const override;
	virtual bool SupportsKeyboardFocus() const override { return true; }

private:
	TSharedRef<SWidget> MakeMenu();
	TSharedRef<SWidget> MakeControls();
	TSharedRef<SWidget> MakePause();
	TSharedRef<SWidget> MakeEnd();
	TSharedRef<SWidget> MakeButton(const TAttribute<FText>& Label, TFunction<void()> OnClick, bool bPrimary = false);
	EVisibility VisFor(uint8 Screen) const;

	void PaintGameplay(const FGeometry& Geo, FSlateWindowElementList& Out, int32 Layer) const;

	TWeakObjectPtr<AVahagnPlayerController> Owner;
};
