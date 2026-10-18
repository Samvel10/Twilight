#include "VahagnHud.h"
#include "VahagnPlayerController.h"
#include "VahagnCharacter.h"
#include "VahagnGameMode.h"
#include "Vishap.h"
#include "TwAssets.h"
#include "TwUi.h"

#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Text/STextBlock.h"
#include "Widgets/Images/SImage.h"
#include "Styling/CoreStyle.h"
#include "Rendering/DrawElements.h"
#include "Fonts/FontMeasure.h"
#include "Framework/Application/SlateApplication.h"
#include "EngineUtils.h"

#define LOCTEXT_NAMESPACE "VahagnHud"

namespace
{
	const FLinearColor Ember(1.f, 0.55f, 0.18f);
	const FLinearColor Gold(1.f, 0.83f, 0.45f);
	const FLinearColor Blood(0.95f, 0.16f, 0.1f);
	const FLinearColor Ink(0.02f, 0.01f, 0.03f);
	const FLinearColor Cream(1.f, 0.95f, 0.88f);

	const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("WhiteBrush"); }

	FText TimeText(float Sec)
	{
		const int32 S = FMath::Max(0, FMath::CeilToInt(Sec));
		return FText::FromString(FString::Printf(TEXT("%02d:%02d"), S / 60, S % 60));
	}

	FText DifficultyName(EVahagnDifficulty D)
	{
		switch (D)
		{
		case EVahagnDifficulty::Easy: return LOCTEXT("Easy", "Հեշտ");
		case EVahagnDifficulty::Hard: return LOCTEXT("Hard", "Դժվար");
		default: return LOCTEXT("Normal", "Նորմալ");
		}
	}
}

void SVahagnHud::Construct(const FArguments& Args)
{
	Owner = Args._Owner;
	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SVahagnHud::VisFor, (uint8)EVahagnScreen::Menu)[ MakeMenu() ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SVahagnHud::VisFor, (uint8)EVahagnScreen::Controls)[ MakeControls() ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SVahagnHud::VisFor, (uint8)EVahagnScreen::Pause)[ MakePause() ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SVahagnHud::VisFor, (uint8)EVahagnScreen::End)[ MakeEnd() ] ]
	];
}

EVisibility SVahagnHud::VisFor(uint8 Screen) const
{
	const AVahagnPlayerController* PC = Owner.Get();
	return PC && (uint8)PC->GetScreen() == Screen ? EVisibility::Visible : EVisibility::Collapsed;
}

TSharedRef<SWidget> SVahagnHud::MakeButton(const TAttribute<FText>& Label, TFunction<void()> OnClick, bool bPrimary)
{
	TSharedPtr<SButton> Btn;
	TSharedRef<SWidget> W =
		SNew(SBox).WidthOverride(420.f).HeightOverride(64.f).Padding(FMargin(0, 6))
		[
			SAssignNew(Btn, SButton)
			.ButtonStyle(&FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("NoBorder"))
			.ContentPadding(0)
			.OnClicked_Lambda([OnClick]() { OnClick(); return FReply::Handled(); })
			.OnHovered_Lambda([this]() { if (AVahagnPlayerController* PC = Owner.Get()) {} })
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
			.Font(TwAssets::Font(22.f, false, true))
			.ColorAndOpacity(Cream)
			.ShadowOffset(FVector2D(1.5f, 1.5f))
			.ShadowColorAndOpacity(FLinearColor(0, 0, 0, 0.7f))
		]);
	return W;
}

