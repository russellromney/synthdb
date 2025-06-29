"""
Populate test branch with sample tables and data for testing.
"""

import synthdb
import random
from datetime import datetime, timedelta

def main():
    # Connect to the database (will use test branch automatically)
    db = synthdb.connect()
    print("Connected to test branch database")
    
    # 1. Create customers table
    print("\n1. Creating customers table...")
    db.create_table('customers')
    db.add_columns('customers', {
        'first_name': 'text',
        'last_name': 'text',
        'email': 'text',
        'phone': 'text',
        'date_of_birth': '1990-01-01',
        'loyalty_points': 0,
        'is_active': True,
        'created_at': datetime.now().isoformat()
    })
    
    # Add customer data
    customers = [
        {'first_name': 'John', 'last_name': 'Doe', 'email': 'john.doe@email.com', 'phone': '555-0101', 'date_of_birth': '1985-03-15', 'loyalty_points': 150, 'is_active': True},
        {'first_name': 'Jane', 'last_name': 'Smith', 'email': 'jane.smith@email.com', 'phone': '555-0102', 'date_of_birth': '1990-07-22', 'loyalty_points': 275, 'is_active': True},
        {'first_name': 'Bob', 'last_name': 'Johnson', 'email': 'bob.j@email.com', 'phone': '555-0103', 'date_of_birth': '1978-11-30', 'loyalty_points': 50, 'is_active': False},
        {'first_name': 'Alice', 'last_name': 'Williams', 'email': 'alice.w@email.com', 'phone': '555-0104', 'date_of_birth': '1992-05-18', 'loyalty_points': 420, 'is_active': True},
        {'first_name': 'Charlie', 'last_name': 'Brown', 'email': 'charlie.brown@email.com', 'phone': '555-0105', 'date_of_birth': '1988-09-10', 'loyalty_points': 180, 'is_active': True},
    ]
    
    customer_ids = {}
    for customer in customers:
        cid = db.insert('customers', customer)
        customer_ids[customer['email']] = cid
        print(f"  Added customer: {customer['first_name']} {customer['last_name']}")
    
    # 2. Create products table
    print("\n2. Creating products table...")
    db.create_table('products')
    db.add_columns('products', {
        'sku': 'text',
        'name': 'text',
        'description': 'text',
        'category': 'text',
        'price': 0.0,
        'cost': 0.0,
        'stock_quantity': 0,
        'reorder_level': 10,
        'is_discontinued': False,
        'weight_kg': 0.0
    })
    
    # Add product data
    products = [
        {'sku': 'LAPTOP-001', 'name': 'Pro Laptop 15"', 'description': 'High-performance laptop with 16GB RAM', 'category': 'Electronics', 'price': 1299.99, 'cost': 850.00, 'stock_quantity': 25, 'reorder_level': 10, 'weight_kg': 2.1},
        {'sku': 'MOUSE-WL-01', 'name': 'Wireless Mouse', 'description': 'Ergonomic wireless mouse with USB receiver', 'category': 'Electronics', 'price': 29.99, 'cost': 12.50, 'stock_quantity': 150, 'reorder_level': 50, 'weight_kg': 0.1},
        {'sku': 'DESK-OAK-01', 'name': 'Oak Standing Desk', 'description': 'Adjustable height standing desk', 'category': 'Furniture', 'price': 599.99, 'cost': 350.00, 'stock_quantity': 8, 'reorder_level': 5, 'weight_kg': 45.0},
        {'sku': 'CHAIR-ERG-01', 'name': 'Ergonomic Office Chair', 'description': 'Lumbar support office chair', 'category': 'Furniture', 'price': 399.99, 'cost': 225.00, 'stock_quantity': 15, 'reorder_level': 10, 'weight_kg': 18.5},
        {'sku': 'HDMI-CBL-2M', 'name': 'HDMI Cable 2m', 'description': 'High-speed HDMI 2.1 cable', 'category': 'Accessories', 'price': 19.99, 'cost': 5.00, 'stock_quantity': 200, 'reorder_level': 100, 'weight_kg': 0.2},
        {'sku': 'WEBCAM-HD', 'name': 'HD Webcam', 'description': '1080p webcam with microphone', 'category': 'Electronics', 'price': 79.99, 'cost': 35.00, 'stock_quantity': 45, 'reorder_level': 20, 'weight_kg': 0.3},
        {'sku': 'MONITOR-27', 'name': '27" 4K Monitor', 'description': 'IPS panel 4K monitor', 'category': 'Electronics', 'price': 449.99, 'cost': 280.00, 'stock_quantity': 12, 'reorder_level': 8, 'weight_kg': 6.8},
        {'sku': 'KEYBOARD-MECH', 'name': 'Mechanical Keyboard', 'description': 'RGB mechanical gaming keyboard', 'category': 'Electronics', 'price': 119.99, 'cost': 65.00, 'stock_quantity': 30, 'reorder_level': 15, 'weight_kg': 1.2},
    ]
    
    product_ids = {}
    for product in products:
        pid = db.insert('products', product)
        product_ids[product['sku']] = pid
        print(f"  Added product: {product['name']} ({product['sku']})")
    
    # 3. Create orders table
    print("\n3. Creating orders table...")
    db.create_table('orders')
    db.add_columns('orders', {
        'order_number': 'text',
        'customer_id': 'text',
        'order_date': datetime.now().isoformat(),
        'status': 'text',
        'subtotal': 0.0,
        'tax_amount': 0.0,
        'shipping_amount': 0.0,
        'total_amount': 0.0,
        'payment_method': 'text',
        'shipping_address': 'text',
        'notes': 'text'
    })
    
    # Add order data
    order_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
    payment_methods = ['credit_card', 'paypal', 'bank_transfer']
    
    orders = []
    order_date = datetime.now() - timedelta(days=30)
    
    for i in range(15):
        customer_email = random.choice(list(customer_ids.keys()))
        status = random.choice(order_statuses)
        payment = random.choice(payment_methods)
        subtotal = round(random.uniform(50, 1500), 2)
        tax = round(subtotal * 0.08, 2)
        shipping = 10.00 if subtotal < 100 else 0
        
        order = {
            'order_number': f'ORD-2024-{1000 + i}',
            'customer_id': customer_ids[customer_email],
            'order_date': (order_date + timedelta(days=random.randint(0, 30))).isoformat(),
            'status': status,
            'subtotal': subtotal,
            'tax_amount': tax,
            'shipping_amount': shipping,
            'total_amount': subtotal + tax + shipping,
            'payment_method': payment,
            'shipping_address': f'{random.randint(100, 999)} Main St, City, State 12345',
            'notes': 'Express delivery requested' if random.random() > 0.8 else None
        }
        
        order_id = db.insert('orders', order)
        orders.append((order_id, order))
        print(f"  Added order: {order['order_number']} - ${order['total_amount']:.2f}")
    
    # 4. Create order_items table
    print("\n4. Creating order_items table...")
    db.create_table('order_items')
    db.add_columns('order_items', {
        'order_id': 'text',
        'product_id': 'text',
        'quantity': 1,
        'unit_price': 0.0,
        'discount_percent': 0.0,
        'line_total': 0.0
    })
    
    # Add order items
    for order_id, order in orders:
        # Each order has 1-4 items
        num_items = random.randint(1, 4)
        selected_products = random.sample(list(product_ids.keys()), num_items)
        
        for sku in selected_products:
            product = next(p for p in products if p['sku'] == sku)
            quantity = random.randint(1, 3)
            discount = random.choice([0, 5, 10, 15]) if random.random() > 0.7 else 0
            unit_price = product['price']
            line_total = quantity * unit_price * (1 - discount/100)
            
            db.insert('order_items', {
                'order_id': order_id,
                'product_id': product_ids[sku],
                'quantity': quantity,
                'unit_price': unit_price,
                'discount_percent': discount,
                'line_total': round(line_total, 2)
            })
    
    print("  Added order items for all orders")
    
    # 5. Create inventory_log table
    print("\n5. Creating inventory_log table...")
    db.create_table('inventory_log')
    db.add_columns('inventory_log', {
        'product_id': 'text',
        'transaction_type': 'text',  # 'purchase', 'sale', 'adjustment', 'return'
        'quantity_change': 0,
        'reference_id': 'text',
        'timestamp': datetime.now().isoformat(),
        'notes': 'text'
    })
    
    # Add some inventory transactions
    transaction_types = ['purchase', 'sale', 'adjustment', 'return']
    for _ in range(20):
        product_sku = random.choice(list(product_ids.keys()))
        trans_type = random.choice(transaction_types)
        
        if trans_type == 'purchase':
            qty = random.randint(10, 100)
        elif trans_type == 'sale':
            qty = -random.randint(1, 10)
        elif trans_type == 'return':
            qty = random.randint(1, 3)
        else:  # adjustment
            qty = random.randint(-5, 5)
        
        db.insert('inventory_log', {
            'product_id': product_ids[product_sku],
            'transaction_type': trans_type,
            'quantity_change': qty,
            'reference_id': f'REF-{random.randint(1000, 9999)}',
            'timestamp': (datetime.now() - timedelta(days=random.randint(0, 30))).isoformat(),
            'notes': 'Cycle count adjustment' if trans_type == 'adjustment' else None
        })
    
    print("  Added inventory transactions")
    
    # 6. Create employees table (with different structure than users)
    print("\n6. Creating employees table...")
    db.create_table('employees')
    db.add_columns('employees', {
        'employee_id': 'text',
        'first_name': 'text',
        'last_name': 'text',
        'department': 'text',
        'position': 'text',
        'hire_date': '2020-01-01',
        'salary': 50000.0,
        'commission_rate': 0.0,
        'manager_id': 'text',
        'is_manager': False,
        'office_location': 'text'
    })
    
    # Add employee data
    departments = ['Sales', 'Engineering', 'Marketing', 'Operations', 'Finance']
    positions = {
        'Sales': ['Sales Rep', 'Senior Sales Rep', 'Sales Manager'],
        'Engineering': ['Junior Developer', 'Senior Developer', 'Tech Lead', 'Engineering Manager'],
        'Marketing': ['Marketing Coordinator', 'Marketing Specialist', 'Marketing Manager'],
        'Operations': ['Operations Analyst', 'Operations Manager'],
        'Finance': ['Accountant', 'Senior Accountant', 'Finance Manager']
    }
    
    employees = []
    for i in range(12):
        dept = random.choice(departments)
        position = random.choice(positions[dept])
        is_manager = 'Manager' in position
        
        employee = {
            'employee_id': f'EMP-{1000 + i}',
            'first_name': f'Employee{i+1}',
            'last_name': random.choice(['Smith', 'Jones', 'Wilson', 'Taylor', 'Davis']),
            'department': dept,
            'position': position,
            'hire_date': (datetime.now() - timedelta(days=random.randint(30, 1000))).date().isoformat(),
            'salary': random.randint(45000, 120000),
            'commission_rate': random.uniform(0.05, 0.15) if dept == 'Sales' else 0,
            'manager_id': None if is_manager else f'EMP-{1000 + random.randint(0, i)}',
            'is_manager': is_manager,
            'office_location': random.choice(['New York', 'San Francisco', 'Chicago', 'Remote'])
        }
        
        emp_id = db.insert('employees', employee)
        employees.append(employee)
        print(f"  Added employee: {employee['first_name']} {employee['last_name']} - {employee['position']}")
    
    # Print summary
    print("\n" + "="*60)
    print("Test data creation complete!")
    print("="*60)
    
    # Show table summary
    tables = db.list_tables()
    print("\nTables created:")
    for table in tables:
        columns = db.list_columns(table['name'])
        print(f"\n{table['name']} ({len(columns)} columns):")
        for col in columns:
            print(f"  - {col['name']} ({col['data_type']})")
    
    # Show record counts
    print("\nRecord counts:")
    for table in tables:
        results = db.query(table['name'])
        print(f"  {table['name']}: {len(results)} records")
    
    # Example queries
    print("\n" + "="*60)
    print("Example SQL queries you can run:")
    print("="*60)
    
    example_queries = [
        "SELECT * FROM customers WHERE is_active = 1",
        "SELECT category, COUNT(*) as count, AVG(price) as avg_price FROM products GROUP BY category",
        "SELECT c.first_name, c.last_name, COUNT(o.row_id) as order_count FROM customers c LEFT JOIN orders o ON c.row_id = o.customer_id GROUP BY c.row_id",
        "SELECT * FROM products WHERE stock_quantity < reorder_level",
        "SELECT department, COUNT(*) as count, AVG(salary) as avg_salary FROM employees GROUP BY department",
        "SELECT DATE(order_date) as date, COUNT(*) as orders, SUM(total_amount) as revenue FROM orders GROUP BY DATE(order_date)"
    ]
    
    for query in example_queries:
        print(f"\nsdb sql \"{query}\"")


if __name__ == "__main__":
    main()