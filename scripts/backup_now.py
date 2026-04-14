from pathlib import Path
from datetime import datetime

def main() -> None:
    backup_root = Path("data/backups")
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    marker = backup_root / f"backup-{stamp}.txt"
    marker.write_text("Backup placeholder. Implement real backup flow.\n", encoding="utf-8")
    print(marker)

if __name__ == "__main__":
    main()
