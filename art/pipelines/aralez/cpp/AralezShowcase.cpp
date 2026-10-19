#include "AralezShowcase.h"
#include "AralezWingComponent.h"

AAralezShowcase::AAralezShowcase()
{
	PrimaryActorTick.bCanEverTick = true;
	Body = CreateDefaultSubobject<UAralezBodyComponent>(TEXT("Body"));
	RootComponent = Body;
}

void AAralezShowcase::BeginPlay()
{
	Super::BeginPlay();
	Body->AssetRoot = AssetRoot;
	Body->Build();
	if (Body->GetWings()) Body->GetWings()->SetFlapRate(FlapHz);
	if (FixedMode >= 0) Body->SetMode((EAralezMode)FixedMode, 0.f);
}

void AAralezShowcase::Tick(float Dt)
{
	Super::Tick(Dt);
	if (FixedMode >= 0) return;
	T += Dt;
	const int32 S = T < 3.f ? 0 : T < 7.f ? 1 : T < 9.f ? 2 : 3;
	if (S != Stage)
	{
		Stage = S;
		const EAralezMode M[4] = { EAralezMode::Glide, EAralezMode::Flap, EAralezMode::Land, EAralezMode::Lick };
		Body->SetMode(M[S], 0.35f);
	}
}
