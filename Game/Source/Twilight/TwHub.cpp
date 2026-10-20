#include "TwHub.h"
#include "Twilight.h"
#include "TwAssets.h"
#include "TwUi.h"
#include "TwFx.h"
#include "VahagnWorld.h"

#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "Widgets/SWeakWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Text/STextBlock.h"
#include "Styling/CoreStyle.h"

#define LOCTEXT_NAMESPACE "TwHub"

using namespace TwUi;

// ------------------------------------------------------------------ game mode
ATwHubGameMode::ATwHubGameMode()
{
	PrimaryActorTick.bCanEverTick = true;
	DefaultPawnClass = nullptr;
	PlayerControllerClass = ATwHubController::StaticClass();
	HUDClass = nullptr;
}

void ATwHubGameMode::StartPlay()
{
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	World = GetWorld()->SpawnActor<AVahagnWorld>(FVector::ZeroVector, FRotator::ZeroRotator, P);
	Cam = GetWorld()->SpawnActor<ACameraActor>(FVector(0, 0, 2000), FRotator(-5, 0, 0), P);
	if (Cam) Cam->GetCameraComponent()->bConstrainAspectRatio = false;
	Super::StartPlay();
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0)) PC->SetViewTarget(Cam);
}

void ATwHubGameMode::Tick(float Dt)
{
	Super::Tick(Dt);
	T += Dt;
	if (Cam)
	{
		// glide low over the purple sea toward the sunset
		const float A = T * 0.03f;
		const FVector Pos(FMath::Cos(A) * 9000.f, FMath::Sin(A) * 9000.f, 900.f + 250.f * FMath::Sin(T * 0.2f));
		const FRotator Rot(-3.f + 2.f * FMath::Sin(T * 0.13f), FMath::RadiansToDegrees(A) + 110.f, 0.f);
		Cam->SetActorLocationAndRotation(Pos, Rot);
	}
}

// ------------------------------------------------------------------ controller
ATwHubController::ATwHubController() { bShowMouseCursor = true; bAutoManageActiveCameraTarget = false; }

void ATwHubController::BeginPlay()
{
	Super::BeginPlay();
	// Shipping builds ignore a map on the command line (UE_ALLOW_MAP_OVERRIDE_IN_SHIPPING is off):
	// "-TwMap=L_Vahagn" jumps straight into a chapter, once per process (returning to the menu stays here)
	static bool bMapOverrideDone = false;
	FString StartMap;
	if (!bMapOverrideDone && FParse::Value(FCommandLine::Get(), TEXT("TwMap="), StartMap) && !StartMap.IsEmpty() && StartMap != TEXT("L_Menu"))
	{
		bMapOverrideDone = true;
		if (!StartMap.StartsWith(TEXT("/"))) StartMap = TEXT("/Game/Twilight/Maps/") + StartMap;
		UGameplayStatics::OpenLevel(this, FName(*StartMap));
		return;
	}
	bMapOverrideDone = true;
	if (GEngine && GEngine->GameViewport && IsLocalController())
	{
		Ui = SNew(STwHubWidget).Owner(this);
		GEngine->GameViewport->AddViewportWidgetContent(SNew(SWeakWidget).PossiblyNullContent(Ui.ToSharedRef()), 10);
	}
	FInputModeGameAndUI M;
	M.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	M.SetHideCursorDuringCapture(false);
	SetInputMode(M);
	bShowMouseCursor = true;
}

void ATwHubController::EndPlay(const EEndPlayReason::Type Reason)
{
	if (Ui.IsValid() && GEngine && GEngine->GameViewport) GEngine->GameViewport->RemoveViewportWidgetContent(Ui.ToSharedRef());
	Ui.Reset();
	Super::EndPlay(Reason);
}

void ATwHubController::Open(const TCHAR* Map)
{
	TwFx::Sound2D(GetWorld(), TEXT("sfx_ui_click"));
	UGameplayStatics::OpenLevel(this, FName(Map));
}

void ATwHubController::Quit() { UKismetSystemLibrary::QuitGame(this, this, EQuitPreference::Quit, false); }

// ------------------------------------------------------------------ widget
static const FSlateBrush* WB() { return FCoreStyle::Get().GetBrush("WhiteBrush"); }

