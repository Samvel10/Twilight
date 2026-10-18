#include "TwUi.h"
#include "TwAssets.h"

#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "Rendering/DrawElements.h"
#include "Rendering/DrawElementTypes.h"
#include "Rendering/SlateRenderer.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"

namespace TwUi
{
	const FLinearColor Ember(1.f, 0.55f, 0.18f);
	const FLinearColor Gold(1.f, 0.83f, 0.45f);
	const FLinearColor Blood(0.95f, 0.16f, 0.1f);
	const FLinearColor Cream(1.f, 0.95f, 0.88f);

	static const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("WhiteBrush"); }

	void Box(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FVector2D& Size, const FLinearColor& C)
	{
		FSlateDrawElement::MakeBox(Out, Layer, Geo.ToPaintGeometry(FVector2f(Size), FSlateLayoutTransform(FVector2f(Pos))), White(), ESlateDrawEffect::None, C);
	}

	void Text(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FText& T, const FSlateFontInfo& F, const FLinearColor& C, float Align, bool bShadow)
	{
		const TSharedRef<FSlateFontMeasure> M = FSlateApplication::Get().GetRenderer()->GetFontMeasureService();
		const FVector2D Sz = M->Measure(T, F);
		const FVector2D P(Pos.X - Sz.X * Align, Pos.Y);
		if (bShadow)
		{
			FSlateDrawElement::MakeText(Out, Layer, Geo.ToPaintGeometry(FVector2f(Sz), FSlateLayoutTransform(FVector2f(P + FVector2D(2, 2)))), T, F, ESlateDrawEffect::None, FLinearColor(0, 0, 0, C.A * 0.75f));
		}
		FSlateDrawElement::MakeText(Out, Layer + 1, Geo.ToPaintGeometry(FVector2f(Sz), FSlateLayoutTransform(FVector2f(P))), T, F, ESlateDrawEffect::None, C);
	}

	void Lines(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const TArray<FVector2f>& Pts, const FLinearColor& C, float Thick)
	{
		FSlateDrawElement::MakeLines(Out, Layer, Geo.ToPaintGeometry(), Pts, ESlateDrawEffect::None, C, true, Thick);
	}

	void Bar(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FVector2D& Size, float Frac, const FLinearColor& A, const FLinearColor& B, bool bRightToLeft)
	{
		Box(Out, Layer, Geo, Pos - FVector2D(2, 2), Size + FVector2D(4, 4), FLinearColor(0, 0, 0, 0.55f));
		Box(Out, Layer + 1, Geo, Pos, Size, FLinearColor(1, 1, 1, 0.07f));
		const float W = Size.X * FMath::Clamp(Frac, 0.f, 1.f);
		if (W > 0.5f)
		{
			const FVector2D P = bRightToLeft ? FVector2D(Pos.X + Size.X - W, Pos.Y) : Pos;
			Box(Out, Layer + 2, Geo, P, FVector2D(W, Size.Y), A);
			Box(Out, Layer + 3, Geo, P, FVector2D(W, Size.Y * 0.38f), B);
		}
	}

	void EdgeGlow(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Size, const FLinearColor& C, float W)
	{
		const FLinearColor Z(C.R, C.G, C.B, 0.f);
		auto G = [&](const FVector2D& Pos, const FVector2D& Sz, const FLinearColor& A, const FLinearColor& B, EOrientation O, float Len)
		{
			TArray<FSlateGradientStop> Stops;
			Stops.Add(FSlateGradientStop(FVector2D(0, 0), A));
			Stops.Add(FSlateGradientStop(O == Orient_Vertical ? FVector2D(Len, 0) : FVector2D(0, Len), B));
			FSlateDrawElement::MakeGradient(Out, Layer, Geo.ToPaintGeometry(FVector2f(Sz), FSlateLayoutTransform(FVector2f(Pos))), Stops, O);
		};
		G(FVector2D(0, 0), FVector2D(W, Size.Y), C, Z, Orient_Vertical, W);
		G(FVector2D(Size.X - W, 0), FVector2D(W, Size.Y), Z, C, Orient_Vertical, W);
		G(FVector2D(0, 0), FVector2D(Size.X, W), C, Z, Orient_Horizontal, W);
		G(FVector2D(0, Size.Y - W), FVector2D(Size.X, W), Z, C, Orient_Horizontal, W);
	}

	TSharedRef<SWidget> Button(const TAttribute<FText>& Label, TFunction<void()> OnClick, bool bPrimary, float Width)
	{
		TSharedPtr<SButton> Btn;
		TSharedRef<SWidget> W =
			SNew(SBox).WidthOverride(Width).HeightOverride(62.f).Padding(FMargin(0, 5))
			[
				SAssignNew(Btn, SButton)
				.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
				.ContentPadding(0)
				.OnClicked_Lambda([OnClick]() { OnClick(); return FReply::Handled(); })
			];
		TWeakPtr<SButton> WeakBtn = Btn;
		Btn->SetContent(
			SNew(SBorder)
			.BorderImage(White())
			.BorderBackgroundColor_Lambda([WeakBtn, bPrimary]()
			{
				const TSharedPtr<SButton> B = WeakBtn.Pin();
				const bool bHot = B.IsValid() && (B->IsHovered() || B->HasKeyboardFocus());
				if (bHot) return FSlateColor(FLinearColor(1.f, 0.45f, 0.12f, 0.92f));
				return FSlateColor(bPrimary ? FLinearColor(0.55f, 0.16f, 0.06f, 0.75f) : FLinearColor(0.f, 0.f, 0.f, 0.5f));
			})
			.HAlign(HAlign_Center).VAlign(VAlign_Center)
			[
				SNew(STextBlock)
				.Text(Label)
				.Font(TwAssets::Font(21.f, false, true))
				.ColorAndOpacity(Cream)
				.ShadowOffset(FVector2D(1.5f, 1.5f))
				.ShadowColorAndOpacity(FLinearColor(0, 0, 0, 0.7f))
			]);
		return W;
	}

	TSharedRef<SWidget> Title(const FText& Main, const FText& Sub, const FText& Blurb, const FLinearColor& Color)
	{
		return SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock).Text(Main).Font(TwAssets::Font(116.f, true, true)).ColorAndOpacity(Color)
				.ShadowOffset(FVector2D(0, 0)).ShadowColorAndOpacity(FLinearColor(1.f, 0.35f, 0.05f, 0.9f))
			]
			+ SVerticalBox::Slot().AutoHeight()[ SNew(STextBlock).Text(Sub).Font(TwAssets::Font(28.f, false, true)).ColorAndOpacity(Cream) ]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 16, 0, 22)
			[
				SNew(SBox).WidthOverride(540.f)
				[
					SNew(STextBlock).AutoWrapText(true).Text(Blurb).Font(TwAssets::Font(17.f, false, false)).ColorAndOpacity(FLinearColor(1.f, 0.9f, 0.8f, 0.85f))
				]
			];
	}
}
