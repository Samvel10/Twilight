#include "HaykHud.h"
#include "HaykPlayerController.h"
#include "HaykGameMode.h"
#include "HaykArcher.h"
#include "HaykArrow.h"
#include "TwAssets.h"
#include "TwUi.h"

#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"
#include "Kismet/GameplayStatics.h"
#include "Camera/PlayerCameraManager.h"

#define LOCTEXT_NAMESPACE "HaykHud"

using namespace TwUi;

static const FSlateBrush* WhiteBrush() { return FCoreStyle::Get().GetBrush("WhiteBrush"); }

void SHaykHud::Construct(const FArguments& Args)
{
	Owner = Args._Owner;
	TWeakObjectPtr<AHaykPlayerController> O = Owner;

	auto Diff = [O]()
	{
		const AHaykGameMode* GM = O.IsValid() ? O->Mode() : nullptr;
		const int32 D = GM ? GM->GetDifficulty() : 1;
		return FText::Format(LOCTEXT("Diff", "ԴԺՎԱՐՈՒԹՅՈՒՆ՝ {0}"), D == 0 ? LOCTEXT("E", "Հեշտ") : (D == 2 ? LOCTEXT("H", "Դժվար") : LOCTEXT("N", "Նորմալ")));
	};
	auto WorldName = [O]()
	{
		const AHaykGameMode* GM = O.IsValid() ? O->Mode() : nullptr;
		return GM && GM->IsNight() ? LOCTEXT("Night", "ԱՇԽԱՐՀ՝ Մասիսի ստորոտ (գիշեր)") : LOCTEXT("Day", "ԱՇԽԱՐՀ՝ Հայոց ձոր (մայրամուտ)");
	};

	TSharedRef<SWidget> Menu =
		SNew(SBorder).BorderImage(WhiteBrush()).BorderBackgroundColor(FLinearColor(0.01f, 0.f, 0.02f, 0.55f)).Padding(FMargin(90, 50))
		.HAlign(HAlign_Left)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().FillHeight(1.f)[ SNew(SSpacer) ]
			+ SVerticalBox::Slot().AutoHeight()[ SNew(STextBlock).Text(LOCTEXT("Ch", "ԳԼՈՒԽ II · ԹՌԻՉՔ ԴԵՊԻ ԴԻՑԱԲԱՆՈՒԹՅԱՆ ԽՈՐՔԵՐԸ")).Font(TwAssets::Font(16.f, false, true)).ColorAndOpacity(FLinearColor(1, 1, 1, 0.6f)) ]
			+ SVerticalBox::Slot().AutoHeight()
			[
				Title(LOCTEXT("T", "ՀԱՅԿ"), LOCTEXT("S", "Ն Ե Տ Ի   Թ Ռ Ի Չ Ք"),
					LOCTEXT("B", "Հայոց ձորում Հայկ Նահապետը կանգնեց բռնակալ Բելի դեմ։ Ըստ Մովսես Խորենացու՝ նրա եռաթև նետը խոցեց Բելի կուրծքը, և հայերը պահեցին իրենց ազատությունը։"), Gold)
			]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Bot", "ԸՆԴԴԵՄ ԲԵԼԻ (ռոբոտ)"), [O]() { if (O.IsValid()) O->UiVsBot(); }, true) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Two", "ԵՐԿՈՒ ԽԱՂԱՑՈՂ"), [O]() { if (O.IsValid()) O->UiVsFriend(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(TAttribute<FText>::CreateLambda(Diff), [O]() { if (O.IsValid() && O->Mode()) O->Mode()->CycleDifficulty(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(TAttribute<FText>::CreateLambda(WorldName), [O]() { if (O.IsValid() && O->Mode()) O->Mode()->ToggleNight(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Ctl", "ԿԱՌԱՎԱՐՈՒՄ"), [O]() { if (O.IsValid()) O->UiControls(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Hub", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiHub(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Quit", "ԵԼՔ"), [O]() { if (O.IsValid()) O->UiQuit(); }) ]
			+ SVerticalBox::Slot().FillHeight(1.f)[ SNew(SSpacer) ]
		];

	auto Row = [](const FText& K, const FText& V) -> TSharedRef<SWidget>
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().AutoWidth().Padding(0, 6)[ SNew(SBox).WidthOverride(300.f)[ SNew(STextBlock).Text(K).Font(TwAssets::Font(20.f, false, true)).ColorAndOpacity(Gold) ] ]
			+ SHorizontalBox::Slot().FillWidth(1.f).Padding(0, 6)[ SNew(STextBlock).Text(V).Font(TwAssets::Font(20.f, false, false)).ColorAndOpacity(Cream) ];
	};
	TSharedRef<SWidget> Controls =
		SNew(SBorder).BorderImage(WhiteBrush()).BorderBackgroundColor(FLinearColor(0.01f, 0.f, 0.02f, 0.75f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SBox).WidthOverride(920.f)
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 20)[ SNew(STextBlock).Text(LOCTEXT("CtlT", "ԿԱՌԱՎԱՐՈՒՄ")).Font(TwAssets::Font(54.f, true, true)).ColorAndOpacity(Gold) ]
				+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k1", "Մկնիկ / WASD"), LOCTEXT("v1", "Նշանառություն (ուղղություն և անկյուն)")) ]
				+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k2", "Ձախ կոճակ (պահել)"), LOCTEXT("v2", "Լարել աղեղը, բաց թողնել՝ կրակել")) ]
				+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k3", "Աջ կոճակ / Q"), LOCTEXT("v3", "Եռաթև նետ՝ ուղղորդվող, ×1.8 վնաս")) ]
				+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k4", "Մկնիկ թռիչքում"), LOCTEXT("v4", "Եռաթև նետի ուղղորդում (դանդաղեցված)")) ]
				+ SVerticalBox::Slot().AutoHeight()[ Row(LOCTEXT("k5", "Esc"), LOCTEXT("v5", "Դադար")) ]
				+ SVerticalBox::Slot().AutoHeight().Padding(0, 18)
				[
					SNew(STextBlock).AutoWrapText(true).Font(TwAssets::Font(17.f, false, false)).ColorAndOpacity(FLinearColor(1, 0.9f, 0.8f, 0.8f))
					.Text(LOCTEXT("Tip", "Քամին փոխվում է ամեն հերթի։ Գլխին հարվածը՝ 40, կրծքին՝ 22, ոտքերին՝ 12 վնաս։ Երկու անընդմեջ դիպուկ հարվածը տալիս է նոր եռաթև նետ։ Վահանները կանգնեցնում են նետերը, բայց կոտրվում են։"))
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left)[ Button(LOCTEXT("Back", "ՀԵՏ"), [O]() { if (O.IsValid()) O->UiBack(); }, true) ]
			]
		];

	TSharedRef<SWidget> Pause =
		SNew(SBorder).BorderImage(WhiteBrush()).BorderBackgroundColor(FLinearColor(0, 0, 0, 0.6f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 20)[ SNew(STextBlock).Text(LOCTEXT("P", "ԴԱԴԱՐ")).Font(TwAssets::Font(64.f, true, true)).ColorAndOpacity(Gold) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Res", "ՇԱՐՈՒՆԱԿԵԼ"), [O]() { if (O.IsValid()) O->UiResume(); }, true) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Rst", "ՍԿՍԵԼ ՆՈՐԻՑ"), [O]() { if (O.IsValid()) O->UiRestart(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Mn", "ԽԱՂԻ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiMenu(); }) ]
			+ SVerticalBox::Slot().AutoHeight()[ Button(LOCTEXT("Hub2", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiHub(); }) ]
		];

	TSharedRef<SWidget> End =
		SNew(SBorder).BorderImage(WhiteBrush()).BorderBackgroundColor(FLinearColor(0, 0, 0, 0.35f)).HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(FMargin(0, 0, 0, 60))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
			[
				SNew(STextBlock).Font(TwAssets::Font(92.f, true, true))
				.Text_Lambda([O]()
				{
					const AHaykGameMode* GM = O.IsValid() ? O->Mode() : nullptr;
					if (!GM) return FText::GetEmpty();
					if (!GM->IsVsBot()) return GM->DidHaykWin() ? LOCTEXT("P1W", "ՀԱՂԹԵՑ ՀԱՅԿԸ") : LOCTEXT("P2W", "ՀԱՂԹԵՑ ԲԵԼԸ");
					return GM->DidHaykWin() ? LOCTEXT("Win", "ՀԱՂԹԱՆԱԿ") : LOCTEXT("Lose", "ՊԱՐՏՈՒԹՅՈՒՆ");
				})
				.ColorAndOpacity_Lambda([O]() { const AHaykGameMode* GM = O.IsValid() ? O->Mode() : nullptr; return FSlateColor(GM && (GM->DidHaykWin() || !GM->IsVsBot()) ? Gold : Blood); })
				.ShadowOffset(FVector2D(0, 0)).ShadowColorAndOpacity(FLinearColor(1.f, 0.3f, 0.05f, 0.8f))
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 4, 0, 18)
			[
				SNew(STextBlock).Font(TwAssets::Font(22.f, false, false)).ColorAndOpacity(Cream)
				.Text_Lambda([O]()
				{
					const AHaykGameMode* GM = O.IsValid() ? O->Mode() : nullptr;
					if (!GM) return FText::GetEmpty();
					const FText Line = GM->DidHaykWin() ? LOCTEXT("WinL", "Եռաթև նետը խոցեց Բելի կուրծքը։ Հայկի ժառանգները ազատ են։") : LOCTEXT("LoseL", "Բելը այս անգամ ավելի դիպուկ էր… Կրկին փորձիր։");
					return FText::Format(LOCTEXT("Stats", "{0}\nՀայկ՝ {1} դիպուկ ({2} գլխին)   ·   Բել՝ {3} դիպուկ ({4} գլխին)   ·   Հերթեր՝ {5}"), Line,
						FText::AsNumber(GM->GetHits(false)), FText::AsNumber(GM->GetHeadshots(false)), FText::AsNumber(GM->GetHits(true)), FText::AsNumber(GM->GetHeadshots(true)), FText::AsNumber(GM->GetTurn()));
				})
				.Justification(ETextJustify::Center)
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(8, 0)[ Button(LOCTEXT("Again", "ԿՐԿԻՆ"), [O]() { if (O.IsValid()) O->UiRestart(); }, true, 300.f) ]
				+ SHorizontalBox::Slot().AutoWidth().Padding(8, 0)[ Button(LOCTEXT("Mn2", "ԽԱՂԻ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiMenu(); }, false, 300.f) ]
				+ SHorizontalBox::Slot().AutoWidth().Padding(8, 0)[ Button(LOCTEXT("Hub3", "ԳԼԽԱՎՈՐ ՄԵՆՅՈՒ"), [O]() { if (O.IsValid()) O->UiHub(); }, false, 300.f) ]
			]
		];

	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SHaykHud::VisFor, (uint8)EHaykScreen::Menu)[ Menu ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SHaykHud::VisFor, (uint8)EHaykScreen::Controls)[ Controls ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SHaykHud::VisFor, (uint8)EHaykScreen::Pause)[ Pause ] ]
		+ SOverlay::Slot()[ SNew(SBox).Visibility(this, &SHaykHud::VisFor, (uint8)EHaykScreen::End)[ End ] ]
	];
}

EVisibility SHaykHud::VisFor(uint8 Screen) const
{
	const AHaykPlayerController* PC = Owner.Get();
	return PC && (uint8)PC->GetScreen() == Screen ? EVisibility::Visible : EVisibility::Collapsed;
}

int32 SHaykHud::OnPaint(const FPaintArgs& Args, const FGeometry& Geo, const FSlateRect& Cull, FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const
{
	const AHaykPlayerController* PC = Owner.Get();
	if (PC && (PC->GetScreen() == EHaykScreen::None || PC->GetScreen() == EHaykScreen::Pause)) PaintDuel(Geo, Out, Layer);
	return SCompoundWidget::OnPaint(Args, Geo, Cull, Out, Layer + 40, Style, bParentEnabled);
}

void SHaykHud::PaintDuel(const FGeometry& Geo, FSlateWindowElementList& Out, int32 L) const
{
	AHaykPlayerController* PC = Owner.Get();
	AHaykGameMode* GM = PC ? PC->Mode() : nullptr;
	if (!GM || !GM->GetHayk() || !GM->GetBel()) return;
	const FVector2D Size = FVector2D(Geo.GetLocalSize());
	const float S = Size.Y / 1080.f;
	const FVector2D C = Size * 0.5f;
	const EHaykState St = GM->GetState();
	if (St == EHaykState::Menu) return;

	// ---- health bars
	const float BW = 560.f * S, BH = 20.f * S;
	AHaykArcher* H = GM->GetHayk();
	AHaykArcher* B = GM->GetBel();
	Text(Out, L + 4, Geo, FVector2D(50 * S, 26 * S), GM->IsVsBot() ? LOCTEXT("Hn", "ՀԱՅԿ") : LOCTEXT("Hn2", "ՀԱՅԿ · Խաղացող 1"), TwAssets::Font(26 * S, true, true), Gold);
	Bar(Out, L + 4, Geo, FVector2D(50 * S, 74 * S), FVector2D(BW, BH), H->GetHealth() / H->GetMaxHealth(), FLinearColor(0.95f, 0.55f, 0.12f), FLinearColor(1.f, 0.85f, 0.45f, 0.9f));
	Text(Out, L + 4, Geo, FVector2D(Size.X - 50 * S, 26 * S), GM->IsVsBot() ? LOCTEXT("Bn", "ԲԵԼ") : LOCTEXT("Bn2", "Խաղացող 2 · ԲԵԼ"), TwAssets::Font(26 * S, true, true), Blood, 1.f);
	Bar(Out, L + 4, Geo, FVector2D(Size.X - 50 * S - BW, 74 * S), FVector2D(BW, BH), B->GetHealth() / B->GetMaxHealth(), FLinearColor(0.75f, 0.06f, 0.03f), FLinearColor(1.f, 0.35f, 0.2f, 0.9f), true);
	// three-feathered arrows available
	auto Feathers = [&](int32 N, float X, float Align)
	{
		const FText T = FText::Format(LOCTEXT("Sp", "Եռաթև նետ × {0}"), FText::AsNumber(N));
		Text(Out, L + 4, Geo, FVector2D(X, 104 * S), T, TwAssets::Font(15 * S, false, true), N > 0 ? Gold : FLinearColor(1, 1, 1, 0.4f), Align);
	};
	Feathers(GM->GetSpecials(false), 50 * S, 0.f);
	Feathers(GM->GetSpecials(true), Size.X - 50 * S, 1.f);

	// ---- turn + wind (top centre)
	if (St == EHaykState::Aim || St == EHaykState::Flight || St == EHaykState::Impact)
	{
		const bool bBel = GM->IsBelTurn();
		const FText Who = bBel ? (GM->IsVsBot() ? LOCTEXT("BT", "ԲԵԼԸ ՆՇԱՆ Է ԲՌՆՈՒՄ") : LOCTEXT("P2", "ԽԱՂԱՑՈՂ 2")) : (GM->IsVsBot() ? LOCTEXT("YT", "ՔՈ ՀԵՐԹՆ Է") : LOCTEXT("P1", "ԽԱՂԱՑՈՂ 1"));
		Text(Out, L + 4, Geo, FVector2D(C.X, 24 * S), Who, TwAssets::Font(22 * S, false, true), bBel ? Blood : Gold, 0.5f);
		if (St == EHaykState::Aim && GM->IsHumanTurn())
		{
			Text(Out, L + 4, Geo, FVector2D(C.X, 56 * S), FText::AsNumber(FMath::CeilToInt(FMath::Max(0.f, GM->GetTurnLeft()))), TwAssets::Font(30 * S, false, true), GM->GetTurnLeft() < 6.f ? Blood : Cream, 0.5f);
		}
		// wind compass: arrow drawn in screen space relative to the camera yaw
		const FVector W = GM->GetWind();
		const float Ws = W.Size();
		const FVector2D WC(C.X, 140 * S);
		Box(Out, L + 3, Geo, WC - FVector2D(70, 34) * S, FVector2D(140, 68) * S, FLinearColor(0, 0, 0, 0.35f));
		if (Ws > 0.2f)
		{
			float CamYaw = 0.f;
			if (APlayerCameraManager* CM = PC->PlayerCameraManager) CamYaw = CM->GetCameraRotation().Yaw;
			const float Rel = FMath::DegreesToRadians(W.Rotation().Yaw - CamYaw);
			const FVector2D D(FMath::Sin(Rel), -FMath::Cos(Rel)); // screen: up = away from camera
			const float Len = (14.f + 6.f * Ws) * S;
			const FVector2D A = WC - D * Len * 0.5f, Bp = WC + D * Len * 0.5f + FVector2D(0, -6 * S);
			const FVector2D N(-D.Y, D.X);
			Lines(Out, L + 5, Geo, { FVector2f(A), FVector2f(Bp) }, FLinearColor(0.7f, 0.9f, 1.f, 0.95f), 3.f * S);
			Lines(Out, L + 5, Geo, { FVector2f(Bp - D * 10 * S + N * 7 * S), FVector2f(Bp), FVector2f(Bp - D * 10 * S - N * 7 * S) }, FLinearColor(0.7f, 0.9f, 1.f, 0.95f), 3.f * S);
		}
		Text(Out, L + 5, Geo, FVector2D(C.X, 176 * S), FText::Format(LOCTEXT("Wind", "ՔԱՄԻ {0} մ/վ"), FText::AsNumber(FMath::RoundToInt(Ws))), TwAssets::Font(14 * S, false, true), FLinearColor(0.8f, 0.92f, 1.f, 0.9f), 0.5f);
	}

	// ---- aiming: crosshair, power, special
	if (St == EHaykState::Aim && GM->IsHumanTurn())
	{
		// mark the opponent: he is far away across the valley
		if (AHaykArcher* Foe = GM->IsBelTurn() ? GM->GetHayk() : GM->GetBel())
		{
			FVector2D Scr;
			if (PC->ProjectWorldLocationToScreen(Foe->GetHeadTarget() + FVector(0, 0, 60.f), Scr, true))
			{
				Scr /= FMath::Max(Geo.GetAccumulatedLayoutTransform().GetScale(), 0.01f);
				const float T = PC->GetWorld()->GetRealTimeSeconds();
				const float Bob = FMath::Sin(T * 4.f) * 4.f * S;
				const FLinearColor Mc = Foe->IsBel() ? Blood : Gold;
				const FVector2D P(Scr.X, Scr.Y - 18.f * S + Bob);
				Lines(Out, L + 6, Geo, { FVector2f(P + FVector2D(-11, -14) * S), FVector2f(P), FVector2f(P + FVector2D(11, -14) * S) }, Mc, 3.f * S);
				Text(Out, L + 6, Geo, P + FVector2D(0, -44 * S), Foe->IsBel() ? LOCTEXT("BelMark", "ԲԵԼ") : LOCTEXT("HaykMark", "ՀԱՅԿ"), TwAssets::Font(15 * S, false, true), Mc, 0.5f);
			}
		}
		const FLinearColor Cc(1, 1, 1, 0.8f);
		const float G = 8 * S, Ln = 8 * S;
		Lines(Out, L + 5, Geo, { FVector2f(C + FVector2D(-G - Ln, 0)), FVector2f(C + FVector2D(-G, 0)) }, Cc, 2 * S);
		Lines(Out, L + 5, Geo, { FVector2f(C + FVector2D(G, 0)), FVector2f(C + FVector2D(G + Ln, 0)) }, Cc, 2 * S);
		Lines(Out, L + 5, Geo, { FVector2f(C + FVector2D(0, G)), FVector2f(C + FVector2D(0, G + Ln)) }, Cc, 2 * S);
		const float P = GM->GetPower();
		const FVector2D PP(C.X - 220 * S, Size.Y - 120 * S);
		Text(Out, L + 5, Geo, FVector2D(C.X, Size.Y - 156 * S), P > 0.f ? LOCTEXT("Pow", "ԱՂԵՂԻ ԼԱՐՈՒՄ") : LOCTEXT("Hold", "Պահի՛ր ձախ կոճակը՝ աղեղը լարելու համար"), TwAssets::Font(16 * S, false, true), Cream, 0.5f);
		Bar(Out, L + 5, Geo, PP, FVector2D(440 * S, 16 * S), P, P >= 1.f ? FLinearColor(1.f, 0.85f, 0.3f) : FLinearColor(1.f, 0.5f, 0.15f), FLinearColor(1, 1, 0.8f, 0.8f));
		if (GM->IsSpecialArmed())
		{
			const float Pulse = 0.7f + 0.3f * FMath::Sin(PC->GetWorld()->GetRealTimeSeconds() * 8.f);
			Text(Out, L + 5, Geo, FVector2D(C.X, Size.Y - 86 * S), LOCTEXT("Armed", "ԵՌԱԹԵՎ ՆԵՏԸ ԼԱՐՎԱԾ Է"), TwAssets::Font(18 * S, true, true), Gold * Pulse, 0.5f);
		}
		else if (GM->GetSpecials(GM->IsBelTurn()) > 0)
		{
			Text(Out, L + 5, Geo, FVector2D(C.X, Size.Y - 86 * S), LOCTEXT("Ready", "Աջ կոճակ / Q՝ եռաթև նետ"), TwAssets::Font(15 * S, false, false), FLinearColor(1, 0.9f, 0.7f, 0.8f), 0.5f);
		}
	}
	if (St == EHaykState::Flight && GM->GetArrow() && GM->GetArrow()->IsSpecial() && GM->IsHumanTurn())
	{
		Text(Out, L + 5, Geo, FVector2D(C.X, Size.Y - 110 * S), LOCTEXT("Steer", "Ուղղորդի՛ր նետը մկնիկով"), TwAssets::Font(20 * S, false, true), Gold, 0.5f);
	}

	// ---- announcements
	FText At, As; float Age = 0.f;
	if (GM->GetAnnouncement(At, As, Age))
	{
		const float A = FMath::Clamp(Age / 0.2f, 0.f, 1.f) * FMath::Clamp((2.8f - Age) / 0.5f, 0.f, 1.f);
		const float Y = C.Y - 250 * S;
		Text(Out, L + 8, Geo, FVector2D(C.X, Y), At, TwAssets::Font(54 * S, true, true), FLinearColor(Gold.R, Gold.G, Gold.B, A), 0.5f);
		if (!As.IsEmpty()) Text(Out, L + 8, Geo, FVector2D(C.X, Y + 78 * S), As, TwAssets::Font(22 * S, false, false), FLinearColor(Cream.R, Cream.G, Cream.B, A * 0.9f), 0.5f);
	}
}

#undef LOCTEXT_NAMESPACE
