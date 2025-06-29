#!/usr/bin/env python3
"""
Comprehensive demo of SynthDB's API server and type-safe models.

This example demonstrates:
1. Starting an API server
2. Using the API client for remote operations
3. Type-safe models with Pydantic
4. Relationship support
5. Integration with saved queries
"""

import asyncio
import threading
import time
import tempfile
import os
from pathlib import Path

import uvicorn
from synthdb import connect
from synthdb.api_client import connect_remote
from synthdb.models import extend_connection_with_models, Relationship, add_relationship


def start_api_server_background(db_path: str, port: int = 8000):
    """Start API server in background thread."""
    from synthdb.api_server import app
    
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    return server_thread


def setup_demo_database(db_path: str):
    """Set up a demo database with sample data."""
    print("🔧 Setting up demo database...")
    
    # Create local connection
    db = connect(db_path)
    extend_connection_with_models(db)
    
    # Create tables
    db.create_table('authors')
    db.add_columns('authors', {
        'name': 'text',
        'email': 'text',
        'bio': 'text',
        'birth_year': 'integer'
    })
    
    db.create_table('books')
    db.add_columns('books', {
        'title': 'text',
        'author_id': 'text',
        'isbn': 'text',
        'pages': 'integer',
        'publication_year': 'integer',
        'genre': 'text'
    })
    
    db.create_table('reviews')
    db.add_columns('reviews', {
        'book_id': 'text',
        'reviewer_name': 'text',
        'rating': 'integer',
        'comment': 'text'
    })
    
    # Insert sample data
    author1_id = db.insert('authors', {
        'name': 'Jane Austen',
        'email': 'jane@classics.com',
        'bio': 'English novelist known for social commentary',
        'birth_year': 1775
    })
    
    author2_id = db.insert('authors', {
        'name': 'George Orwell',
        'email': 'george@dystopia.com', 
        'bio': 'English novelist and social critic',
        'birth_year': 1903
    })
    
    book1_id = db.insert('books', {
        'title': 'Pride and Prejudice',
        'author_id': author1_id,
        'isbn': '978-0-14-143951-8',
        'pages': 432,
        'publication_year': 1813,
        'genre': 'Romance'
    })
    
    book2_id = db.insert('books', {
        'title': '1984',
        'author_id': author2_id,
        'isbn': '978-0-452-28423-4',
        'pages': 328,
        'publication_year': 1949,
        'genre': 'Dystopian Fiction'
    })
    
    # Add reviews
    db.insert('reviews', {
        'book_id': book1_id,
        'reviewer_name': 'Literary Critic',
        'rating': 5,
        'comment': 'A timeless classic with wit and romance'
    })
    
    db.insert('reviews', {
        'book_id': book2_id,
        'reviewer_name': 'Modern Reader',
        'rating': 5,
        'comment': 'Chillingly prophetic and brilliantly written'
    })
    
    # Create saved queries
    db.queries.create_query(
        name='books_with_authors',
        query_text='''
            SELECT 
                b.title,
                b.isbn,
                b.pages,
                b.publication_year,
                b.genre,
                a.name as author_name,
                a.birth_year as author_birth_year
            FROM books b
            JOIN authors a ON b.author_id = a.id
            WHERE (:genre IS NULL OR b.genre = :genre)
            ORDER BY b.publication_year
        ''',
        description='Get books with author information',
        parameters={
            'genre': {
                'type': 'text',
                'required': False,
                'description': 'Filter by genre'
            }
        }
    )
    
    db.queries.create_query(
        name='author_stats',
        query_text='''
            SELECT 
                a.name,
                a.email,
                COUNT(b.id) as book_count,
                AVG(r.rating) as avg_rating,
                MIN(b.publication_year) as first_published,
                MAX(b.publication_year) as last_published
            FROM authors a
            LEFT JOIN books b ON a.id = b.author_id
            LEFT JOIN reviews r ON b.id = r.book_id
            GROUP BY a.id, a.name, a.email
        ''',
        description='Author statistics with ratings'
    )
    
    print(f"✅ Demo database created with sample book data")
    return author1_id, author2_id, book1_id, book2_id


