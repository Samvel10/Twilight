#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class AHaykPlayerController;

class SHaykHud : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SHaykHud) {}
		SLATE_ARGUMENT(TWeakObjectPtr<AHaykPlayerController>, Owner)
	SLATE_END_ARGS()

	void Construct(const FArguments& Args);
	virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geo, const FSlateRect& Cull, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const override;
	virtual bool SupportsKeyboardFocus() const override { return true; }

private:
	EVisibility VisFor(uint8 Screen) const;
	void PaintDuel(const FGeometry& Geo, FSlateWindowElementList& Out, int32 Layer) const;
	TWeakObjectPtr<AHaykPlayerController> Owner;
};
