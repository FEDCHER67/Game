from pathlib import Path
import json,hashlib,re,difflib
root=Path(r"C:\Dev\Game")
out=root/"Working/Reviews/Wind"
source=(root/"ArtSource/Dev/Grass_staging/Wind_v01/evidence/assemble_and_audit_v01.py").read_text()
audit=source[source.index("baseline=json.loads"):source.index('print(json.dumps({"capture"')]
audit=audit.replace("integrity_i05_v01.json","integrity_i05_v02.json")
exec(audit)
print(json.dumps(integrity,indent=2))
assert not modified and not missing and not removed
assert set(changed)=={"1871110881","9223372036854775807"}, "Unexpected changed base scene block"
assert len(added)==3