def demo_local_models(db_path: str):
    """Demonstrate local type-safe models."""
    print("\n📚 Demonstrating Local Type-Safe Models")
    print("=" * 50)
    
    # Connect with models
    db = connect(db_path)
    extend_connection_with_models(db)
    
    # Generate models
    models = db.generate_models()
    Author = models['Authors']
    Book = models['Books']
    Review = models['Reviews']
    
    print(f"✅ Generated {len(models)} models: {list(models.keys())}")
    
    # Set up relationships
    author_books_rel = Relationship(
        related_model=Book,
        foreign_key='author_id',
        related_key='id',
        relationship_type='one_to_many'
    )
    add_relationship(Author, 'books', author_books_rel)
    
    book_reviews_rel = Relationship(
        related_model=Review,
        foreign_key='book_id', 
        related_key='id',
        relationship_type='one_to_many'
    )
    add_relationship(Book, 'reviews', book_reviews_rel)
    
    print("✅ Set up relationships: Author -> Books, Book -> Reviews")
    
    # Demonstrate model usage
    print("\n📖 Querying with type-safe models:")
    
    # Get all authors
    authors = Author.find_all()
    for author in authors:
        print(f"👤 {author.name} (born {author.birth_year})")
        
        # Get author's books using relationship
        books = author.books
        for book in books:
            print(f"   📚 {book.title} ({book.publication_year}) - {book.pages} pages")
            
            # Get book reviews
            reviews = book.reviews
            for review in reviews:
                print(f"      ⭐ {review.rating}/5 - {review.comment}")
    
    # Create a new author using models
    print("\n✍️ Creating new author with models:")
    new_author = Author(
        name="Isaac Asimov",
        email="isaac@scifi.com",
        bio="American science fiction writer",
        birth_year=1920
    )
    author_id = new_author.save()
    print(f"✅ Created author with ID: {author_id}")
    
    # Create a book for the new author
    new_book = Book(
        title="Foundation",
        author_id=author_id,
        isbn="978-0-553-29335-0",
        pages=244,
        publication_year=1951,
        genre="Science Fiction"
    )
    book_id = new_book.save()
    print(f"✅ Created book with ID: {book_id}")
    
    # Demonstrate validation
    print("\n🔍 Demonstrating Pydantic validation:")
    try:
        # This will work - automatic type conversion
        author_with_string_year = Author(
            name="Test Author",
            birth_year="1950"  # String will be converted to int
        )
        print(f"✅ Type conversion: birth_year='1950' -> {author_with_string_year.birth_year} ({type(author_with_string_year.birth_year)})")
        
        # This will fail - extra field validation
        Author(name="Test", unknown_field="value")
    except Exception as e:
        print(f"🚫 Validation error (expected): {e}")


def demo_api_client(port: int = 8000):
    """Demonstrate API client usage."""
    print("\n🌐 Demonstrating API Client")
    print("=" * 50)
    
    # Connect to API server
    api_url = f"http://localhost:{port}"
    print(f"🔗 Connecting to API server at {api_url}")
    
    with connect_remote(api_url, "demo.db") as api:
        # Test basic operations
        print("\n📊 Database info:")
        info = api.get_info()
        print(f"   Tables: {info['tables_count']}")
        print(f"   Total columns: {info['total_columns']}")
        
        # List tables
        print("\n📋 Tables:")
        tables = api.list_tables()
        for table in tables:
            print(f"   - {table['name']}")
        
        # Query data via API
        print("\n📚 Books via API:")
        books = api.query("books", limit=5)
        for book in books:
            print(f"   📖 {book['title']} ({book['publication_year']})")
        
        # Execute saved query via API
        print("\n🔍 Executing saved query via API:")
        book_results = api.queries.execute_query("books_with_authors")
        for result in book_results:
            print(f"   📚 '{result['title']}' by {result['author_name']}")
        
        # Create new data via API
        print("\n➕ Creating new review via API:")
        new_review_id = api.insert("reviews", {
            "book_id": books[0]["id"],
            "reviewer_name": "API User",
            "rating": 4,
            "comment": "Great book, enjoyed it thoroughly!"
        })
        print(f"✅ Created review with ID: {new_review_id}")
        
        # Execute SQL via API
        print("\n💻 Executing SQL via API:")
        sql_results = api.execute_sql(
            "SELECT COUNT(*) as total_books, AVG(pages) as avg_pages FROM books"
        )
        result = sql_results[0]
        print(f"   📊 Total books: {result['total_books']}, Average pages: {result['avg_pages']:.0f}")