TSharedRef<SWidget> SVahagnHud::MakeMenu()
{
	TWeakObjectPtr<AVahagnPlayerController> O = Owner;
	return SNew(SOverlay)
		+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Fill)
		[
			SNew(SBorder).BorderImage(White()).BorderBackgroundColor(FLinearColor(0.01f, 0.f, 0.02f, 0.55f)).Padding(FMargin(90.f, 60.f, 90.f, 60.f))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().FillHeight(1.f)[ SNew(SSpacer) ]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(STextBlock).Text(LOCTEXT("Chapter", "ԳԼՈՒԽ I · ԹՌԻՉՔ ԴԵՊԻ ԴԻՑԱԲԱՆՈՒԹՅԱՆ ԽՈՐՔԵՐԸ"))
					.Font(TwAssets::Font(16.f, false, true)).ColorAndOpacity(FLinearColor(1, 1, 1, 0.6f))
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
				[
					SNew(STextBlock).Text(LOCTEXT("Title", "ՎԱՀԱԳՆ"))
					.Font(TwAssets::Font(120.f, true, true)).ColorAndOpacity(Gold)
					.ShadowOffset(FVector2D(0, 0)).ShadowColorAndOpacity(FLinearColor(1.f, 0.35f, 0.05f, 0.9f))
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(STextBlock).Text(LOCTEXT("Sub", "Վ Ի Շ Ա Պ Ա Ք Ա Ղ"))
					.Font(TwAssets::Font(30.f, false, true)).ColorAndOpacity(Cream)
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 18, 0, 26)
				[
					SNew(SBox).WidthOverride(520.f)
					[
						SNew(STextBlock).AutoWrapText(true)
						.Text(LOCTEXT("Quote", "«Երկնէր երկին, երկնէր երկիր, երկնէր և ծովն ծիրանի…»\nԾիրանի ծովի եղեգից ծնված կրակե պատանին պետք է խոցի Մեծ վիշապին։"))
						.Font(TwAssets::Font(17.f, false, false)).ColorAndOpacity(FLinearColor(1.f, 0.9f, 0.8f, 0.85f))
					]
				]
				+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("Play", "ԽԱՂԱԼ"), [O]() { if (O.IsValid()) O->UiPlay(); }, true) ]
				+ SVerticalBox::Slot().AutoHeight()
				[
					MakeButton(TAttribute<FText>::CreateLambda([O]()
					{
						const AVahagnGameMode* GM = O.IsValid() ? O->Mode() : nullptr;
						return FText::Format(LOCTEXT("Diff", "ԴԺՎԱՐՈՒԹՅՈՒՆ՝ {0}"), DifficultyName(GM ? GM->GetDifficulty() : EVahagnDifficulty::Normal));
					}), [O]() { if (O.IsValid()) O->UiCycleDifficulty(); })
				]
				+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("Controls", "ԿԱՌԱՎԱՐՈՒՄ"), [O]() { if (O.IsValid()) O->UiControls(); }) ]
				+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("Hub", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiHub(); }) ]
				+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("Quit", "ԵԼՔ"), [O]() { if (O.IsValid()) O->UiQuit(); }) ]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 22, 0, 0)
				[
					SNew(STextBlock)
					.Text_Lambda([O]()
					{
						const AVahagnGameMode* GM = O.IsValid() ? O->Mode() : nullptr;
						return FText::Format(LOCTEXT("Best", "Ռեկորդ՝ {0}"), FText::AsNumber(GM ? GM->GetBestScore() : 0));
					})
					.Font(TwAssets::Font(16.f, false, false)).ColorAndOpacity(FLinearColor(1, 1, 1, 0.55f))
				]
				+ SVerticalBox::Slot().FillHeight(1.f)[ SNew(SSpacer) ]
			]
		];
}

