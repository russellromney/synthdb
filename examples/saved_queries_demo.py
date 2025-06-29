#!/usr/bin/env python3
"""
Comprehensive demonstration of SynthDB saved queries functionality.

This example shows how to:
1. Create and manage saved queries with parameters
2. Execute queries with different parameter values
3. Use saved queries for business analytics
4. Handle complex queries with joins and aggregations
"""

import tempfile
import os
from synthdb import connect


def main():
    # Create a temporary database for this demo
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        print("🚀 SynthDB Saved Queries Demo")
        print("=" * 50)
        
        # Connect to database
        db = connect(db_path)
        print(f"📁 Connected to database: {db_path}")
        
        # Create sample tables and data
        setup_sample_data(db)
        
        # Demonstrate saved queries
        demonstrate_saved_queries(db)
        
        # Demonstrate CLI usage
        demonstrate_cli_usage(db_path)
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.unlink(db_path)
        print("\n✅ Demo completed successfully!")


def setup_sample_data(db):
    """Set up sample e-commerce data."""
    print("\n📊 Setting up sample e-commerce data...")
    
    # Create customers table
    db.create_table('customers')
    db.add_columns('customers', {
        'name': 'text',
        'email': 'text',
        'age': 'integer',
        'status': 'text',
        'registration_date': 'timestamp'
    })
    
    # Create products table
    db.create_table('products')
    db.add_columns('products', {
        'name': 'text',
        'category': 'text',
        'price': 'real',
        'in_stock': 'integer'
    })
    
    # Create orders table
    db.create_table('orders')
    db.add_columns('orders', {
        'customer_id': 'text',
        'product_id': 'text',
        'quantity': 'integer',
        'total': 'real',
        'status': 'text',
        'order_date': 'timestamp'
    })
    
    # Insert sample customers
    customers_data = [
        {'name': 'Alice Johnson', 'email': 'alice@example.com', 'age': 28, 'status': 'active', 'registration_date': '2024-01-15'},
        {'name': 'Bob Smith', 'email': 'bob@example.com', 'age': 35, 'status': 'active', 'registration_date': '2024-02-20'},
        {'name': 'Charlie Brown', 'email': 'charlie@example.com', 'age': 22, 'status': 'inactive', 'registration_date': '2024-03-10'},
        {'name': 'Diana Prince', 'email': 'diana@example.com', 'age': 31, 'status': 'active', 'registration_date': '2024-01-05'}
    ]
    
    customer_ids = []
    for customer in customers_data:
        customer_id = db.insert('customers', customer)
        customer_ids.append(customer_id)
    
    # Insert sample products
    products_data = [
        {'name': 'Laptop', 'category': 'Electronics', 'price': 999.99, 'in_stock': 50},
        {'name': 'Mouse', 'category': 'Electronics', 'price': 29.99, 'in_stock': 200},
        {'name': 'Desk Chair', 'category': 'Furniture', 'price': 199.99, 'in_stock': 25},
        {'name': 'Coffee Mug', 'category': 'Kitchenware', 'price': 14.99, 'in_stock': 100}
    ]
    
    product_ids = []
    for product in products_data:
        product_id = db.insert('products', product)
        product_ids.append(product_id)
    
    # Insert sample orders
    orders_data = [
        {'customer_id': customer_ids[0], 'product_id': product_ids[0], 'quantity': 1, 'total': 999.99, 'status': 'completed', 'order_date': '2024-06-01'},
        {'customer_id': customer_ids[0], 'product_id': product_ids[1], 'quantity': 2, 'total': 59.98, 'status': 'completed', 'order_date': '2024-06-02'},
        {'customer_id': customer_ids[1], 'product_id': product_ids[2], 'quantity': 1, 'total': 199.99, 'status': 'completed', 'order_date': '2024-06-05'},
        {'customer_id': customer_ids[1], 'product_id': product_ids[3], 'quantity': 3, 'total': 44.97, 'status': 'pending', 'order_date': '2024-06-20'},
        {'customer_id': customer_ids[3], 'product_id': product_ids[0], 'quantity': 1, 'total': 999.99, 'status': 'completed', 'order_date': '2024-06-15'}
    ]
    
    for order in orders_data:
        db.insert('orders', order)
    
    print(f"   ✓ Created {len(customers_data)} customers")
    print(f"   ✓ Created {len(products_data)} products") 
    print(f"   ✓ Created {len(orders_data)} orders")