TSharedRef<SWidget> STwHubWidget::Card(const FText& Chapter, const FText& Title, const FText& Genre, const FText& Text, const TCHAR* Map, bool bReady)
{
	TWeakObjectPtr<ATwHubController> O = Owner;
	const FString MapStr = Map;
	return SNew(SBox).WidthOverride(430.f)
	[
		SNew(SBorder).BorderImage(WB()).BorderBackgroundColor(FLinearColor(0.02f, 0.f, 0.03f, 0.72f)).Padding(FMargin(28, 26))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[ SNew(STextBlock).Text(Chapter).Font(TwAssets::Font(15.f, false, true)).ColorAndOpacity(FLinearColor(1, 1, 1, 0.55f)) ]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 4)[ SNew(STextBlock).Text(Title).Font(TwAssets::Font(46.f, true, true)).ColorAndOpacity(Gold) ]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)[ SNew(STextBlock).Text(Genre).Font(TwAssets::Font(16.f, false, true)).ColorAndOpacity(Ember) ]
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 16)[ SNew(SBox).HeightOverride(150.f)[ SNew(STextBlock).AutoWrapText(true).Text(Text).Font(TwAssets::Font(16.f, false, false)).ColorAndOpacity(Cream) ] ]
			+ SVerticalBox::Slot().AutoHeight()
			[
				bReady ? Button(LOCTEXT("Play", "ԽԱՂԱԼ"), [O, MapStr]() { if (O.IsValid()) O->Open(*MapStr); }, true, 374.f)
				       : StaticCastSharedRef<SWidget>(SNew(SBox).WidthOverride(374.f).HeightOverride(62.f).HAlign(HAlign_Center).VAlign(VAlign_Center)[ SNew(STextBlock).Text(LOCTEXT("Soon", "ՇՈՒՏՈՎ")).Font(TwAssets::Font(20.f, false, true)).ColorAndOpacity(FLinearColor(1, 1, 1, 0.45f)) ])
			]
		]
	];
}

struct FCodexEntry { FText Name; FText Role; FText Text; };

