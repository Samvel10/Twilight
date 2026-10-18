using UnrealBuildTool;
public class Twilight : ModuleRules
{
	public Twilight(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		// each game keeps small file-local helpers; avoid unity-blob name clashes
		bUseUnity = false;
		PublicDependencyModuleNames.AddRange(new string[] {
			"Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput",
			"Niagara", "UMG", "Slate", "SlateCore", "AIModule", "ProceduralMeshComponent", "ApplicationCore"
		});
	}
}
