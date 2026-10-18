using UnrealBuildTool;
public class Twilight : ModuleRules
{
	public Twilight(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[] {
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
			"Niagara", "UMG", "Slate", "SlateCore", "AIModule", "ProceduralMeshComponent", "ApplicationCore"
		});
	}
}
