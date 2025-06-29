"""Demo of branch creation and management."""

import os
import shutil
from pathlib import Path
import synthdb
from synthdb.local_config import get_local_config, init_local_project


def demo_branches():
    """Demonstrate branch creation and management."""
    print("=== SynthDB Branch Management Demo ===\n")
    
    # Clean up any existing demo directory
    demo_dir = Path("branch_demo")
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
    
    # Create demo directory
    demo_dir.mkdir()
    os.chdir(demo_dir)
    
    try:
        # 1. Initialize project
        print("1. Initializing project...")
        init_local_project()
        config = get_local_config()
        print(f"   Created project with branch: {config.get_active_branch()}")
        print()
        
        # 2. Create some data in main branch
        print("2. Adding data to main branch...")
        db = synthdb.connect()
        db.create_table("users")
        db.add_columns("users", {"name": "text", "email": "text", "role": "text"})
        
        db.insert("users", {"name": "Alice", "email": "alice@example.com", "role": "admin"})
        db.insert("users", {"name": "Bob", "email": "bob@example.com", "role": "user"})
        
        users = db.query("users")
        print(f"   Main branch has {len(users)} users")
        print()
        
        # 3. Create feature branch
        print("3. Creating feature branch...")
        config.create_branch("feature-roles")
        print("   Created branch: feature-roles")
        
        # 4. Create hotfix branch from main
        print("4. Creating hotfix branch from main...")
        config.create_branch("hotfix-123", from_branch="main")
        print("   Created branch: hotfix-123 (from main)")
        print()
        
        # 5. List all branches
        print("5. All branches:")
        branches = config.list_branches()
        active = config.get_active_branch()
        for name, info in branches.items():
            marker = " *" if name == active else ""
            print(f"   - {name}{marker}")
            print(f"     Database: {info['database']}")
            print(f"     Created: {info['created']}")
        print()
        
        # 6. Switch to feature branch and add data
        print("6. Working in feature-roles branch...")
        config.set_active_branch("feature-roles")
        db_feature = synthdb.connect()  # Automatically connects to feature branch
        
        # Add a new user only in feature branch
        db_feature.insert("users", {"name": "Charlie", "email": "charlie@example.com", "role": "moderator"})
        
        feature_users = db_feature.query("users")
        print(f"   Feature branch has {len(feature_users)} users")
        print()
        
        # 7. Switch to hotfix branch
        print("7. Working in hotfix-123 branch...")
        config.set_active_branch("hotfix-123")
        db_hotfix = synthdb.connect()
        
        # Update a user's email (hotfix)
        hotfix_users = db_hotfix.query("users", where="name = 'Alice'")
        if hotfix_users:
            row_id = hotfix_users[0]['row_id']
            # Insert the updated email (SynthDB keeps history)
            db_hotfix.insert("users", "email", "alice.admin@example.com", row_id=row_id)
            print("   Updated Alice's email in hotfix branch")
        
        hotfix_all = db_hotfix.query("users")
        print(f"   Hotfix branch has {len(hotfix_all)} users")
        print()
        
        # 8. Compare branches
        print("8. Branch comparison:")
        print("   Main: 2 users, original emails")
        print("   Feature-roles: 3 users (added Charlie)")
        print("   Hotfix-123: 2 users (Alice's email updated)")
        print()
        
        # 9. Show config structure
        print("9. Project structure:")
        synthdb_dir = config.synthdb_dir
        print(f"   .synthdb/")
        print(f"   ├── config")
        print(f"   └── databases/")
        for db_file in sorted((synthdb_dir / "databases").glob("*.db")):
            print(f"       └── {db_file.name}")
        
    finally:
        # Clean up
        os.chdir("..")
        if demo_dir.exists():
            shutil.rmtree(demo_dir)
        print("\nDemo complete! (cleaned up branch_demo directory)")


if __name__ == "__main__":
    demo_branches()