TSharedRef<SWidget> STwHubWidget::Codex()
{
	const TArray<FCodexEntry> E = {
		{ LOCTEXT("c1n", "Արամազդ"), LOCTEXT("c1r", "Գերագույն աստված · հուն. Զևս"), LOCTEXT("c1t", "Հայկական դիցարանի գլխավոր աստվածը՝ երկնքի և երկրի արարիչը, առատության ու պտղաբերության պարգևատուն։") },
		{ LOCTEXT("c2n", "Անահիտ"), LOCTEXT("c2r", "Մայր աստվածուհի · հուն. Արտեմիս"), LOCTEXT("c2t", "«Ոսկեմայր» Անահիտը մայրության, պտղաբերության և հայոց երկրի պահապանն էր։ Նրա ոսկե արձանը կանգնած էր Երիզայի տաճարում։") },
		{ LOCTEXT("c3n", "Վահագն"), LOCTEXT("c3r", "Կրակի և քաջության աստված · հուն. Հերակլես"), LOCTEXT("c3t", "Ըստ Մովսես Խորենացու՝ ծնվել է ծիրանի ծովի կարմիր եղեգից. «Նա հուր հեր ուներ, բոց ուներ մորուս»։ Կոչվում է Վիշապաքաղ՝ վիշապներին հաղթող։") },
		{ LOCTEXT("c4n", "Աստղիկ"), LOCTEXT("c4r", "Սիրո և գեղեցկության աստվածուհի · հուն. Աֆրոդիտե"), LOCTEXT("c4t", "Վահագնի սիրեցյալը։ Ավանդության համաձայն՝ Վարդավառի տոնը կապված է նրա հետ։") },
		{ LOCTEXT("c5n", "Տիր"), LOCTEXT("c5r", "Գրի և իմաստության աստված · հուն. Ապոլոն"), LOCTEXT("c5t", "Գրչության, գիտությունների և արվեստների հովանավորը, երազների մեկնիչը։") },
		{ LOCTEXT("c6n", "Վիշապներ"), LOCTEXT("c6r", "Ջրերի և խավարի ուժեր"), LOCTEXT("c6t", "Հսկա օձանման արարածներ, որոնք փակում էին ջրերը և սպառնում աշխարհին։ Գեղամա և Արագածի լեռներում կանգնած են հազարամյակներ առաջ կերտված քարե վիշապաքարերը։") },
		{ LOCTEXT("c7n", "Հայկ Նահապետ"), LOCTEXT("c7r", "Հայոց նախահայրը"), LOCTEXT("c7t", "Ապստամբեց Բաբելոնի բռնակալ Բելի դեմ, հաստատվեց Արարատյան երկրում և Հայոց ձորի ճակատամարտում եռաթև նետով սպանեց Բելին։ Ավանդական թվականը՝ Ք․ա․ 2492։") },
		{ LOCTEXT("c8n", "Բել"), LOCTEXT("c8r", "Բաբելոնի բռնակալը"), LOCTEXT("c8t", "Հսկա և ամբարտավան տիրակալ, որ պահանջում էր բոլորից խոնարհվել իրեն։ Նրա պարտությունը դարձավ ազատության խորհրդանիշ։") },
		{ LOCTEXT("c9n", "Նավասարդ"), LOCTEXT("c9r", "Հայկական Նոր տարի"), LOCTEXT("c9t", "Հին հայկական տոմարի առաջին ամիսը։ Նոր տարին՝ Նավասարդի 1-ը (օգոստոսի 11), կապվում է Հայկի հաղթանակի հետ։") },
		{ LOCTEXT("c10n", "Արա Գեղեցիկ"), LOCTEXT("c10r", "Հայոց արքա"), LOCTEXT("c10t", "Ասորեստանի թագուհի Շամիրամը, հմայված նրա գեղեցկությամբ, պատերազմ սկսեց։ Արան զոհվեց ճակատամարտում։") },
		{ LOCTEXT("c11n", "Արալեզներ"), LOCTEXT("c11r", "Կենդանացնող ոգիներ"), LOCTEXT("c11t", "Շնանման ոգիներ, որոնք լիզելով վերքերը կենդանացնում էին մարտում ընկած քաջերին։ Շամիրամը հույս ուներ, որ նրանք կվերադարձնեն Արային։") },
	};
	TSharedRef<SScrollBox> List = SNew(SScrollBox);
	for (const FCodexEntry& X : E)
	{
		List->AddSlot().Padding(0, 0, 0, 18)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth()[ SNew(STextBlock).Text(X.Name).Font(TwAssets::Font(28.f, true, true)).ColorAndOpacity(Gold) ]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom).Padding(16, 0, 0, 4)[ SNew(STextBlock).Text(X.Role).Font(TwAssets::Font(15.f, false, true)).ColorAndOpacity(Ember) ]
			]
			+ SVerticalBox::Slot().AutoHeight()[ SNew(STextBlock).AutoWrapText(true).Text(X.Text).Font(TwAssets::Font(17.f, false, false)).ColorAndOpacity(Cream) ]
		];
	}
	return SNew(SBorder).BorderImage(WB()).BorderBackgroundColor(FLinearColor(0.01f, 0.f, 0.02f, 0.85f)).HAlign(HAlign_Center).VAlign(VAlign_Center).Padding(40)
	[
		SNew(SBox).WidthOverride(1100.f).HeightOverride(860.f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 18)[ SNew(STextBlock).Text(LOCTEXT("CodexT", "ԴԻՑԱՐԱՆ")).Font(TwAssets::Font(56.f, true, true)).ColorAndOpacity(Gold) ]
			+ SVerticalBox::Slot().FillHeight(1.f)[ List ]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left).Padding(0, 14, 0, 0)[ Button(LOCTEXT("Back", "ՀԵՏ"), [this]() { bCodex = false; }, true, 300.f) ]
		]
	];
}