TSharedRef<SWidget> SVahagnHud::MakeControls()
{
	TWeakObjectPtr<AVahagnPlayerController> O = Owner;
	auto Row = [](const FText& Key, const FText& What) -> TSharedRef<SWidget>
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().Padding(0, 6)
			[ SNew(SBox).WidthOverride(260.f)[ SNew(STextBlock).Text(Key).Font(TwAssets::Font(20.f, false, true)).ColorAndOpacity(Gold) ] ]
			+ SHorizontalBox::Slot().FillWidth(1.f).Padding(0, 6)
			[ SNew(STextBlock).Text(What).Font(TwAssets::Font(20.f, false, false)).ColorAndOpacity(Cream) ];
	};
	return SNew(SBorder).BorderImage(White()).BorderBackgroundColor(FLinearColor(0.01f, 0.f, 0.02f, 0.75f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
	[
		SNew(SBox).WidthOverride(900.f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 24)[ SNew(STextBlock).Text(LOCTEXT("CtlTitle", "ԿԱՌԱՎԱՐՈՒՄ")).Font(TwAssets::Font(54.f, true, true)).ColorAndOpacity(Gold) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k1", "Մկնիկ"), LOCTEXT("v1", "Նշանառություն և թռիչքի ուղղություն")) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k2", "W A S D"), LOCTEXT("v2", "Թռիչք առաջ, հետ, կողքեր")) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k3", "Space / Ctrl"), LOCTEXT("v3", "Վեր / վար")) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k4", "Shift"), LOCTEXT("v4", "Արագացում")) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k5", "Ձախ կոճակ"), LOCTEXT("v5", "Կրակե գնդակներ")) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k6", "Աջ կոճակ (պահել)"), LOCTEXT("v6", "Լիցքավորված հարված՝ պայթյունով")) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k7", "Q"), LOCTEXT("v7", "Արևի պոռթկում (երբ լիցքավորված է)")) ]
			+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k8", "Esc"), LOCTEXT("v8", "Դադար")) ]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 18, 0, 18)
			[
				SNew(STextBlock).AutoWrapText(true)
				.Text(LOCTEXT("Tip", "Խորհուրդ. վիշապի գլխին հասցված հարվածը կրկնակի վնաս է տալիս։ Սպանված վիշապներից մնացած կրակե գնդիկները բուժում են և լիցքավորում Արևի պոռթկումը։ Կրակե շնչից խուսափիր՝ կողք թռչելով։"))
				.Font(TwAssets::Font(17.f, false, false)).ColorAndOpacity(FLinearColor(1, 0.9f, 0.8f, 0.8f))
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left)[ MakeButton(LOCTEXT("Back", "ՀԵՏ"), [O]() { if (O.IsValid()) O->UiBack(); }, true) ]
		]
	];
}

TSharedRef<SWidget> SVahagnHud::MakePause()
{
	TWeakObjectPtr<AVahagnPlayerController> O = Owner;
	return SNew(SBorder).BorderImage(White()).BorderBackgroundColor(FLinearColor(0.f, 0.f, 0.f, 0.6f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 24)[ SNew(STextBlock).Text(LOCTEXT("Paused", "ԴԱԴԱՐ")).Font(TwAssets::Font(64.f, true, true)).ColorAndOpacity(Gold) ]
		+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("Resume", "ՇԱՐՈՒՆԱԿԵԼ"), [O]() { if (O.IsValid()) O->UiResume(); }, true) ]
		+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("Restart", "ՍԿՍԵԼ ՆՈՐԻՑ"), [O]() { if (O.IsValid()) O->UiRestart(); }) ]
		+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("ToMenu", "ԽԱՂԻ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiMenu(); }) ]
		+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("ToHub", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiHub(); }) ]
		+ SVerticalBox::Slot().AutoHeight()[ MakeButton(LOCTEXT("Quit2", "ԵԼՔ"), [O]() { if (O.IsValid()) O->UiQuit(); }) ]
	];
}

