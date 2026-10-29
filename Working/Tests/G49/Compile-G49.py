"""Roslyn-only check of the actual Unity sources while another owner holds Unity.
Use current asmdef references in memory; do not rewrite Unity's stale generated projects.
This is not a Unity compilation or a Unity test run.
"""
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
root = Path('C:/Dev/Game')
skill = Path('C:/Users/Zeyo-ne/.codex/plugins/cache/agent-foundry/agent-foundry/0.9.4/skills/unity-cli/scripts/unity_compile_check.py')
spec = importlib.util.spec_from_file_location('compile_check', skill)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
project = module.UnityProject(root)
for asmdef in (root / 'Assets/OnlyVolunteers').rglob('*.asmdef'):
    data = json.loads(asmdef.read_text(encoding='utf-8-sig'))
    target = project.by_assembly.get(data['name'].lower())
    if target is None:
        continue
    for name in data.get('references', []):
        dependency = project.by_assembly.get(name.lower())
        if dependency and module.normalize(dependency.path) not in target.references:
            target.references.append(module.normalize(dependency.path))
files = list((root / 'Assets/OnlyVolunteers/Inventory/Core').glob('*.cs'))
files += list((root / 'Assets/OnlyVolunteers/Buyers/Core').glob('*.cs'))
files += list((root / 'Assets/OnlyVolunteers/Operation/Stage1/Core').glob('*.cs'))
files += list((root / 'Assets/OnlyVolunteers/Inventory/Tests/EditMode').glob('*.cs'))
files += list((root / 'Assets/OnlyVolunteers/Operation/Stage1/Tests').glob('*.cs'))
files += list((root / 'Assets/OnlyVolunteers/Buyers/Tests').glob('*.cs'))
files += [root / ('Assets/OnlyVolunteers/' + p) for p in [
    'Inventory/Runtime/ItemDefinition.cs', 'Inventory/Runtime/ItemStackSerializers.cs',
    'Inventory/Runtime/LocalInventory.cs', 'Inventory/Runtime/OfflineWorldItem.cs', 'Inventory/Runtime/WorldItem.cs',
    'Capture/Scripts/CaptureFieldKit.cs', 'Capture/Scripts/CaptureSyringeBindings.cs', 'Capture/Scripts/CaptureNpc.cs',
    'Operation/Stage1/Scripts/NetworkOperationTable.cs', 'Operation/Stage1/Scripts/OperationHud.cs']]
sys.exit(module.check(project, [str(p) for p in files], False))