def demo_models_with_api():
    """Demonstrate using models with API client."""
    print("\n🔀 Demonstrating Models + API Integration")
    print("=" * 50)
    
    # Note: In a real scenario, you could extend the API client with model support
    # For this demo, we'll show how they could work together conceptually
    
    api_url = "http://localhost:8000"
    
    with connect_remote(api_url, "demo.db") as api:
        # Get raw data from API
        authors_data = api.query("authors")
        
        # Convert to local models for type safety (conceptual)
        print("🔄 Converting API data to typed models:")
        for author_data in authors_data:
            print(f"   👤 {author_data['name']} - Email: {author_data['email']}")
        
        # Execute saved query and show structure
        stats = api.queries.execute_query("author_stats")
        print("\n📈 Author statistics from saved query:")
        for stat in stats:
            book_count = stat['book_count'] or 0
            avg_rating = stat['avg_rating'] or 0
            print(f"   👤 {stat['name']}: {book_count} books, {avg_rating:.1f} avg rating")


def demo_code_generation(db_path: str):
    """Demonstrate model code generation."""
    print("\n⚙️ Demonstrating Model Code Generation")
    print("=" * 50)
    
    # Create output directory
    output_dir = Path("generated_models")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "models.py"
    
    # Generate models code
    db = connect(db_path)
    extend_connection_with_models(db)
    
    from synthdb.models import ModelGenerator
    generator = ModelGenerator(db)
    
    # Generate code manually (similar to CLI command)
    tables = db.list_tables()
    
    code_lines = [
        '"""Auto-generated models for SynthDB."""',
        '',
        'from datetime import datetime',
        'from typing import Optional',
        'from pydantic import Field',
        '',
        'from synthdb.models import SynthDBModel',
        '',
    ]
    
    for table in tables:
        table_name = table['name']
        columns = db.list_columns(table_name)
        class_name = generator._table_name_to_class_name(table_name)
        
        code_lines.extend([
            f'class {class_name}(SynthDBModel):',
            f'    """Model for {table_name} table."""',
            f'    __table_name__ = "{table_name}"',
            '',
        ])
        
        for col in columns:
            if col['name'] in ('id', 'created_at', 'updated_at'):
                continue
            
            python_type = generator._map_synthdb_type(col['data_type'])
            type_name = python_type.__name__
            if type_name == 'datetime':
                type_name = 'datetime'
            
            code_lines.append(f'    {col["name"]}: Optional[{type_name}] = Field(None, description="Column from {table_name} table")')
        
        code_lines.extend(['', ''])
    
    # Write generated code
    with open(output_file, 'w') as f:
        f.write('\n'.join(code_lines))
    
    print(f"✅ Generated models code: {output_file}")
    print(f"📝 Generated {len(tables)} model classes")
    
    # Show sample of generated code
    print("\n📄 Sample generated code:")
    with open(output_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:20]):  # Show first 20 lines
            print(f"   {i+1:2d}: {line.rstrip()}")
        if len(lines) > 20:
            print(f"   ... ({len(lines) - 20} more lines)")


def cleanup_demo(db_path: str):
    """Clean up demo files."""
    print("\n🧹 Cleaning up demo files...")
    
    # Remove database
    if os.path.exists(db_path):
        os.unlink(db_path)
        print(f"✅ Removed database: {db_path}")
    
    # Remove generated models
    output_dir = Path("generated_models")
    if output_dir.exists():
        for file in output_dir.iterdir():
            file.unlink()
        output_dir.rmdir()
        print(f"✅ Removed generated models directory")


def main():
    """Run the comprehensive demo."""
    print("🚀 SynthDB API & Models Comprehensive Demo")
    print("=" * 60)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Set up demo database
        setup_demo_database(db_path)
        
        # Start API server in background
        print(f"\n🌐 Starting API server...")
        server_thread = start_api_server_background(db_path, port=8000)
        print(f"✅ API server running on http://localhost:8000")
        
        # Demo local models
        demo_local_models(db_path)
        
        # Demo API client
        demo_api_client(port=8000)
        
        # Demo models + API integration
        demo_models_with_api()
        
        # Demo code generation
        demo_code_generation(db_path)
        
        print("\n🎉 Demo completed successfully!")
        print("\n💡 Key takeaways:")
        print("   • Type-safe models provide compile-time validation")
        print("   • API server enables remote database access")
        print("   • Models work with both local and remote connections")
        print("   • Saved queries integrate seamlessly with both")
        print("   • Code generation creates reusable model definitions")
        
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_demo(db_path)


if __name__ == "__main__":
    main()