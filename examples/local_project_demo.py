"""Demo of SynthDB local project and branch management."""

import os
import shutil
from pathlib import Path
import synthdb
from synthdb.local_config import get_local_config, init_local_project


def demo_local_project():
    """Demonstrate local project and branch features."""
    print("=== SynthDB Local Project Demo ===\n")
    
    # Clean up any existing demo directory
    demo_dir = Path("demo_project")
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
    
    # Create demo directory
    demo_dir.mkdir()
    os.chdir(demo_dir)
    
    try:
        # 1. Initialize a new project
        print("1. Initializing SynthDB project...")
        project_path = init_local_project()
        print(f"   Created: {project_path}")
        print(f"   Config file: {project_path / 'config'}")
        print()
        
        # 2. Show project status
        print("2. Project status:")
        config = get_local_config()
        print(f"   Active branch: {config.get_active_branch()}")
        print(f"   Database path: {config.get_database_path()}")
        print()
        
        # 3. Connect to the database
        print("3. Connecting to database...")
        db = synthdb.connect()  # Will use .synthdb config automatically
        print(f"   Connected to: {config.get_database_path()}")
        print()
        
        # 4. Create a table and add data
        print("4. Creating table and adding data...")
        db.create_table("products")
        db.add_columns("products", {"name": "text", "price": "real"})
        
        # Use the connection object to insert data
        db.insert("products", {"name": "Widget", "price": 19.99})
        db.insert("products", {"name": "Gadget", "price": 29.99})
        print("   Added 2 products to main branch")
        print()
        
        # 5. Create a new branch
        print("5. Creating development branch...")
        dev_db_path = config.create_branch("development")
        print(f"   Created branch 'development' at: {dev_db_path}")
        print()
        
        # 6. Switch to development branch
        print("6. Switching to development branch...")
        config.set_active_branch("development")
        print(f"   Active branch: {config.get_active_branch()}")
        print()
        
        # 7. Connect to development database
        print("7. Working with development database...")
        # Need to reconnect after branch switch
        dev_db = synthdb.connect()
        
        # Verify data was copied
        products = dev_db.query("products")
        print(f"   Found {len(products)} products in development branch")
        
        # Add development-only data
        dev_db.insert("products", {"name": "Prototype", "price": 99.99})
        print("   Added prototype product to development branch")
        print()
        
        # 8. List all branches
        print("8. All branches:")
        branches = config.list_branches()
        for branch_name, info in branches.items():
            active = " (active)" if branch_name == config.get_active_branch() else ""
            print(f"   - {branch_name}{active}")
            print(f"     Database: {info['database']}")
            print(f"     Created: {info['created']}")
        print()
        
        # 9. Switch back to main
        print("9. Switching back to main branch...")
        config.set_active_branch("main")
        main_db = synthdb.connect()
        
        # Verify main branch doesn't have prototype
        main_products = main_db.query("products")
        print(f"   Main branch has {len(main_products)} products")
        print("   (Prototype product only exists in development branch)")
        print()
        
        # 10. Show config file contents
        print("10. Config file contents:")
        config_path = project_path / "config"
        with open(config_path) as f:
            print("   " + f.read().replace("\n", "\n   "))
        
    finally:
        # Clean up
        os.chdir("..")
        if demo_dir.exists():
            shutil.rmtree(demo_dir)
        print("\nDemo complete! (cleaned up demo_project directory)")


if __name__ == "__main__":
    demo_local_project()