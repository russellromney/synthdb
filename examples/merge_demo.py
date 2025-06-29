"""Demo of branch structure merging functionality."""

import os
import shutil
from pathlib import Path
import synthdb
from synthdb.local_config import get_local_config, init_local_project


def demo_merge():
    """Demonstrate branch merging capabilities."""
    print("=== SynthDB Branch Merge Demo ===\n")
    
    # Clean up any existing demo directory
    demo_dir = Path("merge_demo")
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
        print("   ✓ Created project with main branch")
        print()
        
        # 2. Create initial structure in main
        print("2. Creating initial structure in main branch...")
        db = synthdb.connect()
        
        # Create users table
        db.create_table("users")
        db.add_columns("users", {
            "name": "text",
            "email": "text",
            "created_at": "timestamp"
        })
        
        # Create products table
        db.create_table("products")
        db.add_columns("products", {
            "name": "text",
            "price": "real"
        })
        
        print("   ✓ Created tables: users, products")
        print()
        
        # 3. Create feature branch for analytics
        print("3. Creating feature-analytics branch...")
        config.create_branch("feature-analytics")
        config.set_active_branch("feature-analytics")
        print("   ✓ Switched to feature-analytics branch")
        print()
        
        # 4. Add new analytics structure
        print("4. Adding analytics tables and columns...")
        db_analytics = synthdb.connect()
        
        # Add new analytics table
        db_analytics.create_table("analytics_events")
        db_analytics.add_columns("analytics_events", {
            "event_type": "text",
            "user_id": "text",
            "timestamp": "timestamp",
            "properties": "text"  # JSON stored as text
        })
        
        # Add analytics columns to existing users table
        db_analytics.add_columns("users", {
            "last_active": "timestamp",
            "total_events": "integer"
        })
        
        print("   ✓ Added analytics_events table")
        print("   ✓ Added columns to users table: last_active, total_events")
        print()
        
        # 5. Create another feature branch for inventory
        print("5. Creating feature-inventory branch from main...")
        config.create_branch("feature-inventory", from_branch="main")
        config.set_active_branch("feature-inventory")
        print("   ✓ Switched to feature-inventory branch")
        print()
        
        # 6. Add inventory features
        print("6. Adding inventory structure...")
        db_inventory = synthdb.connect()
        
        # Add inventory table
        db_inventory.create_table("inventory")
        db_inventory.add_columns("inventory", {
            "product_id": "text",
            "quantity": "integer",
            "warehouse": "text",
            "last_updated": "timestamp"
        })
        
        # Add inventory columns to products
        db_inventory.add_columns("products", {
            "sku": "text",
            "weight": "real"
        })
        
        # Try to change a column type (this will create a conflict)
        # In a real scenario, this might happen accidentally
        db_inventory.add_columns("users", {
            "created_at": "text"  # Was timestamp in main!
        })
        
        print("   ✓ Added inventory table")
        print("   ✓ Added columns to products: sku, weight")
        print("   ✓ Modified users.created_at type (will cause conflict)")
        print()
        
        # 7. Switch to main and preview merge from analytics
        print("7. Previewing merge from feature-analytics to main...")
        config.set_active_branch("main")
        
        results = config.merge_structure("feature-analytics", dry_run=True)
        print(f"   Would add tables: {results['new_tables']}")
        print(f"   Would add columns: {results['new_columns']}")
        print()
        
        # 8. Actually merge analytics
        print("8. Merging feature-analytics into main...")
        results = config.merge_structure("feature-analytics")
        print("   ✓ Merged successfully!")
        print(f"   Added tables: {results['new_tables']}")
        print(f"   Added columns: {results['new_columns']}")
        print()
        
        # 9. Try to merge inventory (will show conflict)
        print("9. Attempting to merge feature-inventory...")
        results = config.merge_structure("feature-inventory", dry_run=True)
        
        print(f"   Would add tables: {results['new_tables']}")
        print(f"   Would add columns: {results['new_columns']}")
        if results['type_conflicts']:
            print("   ⚠️  Type conflicts detected:")
            for conflict in results['type_conflicts']:
                print(f"      - {conflict['table']}.{conflict['column']}: "
                      f"{conflict['source_type']} (inventory) vs "
                      f"{conflict['target_type']} (main)")
        print()
        
        # 10. Apply the merge anyway (conflicts are skipped)
        print("10. Applying merge (conflicts will be skipped)...")
        results = config.merge_structure("feature-inventory")
        print("   ✓ Merged successfully!")
        print("   Type conflicts were not merged (kept original types)")
        print()
        
        # 11. Verify final structure
        print("11. Final structure in main branch:")
        db_main = synthdb.connect()
        
        tables = db_main.list_tables()
        for table in sorted(tables, key=lambda t: t['name']):
            columns = db_main.list_columns(table['name'])
            print(f"   Table: {table['name']}")
            for col in columns:
                print(f"     - {col['name']}: {col['data_type']}")
        
        print("\n✓ Demo completed successfully!")
        print("\nKey takeaways:")
        print("- Branches can develop structure independently")
        print("- Merging only adds new tables and columns")
        print("- Type conflicts are detected and reported")
        print("- Original types are preserved (no destructive changes)")
        
    finally:
        # Clean up
        os.chdir("..")
        if demo_dir.exists():
            shutil.rmtree(demo_dir)
        print("\n(Cleaned up merge_demo directory)")


if __name__ == "__main__":
    demo_merge()