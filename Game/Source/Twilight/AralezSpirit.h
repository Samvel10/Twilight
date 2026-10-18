#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "AralezSpirit.generated.h"

class USpringArmComponent;
class UCameraComponent;
class UPointLightComponent;
class UStaticMeshComponent;
class UMaterialInstanceDynamic;
class UInstancedStaticMeshComponent;

/** A winged spirit-dog made of light. Player-controlled or a racing bot. */
UCLASS()
class TWILIGHT_API AAralezSpirit : public APawn
{
	GENERATED_BODY()
public:
	AAralezSpirit();
	void Setup(bool bInBot, const FLinearColor& InColor, const FText& InName, int32 InSkill);
	virtual void Tick(float Dt) override;

	// input (player)
	void InMove(const FVector2D& V) { MoveIn = V; }
	void InLook(const FVector2D& V);
	void InUp(float V) { UpIn = V; }
	void InDash();
	void InHowl();
	void SetControlEnabled(bool b) { bControl = b; if (!b) { MoveIn = FVector2D::ZeroVector; UpIn = 0.f; } }

	// race state
	int32 GetLights() const { return Lights; }
	void AddLights(int32 N) { Lights += N; Pulse = 1.f; }
	int32 StealLights(int32 N);
	float GetProgress() const { return PathT; }
	bool IsFinished() const { return bFinished; }
	float GetFinishTime() const { return FinishTime; }
	void MarkFinished(float Time) { bFinished = true; FinishTime = Time; }
	bool IsBot() const { return bBot; }
	FText GetRacerName() const { return Name; }
	FLinearColor GetColor() const { return Color; }
	float GetDashCooldown() const { return DashCd; }
	float GetHowlCooldown() const { return HowlCd; }
	float GetStun() const { return Stun; }
	void Stunned(float Secs) { Stun = FMath::Max(Stun, Secs); }
	FVector GetVel() const { return Vel; }

	static constexpr float Speed = 2600.f;

protected:
	virtual void BeginPlay() override;

private:
	void BuildBody();
	void ThinkBot(float Dt);
	void Move(float Dt);
	void Animate(float Dt);

	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> Root;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USceneComponent> BodyRoot;
	UPROPERTY(VisibleAnywhere) TObjectPtr<USpringArmComponent> Boom;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UCameraComponent> Camera;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> Glow;
	UPROPERTY(VisibleAnywhere) TObjectPtr<UInstancedStaticMeshComponent> Trail;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> WingL;
	UPROPERTY() TObjectPtr<UStaticMeshComponent> WingR;
	UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> TailParts;
	UPROPERTY() TObjectPtr<UMaterialInstanceDynamic> Mat;

	bool bBot = false;
	bool bControl = true;
	int32 Skill = 1;
	FLinearColor Color = FLinearColor(0.6f, 0.9f, 1.f);
	FText Name;
	FVector Vel = FVector::ZeroVector;
	FVector2D MoveIn = FVector2D::ZeroVector;
	float UpIn = 0.f;
	float PathT = 0.f;
	int32 Lights = 0;
	bool bFinished = false;
	float FinishTime = 0.f;
	float DashCd = 0.f, DashTime = 0.f, HowlCd = 0.f;
	float Stun = 0.f;
	float Pulse = 0.f;
	float Flap = 0.f;
	float BotLane = 0.f;
	float BotThink = 0.f;
	FVector BotGoal = FVector::ZeroVector;
	float TrailTimer = 0.f;
	int32 TrailNext = 0;
	TArray<float> TrailBirth;
};
