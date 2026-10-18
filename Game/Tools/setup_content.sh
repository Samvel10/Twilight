#!/usr/bin/env bash
# Restores engine-provided content that is not stored in git (mannequins + StarterContent).
set -e
UE=${UE:-$HOME/UnrealEngine-5.8}
G=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$G/Content"
[ -d "$G/Content/Characters" ] || cp -r "$UE/Templates/TemplateResources/High/Characters/Content" "$G/Content/Characters"
[ -d "$G/Content/StarterContent" ] || cp -r "$UE/Samples/StarterContent/Content/StarterContent" "$G/Content/StarterContent"
echo "content ready in $G/Content"
