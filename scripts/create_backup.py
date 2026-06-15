import shutil
import os
from datetime import datetime

def create_backup():
    # Define files and directories to back up
    items_to_backup = [
        ".env",
        "app/config.py",
        "reports/",
        "requirements.txt"
    ]
    
    backup_folder = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if not os.path.exists("backups"):
        os.makedirs("backups")
        
    os.makedirs(backup_folder)
    
    for item in items_to_backup:
        if os.path.exists(item):
            dest = os.path.join(backup_folder, os.path.basename(item.rstrip('/')))
            if os.path.isdir(item):
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
            print(f"Backed up: {item}")
        else:
            print(f"Warning: {item} not found, skipping.")
            
    print(f"Backup completed at {backup_folder}")

if __name__ == "__main__":
    create_backup()