def demonstrate_saved_queries(db):
    """Demonstrate various saved query features."""
    print("\n💾 Creating and executing saved queries...")
    
    # 1. Simple query without parameters
    print("\n1️⃣ Simple query: All active customers")
    active_customers_query = db.queries.create_query(
        name='active_customers',
        query_text="SELECT name, email, age FROM customers WHERE status = 'active'",
        description='Get all active customers'
    )
    
    results = db.queries.execute_query('active_customers')
    print(f"   ✓ Found {len(results)} active customers:")
    for customer in results:
        print(f"     - {customer['name']} ({customer['email']})")
    
    # 2. Parameterized query with defaults
    print("\n2️⃣ Parameterized query: Customers by age range")
    age_filter_query = db.queries.create_query(
        name='customers_by_age',
        query_text='SELECT name, email, age FROM customers WHERE age >= :min_age AND age <= :max_age AND status = :status',
        description='Get customers within an age range',
        parameters={
            'min_age': {'type': 'integer', 'default': 18, 'description': 'Minimum age'},
            'max_age': {'type': 'integer', 'default': 100, 'description': 'Maximum age'}, 
            'status': {'type': 'text', 'default': 'active', 'description': 'Customer status'}
        }
    )
    
    # Execute with default parameters
    results = db.queries.execute_query('customers_by_age')
    print(f"   ✓ All active customers: {len(results)} found")
    
    # Execute with specific parameters
    results = db.queries.execute_query('customers_by_age', min_age=25, max_age=35)
    print(f"   ✓ Active customers aged 25-35: {len(results)} found")
    for customer in results:
        print(f"     - {customer['name']} (age {customer['age']})")
    
    # 3. Complex analytical query with joins
    print("\n3️⃣ Complex analytics: Customer lifetime value")
    customer_analytics_query = db.queries.create_query(
        name='customer_lifetime_value',
        query_text='''
            SELECT 
                c.name,
                c.email,
                COUNT(o.id) as total_orders,
                SUM(o.total) as lifetime_value,
                AVG(o.total) as avg_order_value,
                MAX(o.order_date) as last_order_date
            FROM customers c
            LEFT JOIN orders o ON c.id = o.customer_id
            WHERE c.status = :status
            GROUP BY c.id, c.name, c.email
            HAVING COUNT(o.id) > 0
            ORDER BY lifetime_value DESC
        ''',
        description='Calculate customer lifetime value and statistics',
        parameters={
            'status': {'type': 'text', 'default': 'active'}
        }
    )
    
    results = db.queries.execute_query('customer_lifetime_value')
    print(f"   ✓ Customer analytics for {len(results)} customers:")
    for customer in results:
        print(f"     - {customer['name']}: ${customer['lifetime_value']:.2f} lifetime value, {customer['total_orders']} orders")
    
    # 4. Product performance query
    print("\n4️⃣ Product performance analysis")
    product_performance_query = db.queries.create_query(
        name='product_performance',
        query_text='''
            SELECT 
                p.name,
                p.category,
                p.price,
                COALESCE(SUM(o.quantity), 0) as units_sold,
                COALESCE(SUM(o.total), 0) as revenue,
                COUNT(DISTINCT o.customer_id) as unique_customers
            FROM products p
            LEFT JOIN orders o ON p.id = o.product_id AND o.status = 'completed'
            GROUP BY p.id, p.name, p.category, p.price
            ORDER BY revenue DESC
        ''',
        description='Analyze product sales performance'
    )
    
    # All products
    results = db.queries.execute_query('product_performance')
    print(f"   ✓ Performance for all products:")
    for product in results:
        print(f"     - {product['name']}: {product['units_sold']} units, ${product['revenue']:.2f} revenue")
    
    # 5. Category-specific query
    print("\n5️⃣ Electronics performance")
    electronics_query = db.queries.create_query(
        name='electronics_performance',
        query_text='''
            SELECT 
                p.name,
                p.price,
                COALESCE(SUM(o.quantity), 0) as units_sold,
                COALESCE(SUM(o.total), 0) as revenue
            FROM products p
            LEFT JOIN orders o ON p.id = o.product_id AND o.status = 'completed'
            WHERE p.category = :category
            GROUP BY p.id, p.name, p.price
            ORDER BY revenue DESC
        ''',
        description='Analyze performance for specific category',
        parameters={
            'category': {'type': 'text', 'required': True, 'description': 'Product category to analyze'}
        }
    )
    
    results = db.queries.execute_query('electronics_performance', category='Electronics')
    print(f"   ✓ Electronics performance: {len(results)} products")
    for product in results:
        print(f"     - {product['name']}: {product['units_sold']} units, ${product['revenue']:.2f} revenue")
    
    # 6. List all saved queries
    print("\n📋 All saved queries:")
    all_queries = db.queries.list_queries()
    for query in all_queries:
        param_count = len(query.parameters) if query.parameters else 0
        print(f"   - {query.name}: {query.description} ({param_count} parameters)")


def demonstrate_cli_usage(db_path):
    """Demonstrate CLI commands for saved queries."""
    print("\n🖥️  CLI Usage Examples:")
    print(f"   Database path: {db_path}")
    print("\n   Available CLI commands:")
    print("   # Create a query from command line")
    print(f'   sdb query create my_query --query "SELECT * FROM customers" --path {db_path}')
    print("\n   # List all saved queries")
    print(f"   sdb query list --path {db_path}")
    print("\n   # Show query details")
    print(f"   sdb query show active_customers --path {db_path}")
    print("\n   # Execute a query with parameters")
    print(f"   sdb query exec customers_by_age --param min_age=25 --param max_age=35 --path {db_path}")
    print("\n   # Delete a query")
    print(f"   sdb query delete my_query --path {db_path}")


if __name__ == "__main__":
    main()