void STwHubWidget::Construct(const FArguments& Args)
{
	Owner = Args._Owner;
	TWeakObjectPtr<ATwHubController> O = Owner;
	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot()
		[
			SNew(SBox).Visibility_Lambda([this]() { return bCodex ? EVisibility::Collapsed : EVisibility::Visible; })
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 60, 0, 0)
				[
					SNew(STextBlock).Text(LOCTEXT("Pre", "ԹՌԻՉՔ ԴԵՊԻ ԴԻՑԱԲԱՆՈՒԹՅԱՆ ԽՈՐՔԵՐԸ")).Font(TwAssets::Font(18.f, false, true)).ColorAndOpacity(FLinearColor(1, 1, 1, 0.7f))
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
				[
					SNew(STextBlock).Text(LOCTEXT("Name", "ԾԻՐԱՆԻ")).Font(TwAssets::Font(130.f, true, true)).ColorAndOpacity(Gold)
					.ShadowOffset(FVector2D(0, 0)).ShadowColorAndOpacity(FLinearColor(1.f, 0.35f, 0.05f, 0.9f))
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 30)
				[
					SNew(STextBlock).Text(LOCTEXT("Tag", "Երեք առասպել · երեք խաղ")).Font(TwAssets::Font(24.f, false, false)).ColorAndOpacity(Cream)
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().Padding(14, 0)[ Card(LOCTEXT("C1", "ԳԼՈՒԽ I"), LOCTEXT("V", "ՎԱՀԱԳՆ"), LOCTEXT("VG", "Թռիչքային էքշն · 8 րոպե"), LOCTEXT("VT", "Կրակե պատանին պաշտպանում է Սևանը։ Օձանման վիշապները բարձրանում են լճից, իսկ Վահագնը նրանց խոցում է կրակով ու կայծակով։"), TEXT("/Game/Twilight/Maps/L_Vahagn"), true) ]
					+ SHorizontalBox::Slot().AutoWidth().Padding(14, 0)[ Card(LOCTEXT("C2", "ԳԼՈՒԽ II"), LOCTEXT("H", "ՀԱՅԿ"), LOCTEXT("HG", "Մենամարտ · 1–2 խաղացող"), LOCTEXT("HT", "Վանա լճի ափին Բելը կանգնած է բլրի վրա՝ նետաձիգների հետևում։ Ճեղքի՛ր շարքը, և եռաթև նետը կխոցի բռնակալին։"), TEXT("/Game/Twilight/Maps/L_Hayk"), true) ]
					+ SHorizontalBox::Slot().AutoWidth().Padding(14, 0)[ Card(LOCTEXT("C3", "ԳԼՈՒԽ III"), LOCTEXT("A", "ԱՐԱԼԵԶ"), LOCTEXT("AG", "Արայի դաշտը"), LOCTEXT("AT", "Մայրամուտին Արալեզներն իջնում են երկնքից մարտադաշտ։ Կենդանացրո՛ւ ընկած քաջերին և Արա Գեղեցիկին, մինչև Շամիրամը կխաբի ժողովրդին։"), TEXT("/Game/Twilight/Maps/L_Aralez"), true) ]
				]
				+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 30, 0, 0)
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth().Padding(10, 0)[ Button(LOCTEXT("Codex", "ԴԻՑԱՐԱՆ"), [this]() { bCodex = true; }, false, 320.f) ]
					+ SHorizontalBox::Slot().AutoWidth().Padding(10, 0)[ Button(LOCTEXT("Quit", "ԵԼՔ"), [O]() { if (O.IsValid()) O->Quit(); }, false, 320.f) ]
				]
			]
		]
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0, 0, 0, 10)
		[
			SNew(STextBlock).Text(LOCTEXT("Credits", "Կերպարներ՝ Andy Woodhead, Mu.Mu1 · Օձ-վիշապ՝ ffish.asia · Արալեզ՝ quander · Բույսեր՝ emarshall, 3dhdscan, evolveduk (CC BY 4.0) · Ռելիեֆ՝ Mapzen / SRTM · Երկինք, ժայռեր՝ Poly Haven (CC0)"))
			.Font(TwAssets::Font(11.f, false, false)).ColorAndOpacity(FLinearColor(1.f, 0.92f, 0.8f, 0.55f))
		]
		+ SOverlay::Slot()
		[
			SNew(SBox).Visibility_Lambda([this]() { return bCodex ? EVisibility::Visible : EVisibility::Collapsed; })[ Codex() ]
		]
	];
}

#undef LOCTEXT_NAMESPACE
