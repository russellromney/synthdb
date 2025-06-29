"""
Demo of safe SQL execution feature in SynthDB.

This example shows how to execute custom SQL queries safely
against SynthDB databases with built-in validation and security.
"""

import synthdb
import os


def main():
    """Demonstrate safe SQL execution."""
    db_path = 'sql_demo.db'
    
    # Clean up any existing database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Create connection
    db = synthdb.connect(db_path)
    print("Created SynthDB connection")
    
    # Create schema
    print("\n1. Setting up sample data...")
    
    # Create users table
    db.create_table('users')
    db.add_columns('users', {
        'name': 'text',
        'email': 'text',
        'age': 25,
        'department': 'text',
        'salary': 50000.0,
        'active': True
    })
    
    # Create products table
    db.create_table('products')
    db.add_columns('products', {
        'name': 'text',
        'category': 'text',
        'price': 19.99,
        'stock': 100,
        'discontinued': False
    })
    
    # Insert sample users
    users_data = [
        {'name': 'Alice Johnson', 'email': 'alice@company.com', 'age': 30, 'department': 'Engineering', 'salary': 85000, 'active': True},
        {'name': 'Bob Smith', 'email': 'bob@company.com', 'age': 25, 'department': 'Sales', 'salary': 65000, 'active': True},
        {'name': 'Charlie Brown', 'email': 'charlie@company.com', 'age': 35, 'department': 'Engineering', 'salary': 95000, 'active': True},
        {'name': 'Diana Prince', 'email': 'diana@company.com', 'age': 28, 'department': 'Marketing', 'salary': 70000, 'active': False},
        {'name': 'Eve Wilson', 'email': 'eve@company.com', 'age': 45, 'department': 'Sales', 'salary': 75000, 'active': True},
    ]
    
    for user in users_data:
        db.insert('users', user)
    
    # Insert sample products
    products_data = [
        {'name': 'Laptop Pro', 'category': 'Electronics', 'price': 1299.99, 'stock': 50, 'discontinued': False},
        {'name': 'Wireless Mouse', 'category': 'Electronics', 'price': 29.99, 'stock': 200, 'discontinued': False},
        {'name': 'Office Chair', 'category': 'Furniture', 'price': 399.99, 'stock': 30, 'discontinued': False},
        {'name': 'Desk Lamp', 'category': 'Furniture', 'price': 49.99, 'stock': 100, 'discontinued': False},
        {'name': 'Old Monitor', 'category': 'Electronics', 'price': 199.99, 'stock': 5, 'discontinued': True},
    ]
    
    for product in products_data:
        db.insert('products', product)
    
    print("Sample data created successfully")
    
    # 2. Basic SELECT queries
    print("\n2. Basic SELECT queries:")
    
    # Select all users
    results = db.execute_sql("SELECT * FROM users WHERE active = 1")
    print(f"\nActive users: {len(results)}")
    for user in results:
        print(f"  - {user['name']} ({user['department']})")
    
    # 3. Queries with parameters (safe from SQL injection)
    print("\n3. Parameterized queries (SQL injection safe):")
    
    min_age = 30
    department = 'Engineering'
    results = db.execute_sql(
        "SELECT name, age, salary FROM users WHERE age >= ? AND department = ?",
        [min_age, department]
    )
    print(f"\nEngineering staff aged {min_age}+:")
    for user in results:
        print(f"  - {user['name']}, age {user['age']}, salary ${user['salary']:,.2f}")
    
    # 4. Aggregation queries
    print("\n4. Aggregation queries:")
    
    # Department statistics
    results = db.execute_sql("""
        SELECT 
            department,
            COUNT(*) as employee_count,
            AVG(salary) as avg_salary,
            MIN(age) as youngest,
            MAX(age) as oldest
        FROM users
        WHERE active = 1
        GROUP BY department
        ORDER BY avg_salary DESC
    """)
    
    print("\nDepartment Statistics:")
    for dept in results:
        print(f"  {dept['department']}:")
        print(f"    - Employees: {dept['employee_count']}")
        print(f"    - Avg Salary: ${dept['avg_salary']:,.2f}")
        print(f"    - Age Range: {dept['youngest']}-{dept['oldest']}")
    
    # 5. Product analytics
    print("\n5. Product analytics:")
    
    results = db.execute_sql("""
        SELECT 
            category,
            COUNT(*) as product_count,
            SUM(stock) as total_inventory,
            AVG(price) as avg_price,
            MIN(price) as min_price,
            MAX(price) as max_price
        FROM products
        WHERE discontinued = 0
        GROUP BY category
    """)
    
    print("\nProduct Category Analysis:")
    for cat in results:
        print(f"  {cat['category']}:")
        print(f"    - Products: {cat['product_count']}")
        print(f"    - Total Stock: {cat['total_inventory']}")
        print(f"    - Price Range: ${cat['min_price']} - ${cat['max_price']}")
        print(f"    - Avg Price: ${cat['avg_price']:.2f}")
    
    # 6. Complex queries with subqueries
    print("\n6. Complex queries:")
    
    # Find users earning above department average
    results = db.execute_sql("""
        SELECT 
            u.name,
            u.department,
            u.salary,
            dept_avg.avg_salary,
            u.salary - dept_avg.avg_salary as above_average
        FROM users u
        JOIN (
            SELECT department, AVG(salary) as avg_salary
            FROM users
            WHERE active = 1
            GROUP BY department
        ) dept_avg ON u.department = dept_avg.department
        WHERE u.salary > dept_avg.avg_salary
        ORDER BY above_average DESC
    """)
    
    print("\nEmployees earning above department average:")
    for emp in results:
        print(f"  - {emp['name']} ({emp['department']}): ${emp['salary']:,.2f} "
              f"(+${emp['above_average']:,.2f} above avg)")
    
    # 7. Demonstrating safety features
    print("\n7. Safety features demonstration:")
    
    # These queries will be rejected
    unsafe_queries = [
        ("INSERT", "INSERT INTO users (name) VALUES ('Hacker')"),
        ("UPDATE", "UPDATE users SET salary = 1000000"),
        ("DELETE", "DELETE FROM users"),
        ("DROP", "DROP TABLE users"),
        ("Internal table access", "SELECT * FROM table_definitions"),
        ("Multiple statements", "SELECT * FROM users; DROP TABLE users"),
    ]
    
    for desc, query in unsafe_queries:
        try:
            db.execute_sql(query)
            print(f"  ❌ {desc}: Should have been blocked!")
        except ValueError as e:
            print(f"  ✅ {desc}: Blocked - {e}")
    
    # 8. Working with timestamps
    print("\n8. Timestamp queries:")
    
    # Get recently added records
    results = db.execute_sql("""
        SELECT 
            name,
            created_at,
            strftime('%Y-%m-%d %H:%M', created_at) as created_formatted
        FROM users
        ORDER BY created_at DESC
        LIMIT 3
    """)
    
    print("\nMost recently added users:")
    for user in results:
        print(f"  - {user['name']} (added: {user['created_formatted']})")
    
    # Clean up
    print("\n✨ Demo completed successfully!")
    print(f"\nDatabase saved to: {db_path}")
    print("You can connect to it and run more queries:")
    print("  db = synthdb.connect('sql_demo.db')")
    print("  results = db.execute_sql('SELECT * FROM users')")


if __name__ == "__main__":
    main()