TSharedRef<SWidget> SVahagnHud::MakeEnd()
{
	TWeakObjectPtr<AVahagnPlayerController> O = Owner;
	return SNew(SBorder).BorderImage(White()).BorderBackgroundColor(FLinearColor(0.f, 0.f, 0.f, 0.55f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
	[
		SNew(SVerticalBox)
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
		[
			SNew(STextBlock)
			.Text_Lambda([O]() { return O.IsValid() && O->WasVictory() ? LOCTEXT("Win", "ՀԱՂԹԱՆԱԿ") : LOCTEXT("Lose", "ՊԱՐՏՈՒԹՅՈՒՆ"); })
			.ColorAndOpacity_Lambda([O]() { return FSlateColor(O.IsValid() && O->WasVictory() ? Gold : Blood); })
			.Font(TwAssets::Font(96.f, true, true))
			.ShadowOffset(FVector2D(0, 0)).ShadowColorAndOpacity(FLinearColor(1.f, 0.3f, 0.05f, 0.8f))
		]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 6, 0, 26)
		[
			SNew(STextBlock)
			.Text_Lambda([O]()
			{
				return O.IsValid() && O->WasVictory()
					? LOCTEXT("WinSub", "Մեծ վիշապը խոցված է։ Ծիրանի ծովը խաղաղվեց։")
					: LOCTEXT("LoseSub", "Վահագնի կրակը մարեց… բայց առասպելը շարունակվում է։");
			})
			.Font(TwAssets::Font(24.f, false, false)).ColorAndOpacity(Cream)
		]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 26)
		[
			SNew(STextBlock)
			.Text_Lambda([O]()
			{
				const AVahagnGameMode* GM = O.IsValid() ? O->Mode() : nullptr;
				if (!GM) return FText::GetEmpty();
				return FText::Format(LOCTEXT("Stats", "Միավոր՝ {0}     Վիշապներ՝ {1}     Ժամանակ՝ {2}     Ռեկորդ՝ {3}"),
					FText::AsNumber(GM->GetScore()), FText::AsNumber(GM->GetKills()), TimeText(GM->GetMatchTime()), FText::AsNumber(GM->GetBestScore()));
			})
			.Font(TwAssets::Font(22.f, false, true)).ColorAndOpacity(Gold)
		]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[ MakeButton(LOCTEXT("Again", "ԿՐԿԻՆ"), [O]() { if (O.IsValid()) O->UiRestart(); }, true) ]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[ MakeButton(LOCTEXT("ToMenu2", "ԽԱՂԻ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiMenu(); }) ]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[ MakeButton(LOCTEXT("ToHub2", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiHub(); }) ]
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[ MakeButton(LOCTEXT("Quit3", "ԵԼՔ"), [O]() { if (O.IsValid()) O->UiQuit(); }) ]
	];
}

// ======================================================================= painted HUD

namespace
{
	void Box(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FVector2D& Size, const FLinearColor& C)
	{
		FSlateDrawElement::MakeBox(Out, Layer, Geo.ToPaintGeometry(FVector2f(Size), FSlateLayoutTransform(FVector2f(Pos))), White(), ESlateDrawEffect::None, C);
	}

	void Text(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FText& T, const FSlateFontInfo& InF, const FLinearColor& C, float Align = 0.f, bool bShadow = true)
	{
		FSlateFontInfo F = InF;
		F.OutlineSettings.OutlineSize = FMath::Max(1, FMath::RoundToInt(F.Size / 18.f));
		F.OutlineSettings.OutlineColor = FLinearColor(0.06f, 0.01f, 0.02f, 0.8f * C.A);
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

	void Bar(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geo, const FVector2D& Pos, const FVector2D& Size, float Frac, const FLinearColor& A, const FLinearColor& B)
	{
		Box(Out, Layer, Geo, Pos - FVector2D(2, 2), Size + FVector2D(4, 4), FLinearColor(0, 0, 0, 0.55f));
		Box(Out, Layer + 1, Geo, Pos, Size, FLinearColor(1, 1, 1, 0.07f));
		const float W = Size.X * FMath::Clamp(Frac, 0.f, 1.f);
		if (W > 0.5f)
		{
			// two-tone fill for a "molten" look
			Box(Out, Layer + 2, Geo, Pos, FVector2D(W, Size.Y), A);
			Box(Out, Layer + 3, Geo, Pos, FVector2D(W, Size.Y * 0.38f), B);
		}
	}
}

int32 SVahagnHud::OnPaint(const FPaintArgs& Args, const FGeometry& Geo, const FSlateRect& Cull, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const
{
	const AVahagnPlayerController* PC = Owner.Get();
	if (PC && (PC->GetScreen() == EVahagnScreen::None || PC->GetScreen() == EVahagnScreen::Pause || PC->GetScreen() == EVahagnScreen::End))
	{
		PaintGameplay(Geo, Out, Layer);
	}
	return SCompoundWidget::OnPaint(Args, Geo, Cull, Out, Layer + 40, Style, bParentEnabled);
}

void SVahagnHud::PaintGameplay(const FGeometry& Geo, FSlateWindowElementList& Out, int32 L) const
{
	AVahagnPlayerController* PC = Owner.Get();
	AVahagnCharacter* H = PC ? PC->Hero() : nullptr;
	AVahagnGameMode* GM = PC ? PC->Mode() : nullptr;
	if (!H || !GM) return;

	const FVector2D Size = FVector2D(Geo.GetLocalSize());
	const float S = Size.Y / 1080.f;
	const FVector2D C = Size * 0.5f;
	const float Now = PC->GetWorld()->GetRealTimeSeconds();
	const bool bEnded = PC->GetScreen() == EVahagnScreen::End;

	// damage vignette
	if (H->GetDamageFlash() > 0.01f)
	{
		TwUi::EdgeGlow(Out, L, Geo, Size, FLinearColor(0.85f, 0.05f, 0.02f, H->GetDamageFlash() * 0.6f), 260.f * S);
	}
	if (H->GetHealth() < 30.f && !H->IsDead())
	{
		const float A = (0.35f + 0.2f * FMath::Sin(Now * 6.f)) * (1.f - H->GetHealth() / 30.f);
		TwUi::EdgeGlow(Out, L, Geo, Size, FLinearColor(0.6f, 0.f, 0.f, A), 380.f * S);
	}
	if (bEnded) return;

	const EVahagnMatch MS = GM->GetMatchState();

	// ---- off-screen / on-screen vishap markers
	for (TActorIterator<AVishap> It(PC->GetWorld()); It; ++It)
	{
		AVishap* V = *It;
		if (!V->IsAlive()) continue;
		const FVector W = V->GetHeadLocation();
		FVector2D Scr = FVector2D::ZeroVector;
		const bool bOn = PC->ProjectWorldLocationToScreen(W, Scr, true);
		const float DPI = Geo.GetAccumulatedLayoutTransform().GetScale();
		Scr /= FMath::Max(DPI, 0.01f);
		const bool bInside = bOn && Scr.X > 40 * S && Scr.X < Size.X - 40 * S && Scr.Y > 40 * S && Scr.Y < Size.Y - 40 * S;
		const FLinearColor Col = V->IsBoss() ? Blood : Ember;
		if (bInside)
		{
			// small health bar over damaged vishaps
			if (V->GetHealth() < V->GetMaxHealth() && !V->IsBoss())
			{
				const FVector2D BP(Scr.X - 40 * S, Scr.Y - 60 * S);
				Bar(Out, L + 2, Geo, BP, FVector2D(80 * S, 6 * S), V->GetHealth() / V->GetMaxHealth(), Blood, FLinearColor(1, 0.5f, 0.3f, 0.8f));
			}
		}
		else
		{
			// edge arrow pointing toward the threat
			FVector2D Dir;
			if (bOn) Dir = Scr - C;
			else
			{
				FVector CamLoc; FRotator CamRot;
				PC->GetPlayerViewPoint(CamLoc, CamRot);
				const FVector Lc = CamRot.UnrotateVector(W - CamLoc); // x fwd, y right, z up
				Dir = FVector2D(Lc.Y, -Lc.Z);
			}
			if (Dir.IsNearlyZero()) Dir = FVector2D(0, 1);
			Dir.Normalize();
			const float Mx = C.X - 70 * S, My = C.Y - 70 * S;
			const float K = FMath::Min(Mx / FMath::Max(FMath::Abs(Dir.X), 1e-3f), My / FMath::Max(FMath::Abs(Dir.Y), 1e-3f));
			const FVector2D P = C + Dir * K;
			const FVector2D N(-Dir.Y, Dir.X);
			const float Sz = (V->IsBoss() ? 30.f : 18.f) * S;
			TArray<FVector2f> Tri = { FVector2f(P + Dir * Sz), FVector2f(P - Dir * Sz * 0.5f + N * Sz * 0.7f), FVector2f(P - Dir * Sz * 0.5f - N * Sz * 0.7f), FVector2f(P + Dir * Sz) };
			Lines(Out, L + 3, Geo, Tri, Col, 3.f * S);
		}
	}

	// ---- crosshair
	{
		const bool bLocked = H->GetAimTarget() != nullptr;
		const FLinearColor Cc = bLocked ? FLinearColor(1.f, 0.35f, 0.15f, 0.95f) : FLinearColor(1, 1, 1, 0.85f);
		const float G = (bLocked ? 7.f : 10.f) * S, Ln = 9.f * S;
		Lines(Out, L + 5, Geo, { FVector2f(C + FVector2D(-G - Ln, 0)), FVector2f(C + FVector2D(-G, 0)) }, Cc, 2.f * S);
		Lines(Out, L + 5, Geo, { FVector2f(C + FVector2D(G, 0)), FVector2f(C + FVector2D(G + Ln, 0)) }, Cc, 2.f * S);
		Lines(Out, L + 5, Geo, { FVector2f(C + FVector2D(0, -G - Ln)), FVector2f(C + FVector2D(0, -G)) }, Cc, 2.f * S);
		Lines(Out, L + 5, Geo, { FVector2f(C + FVector2D(0, G)), FVector2f(C + FVector2D(0, G + Ln)) }, Cc, 2.f * S);
		Box(Out, L + 5, Geo, C - FVector2D(1.5f, 1.5f) * S, FVector2D(3, 3) * S, Cc);
		// charge ring
		if (H->GetCharge() > 0.01f)
		{
			TArray<FVector2f> Arc;
			const int32 Seg = 40;
			const float R = 26.f * S;
			for (int32 i = 0; i <= FMath::CeilToInt(Seg * H->GetCharge()); ++i)
			{
				const float A = -PI * 0.5f + 2.f * PI * i / Seg;
				Arc.Add(FVector2f(C + FVector2D(FMath::Cos(A), FMath::Sin(A)) * R));
			}
			Lines(Out, L + 5, Geo, Arc, H->GetCharge() >= 1.f ? Gold : Ember, 3.f * S);
		}
		// hit marker
		if (H->GetHitMarker() > 0.f)
		{
			const float A = FMath::Clamp(H->GetHitMarker(), 0.f, 1.f);
			const float a = 8.f * S, b = 16.f * S;
			const FLinearColor Hc(1.f, 0.9f, 0.6f, A);
			Lines(Out, L + 6, Geo, { FVector2f(C + FVector2D(-b, -b)), FVector2f(C + FVector2D(-a, -a)) }, Hc, 2.5f * S);
			Lines(Out, L + 6, Geo, { FVector2f(C + FVector2D(b, -b)), FVector2f(C + FVector2D(a, -a)) }, Hc, 2.5f * S);
			Lines(Out, L + 6, Geo, { FVector2f(C + FVector2D(-b, b)), FVector2f(C + FVector2D(-a, a)) }, Hc, 2.5f * S);
			Lines(Out, L + 6, Geo, { FVector2f(C + FVector2D(b, b)), FVector2f(C + FVector2D(a, a)) }, Hc, 2.5f * S);
		}
	}

	// ---- top: timer + wave / boss bar
	Text(Out, L + 6, Geo, FVector2D(C.X, 22 * S), TimeText(GM->GetTimeLeft()), TwAssets::Font(34 * S, false, true), GM->GetTimeLeft() < 60.f ? Blood : Cream, 0.5f);
	if (AVishap* B = GM->GetBoss(); B && B->IsAlive())
	{
		const FVector2D BS(820 * S, 16 * S);
		const FVector2D BP(C.X - BS.X * 0.5f, 104 * S);
		Text(Out, L + 6, Geo, FVector2D(C.X, 72 * S), LOCTEXT("BossName", "ՄԵԾ ՎԻՇԱՊ"), TwAssets::Font(22 * S, true, true), Blood, 0.5f);
		Bar(Out, L + 6, Geo, BP, BS, B->GetHealth() / B->GetMaxHealth(), FLinearColor(0.75f, 0.05f, 0.03f), FLinearColor(1.f, 0.35f, 0.2f, 0.9f));
	}
	else if (MS == EVahagnMatch::Playing && GM->GetWave() >= 1 && GM->GetWave() <= 3)
	{
		Text(Out, L + 6, Geo, FVector2D(C.X, 72 * S), FText::Format(LOCTEXT("Wave", "ԱԼԻՔ {0} / {1}   ·   ՎԻՇԱՊՆԵՐ՝ {2}"), FText::AsNumber(GM->GetWave()), FText::AsNumber(GM->GetNumWaves()), FText::AsNumber(GM->AliveVishaps())), TwAssets::Font(18 * S, false, true), FLinearColor(1, 0.9f, 0.8f, 0.8f), 0.5f);
	}

	// ---- top-left: score
	Text(Out, L + 6, Geo, FVector2D(40 * S, 28 * S), FText::Format(LOCTEXT("Score", "ՄԻԱՎՈՐ  {0}"), FText::AsNumber(GM->GetScore())), TwAssets::Font(22 * S, false, true), Gold);
	Text(Out, L + 6, Geo, FVector2D(40 * S, 60 * S), FText::Format(LOCTEXT("Kills", "Խոցված վիշապներ՝ {0}"), FText::AsNumber(GM->GetKills())), TwAssets::Font(16 * S, false, false), FLinearColor(1, 1, 1, 0.7f));

	// ---- bottom-left: vitals
	const FVector2D V0(48 * S, Size.Y - 150 * S);
	Text(Out, L + 6, Geo, V0 + FVector2D(0, -30 * S), LOCTEXT("HP", "ԿՅԱՆՔ"), TwAssets::Font(15 * S, false, true), Cream);
	Bar(Out, L + 6, Geo, V0, FVector2D(380 * S, 18 * S), H->GetHealth() / H->GetMaxHealth(), FLinearColor(0.9f, 0.25f, 0.05f), FLinearColor(1.f, 0.75f, 0.35f, 0.9f));
	Text(Out, L + 6, Geo, V0 + FVector2D(0, 30 * S), LOCTEXT("Boost", "ԱՐԱԳԱՑՈՒՄ"), TwAssets::Font(13 * S, false, true), FLinearColor(1, 1, 1, 0.7f));
	Bar(Out, L + 6, Geo, V0 + FVector2D(0, 54 * S), FVector2D(260 * S, 8 * S), H->GetBoostEnergy() / 100.f, FLinearColor(0.35f, 0.75f, 1.f), FLinearColor(0.8f, 0.95f, 1.f, 0.8f));
	// Nova
	{
		const bool bReady = H->GetNova() >= 100.f;
		const FVector2D NP(48 * S, Size.Y - 62 * S);
		const float Pulse = bReady ? 0.75f + 0.25f * FMath::Sin(Now * 7.f) : 1.f;
		Text(Out, L + 6, Geo, NP + FVector2D(0, -24 * S), bReady ? LOCTEXT("NovaReady", "ԱՐԵՎԻ ՊՈՌԹԿՈՒՄԸ ՊԱՏՐԱՍՏ Է · Q") : LOCTEXT("Nova", "ԱՐԵՎԻ ՊՈՌԹԿՈՒՄ"), TwAssets::Font(13 * S, false, true), bReady ? Gold * Pulse : FLinearColor(1, 1, 1, 0.7f));
		Bar(Out, L + 6, Geo, NP, FVector2D(260 * S, 8 * S), H->GetNova() / 100.f, FLinearColor(1.f, 0.7f, 0.15f) * Pulse, FLinearColor(1.f, 0.95f, 0.6f, 0.9f));
	}

	// ---- intro countdown
	if (MS == EVahagnMatch::Intro)
	{
		const int32 N = FMath::CeilToInt(GM->GetIntroLeft());
		Text(Out, L + 8, Geo, FVector2D(C.X, C.Y - 160 * S), FText::AsNumber(FMath::Max(1, N)), TwAssets::Font(110 * S, true, true), Gold, 0.5f);
	}

	// ---- announcements
	FText At, As; float Age = 0.f;
	if (GM->GetAnnouncement(At, As, Age))
	{
		const float A = FMath::Clamp(Age / 0.25f, 0.f, 1.f) * FMath::Clamp((3.2f - Age) / 0.6f, 0.f, 1.f);
		const float Y = C.Y - 300 * S + (1.f - FMath::Clamp(Age / 0.25f, 0.f, 1.f)) * 20 * S;
		const float TitleSize = At.ToString().Len() > 26 ? 30.f : 56.f; // long quotes must fit the screen
		Text(Out, L + 8, Geo, FVector2D(C.X, Y), At, TwAssets::Font(TitleSize * S, true, true), FLinearColor(Gold.R, Gold.G, Gold.B, A), 0.5f);
		if (!As.IsEmpty()) Text(Out, L + 8, Geo, FVector2D(C.X, Y + 80 * S), As, TwAssets::Font(22 * S, false, false), FLinearColor(Cream.R, Cream.G, Cream.B, A * 0.9f), 0.5f);
	}

	// ---- controls hint for the first seconds
	if (MS == EVahagnMatch::Intro || (MS == EVahagnMatch::Playing && GM->GetMatchTime() < 14.f))
	{
		Text(Out, L + 6, Geo, FVector2D(Size.X - 40 * S, Size.Y - 50 * S),
			LOCTEXT("Hint", "Ձախ կոճակ՝ կրակ · Աջ կոճակ՝ լիցքավորված հարված · Shift՝ արագացում · Space/Ctrl՝ վեր/վար · Q՝ պոռթկում · Esc՝ դադար"),
			TwAssets::Font(15 * S, false, false), FLinearColor(1, 1, 1, 0.75f), 1.f);
	}
}

#undef LOCTEXT_NAMESPACE
