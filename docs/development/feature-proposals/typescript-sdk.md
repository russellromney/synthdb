# SynthDB TypeScript SDK Feature Request

## Overview

This proposal outlines a TypeScript SDK for SynthDB that provides a type-safe, developer-friendly interface to the SynthDB API server. The SDK will enable JavaScript/TypeScript applications to interact with SynthDB databases through a fluent API with full TypeScript support, automatic type inference, and built-in authentication mechanisms.

## Goals

- Provide complete type-safe access to all SynthDB API features
- Support both browser and Node.js environments
- Enable row-level security through authentication
- Offer intuitive developer experience with auto-completion
- Support real-time subscriptions (future enhancement)
- Minimize bundle size for browser applications

## Architecture

### SDK Design Principles

1. **Type Safety**: Full TypeScript support with generics for table schemas
2. **Fluent API**: Chainable methods for intuitive query building
3. **Lazy Evaluation**: Queries only execute when needed
4. **Error Handling**: Consistent error types with detailed messages
5. **Tree-Shakeable**: Modular design for optimal bundle sizes

### Core Components

```
synthdb-ts/
├── src/
│   ├── client/           # Main client class
│   ├── auth/            # Authentication providers
│   ├── tables/          # Table operations
│   ├── queries/         # Query builders
│   ├── types/           # TypeScript type definitions
│   ├── errors/          # Error classes
│   └── utils/           # Utility functions
├── tests/
└── examples/
```

## Authentication Options

### Option 1: No Row-Level Security (Simple Mode)

For development or internal applications without authentication requirements:

```typescript
import { SynthDB } from '@synthdb/client';

// No authentication required
const db = new SynthDB({
  url: 'http://localhost:8000',
  database: 'app.db'
});

// All operations available
const users = await db.table('users').query();
```

### Option 2: API Key Authentication (Service Mode)

For server-to-server communication or trusted environments:

```typescript
const db = new SynthDB({
  url: 'https://api.example.com',
  database: 'app.db',
  auth: {
    type: 'apiKey',
    key: process.env.SYNTHDB_API_KEY
  }
});
```

### Option 3: User-Based Row-Level Security (RLS Mode)

For multi-tenant applications where users can only access their own data:

```typescript
const db = new SynthDB({
  url: 'https://api.example.com',
  database: 'app.db',
  auth: {
    type: 'user',
    provider: 'jwt', // or 'session'
    token: userToken
  }
});

// Queries automatically filtered by user_id
const myPosts = await db.table('posts').query();
// Equivalent to: SELECT * FROM posts WHERE user_id = current_user_id
```

#### RLS Implementation Requirements

1. **Users Table**: Every project with RLS must have a `users` table:
   ```typescript
   interface User {
     id: string;        // UUID
     email: string;
     created_at: string;
     // ... other fields
   }
   ```

2. **Foreign Key Convention**: Tables with user data must include `user_id`:
   ```typescript
   interface Post {
     id: string;
     user_id: string;   // References users.id
     title: string;
     content: string;
   }
   ```

3. **Automatic Filtering**: SDK automatically adds user_id filters:
   ```typescript
   // User writes:
   const posts = await db.table('posts').query();
   
   // SDK sends:
   GET /api/v1/databases/app.db/tables/posts/rows?where=user_id='current-user-id'
   ```

## API Design

### Basic Usage

```typescript
import { SynthDB } from '@synthdb/client';

// Initialize client
const db = new SynthDB({
  url: 'http://localhost:8000',
  database: 'app.db'
});

// Create table with typed columns
const usersTable = await db.createTable('users', {
  columns: [
    { name: 'email', type: 'text' },
    { name: 'age', type: 'integer' },
    { name: 'score', type: 'real' },
    { name: 'created_at', type: 'timestamp' }
  ]
});

// Get typed table reference
const users = db.table<{
  email: string;
  age: number;
  score: number;
  created_at: Date;
}>('users');

// Insert with type safety
const userId = await users.insert({
  email: 'user@example.com',
  age: 25,
  score: 98.5,
  created_at: new Date()
});

// Query with type-safe results
const adults = await users
  .where('age > ?', 18)
  .orderBy('created_at', 'desc')
  .limit(10)
  .query();

// Update specific row
await users.update(userId, {
  score: 99.0
});

// Delete row
await users.delete(userId);
```

### Advanced Features

#### Type Inference from Sample Data

```typescript
// Infer types from sample data
const products = await db.createTableFromSample('products', [
  { name: 'Widget', price: 19.99, in_stock: true },
  { name: 'Gadget', price: 29.99, in_stock: false }
]);

// TypeScript knows the schema
const expensiveProducts = await products
  .where('price > ?', 25)
  .query();
```

#### Bulk Operations

```typescript
// Bulk insert with type checking
await users.bulkInsert([
  { email: 'user1@example.com', age: 25 },
  { email: 'user2@example.com', age: 30 }
]);

// Import from CSV
await users.importCSV('./users.csv', {
  inferTypes: true,
  sampleSize: 100
});

// Export to JSON
const data = await users.exportJSON({
  where: 'age > 18'
});
```

#### Transactions

```typescript
await db.transaction(async (tx) => {
  const user = await tx.table('users').insert({
    email: 'new@example.com',
    age: 25
  });
  
  await tx.table('profiles').insert({
    user_id: user.id,
    bio: 'New user'
  });
});
```

#### Real-time Subscriptions (Future)

```typescript
// Subscribe to changes
const subscription = users
  .where('age > ?', 18)
  .subscribe((changes) => {
    console.log('Data changed:', changes);
  });

// Unsubscribe
subscription.unsubscribe();
```

## Implementation Details

### Core Client Class

```typescript
// src/client/SynthDBClient.ts
export class SynthDB {
  private api: APIClient;
  private auth?: AuthProvider;
  
  constructor(config: SynthDBConfig) {
    this.api = new APIClient(config.url);
    this.auth = createAuthProvider(config.auth);
  }
  
  table<T = any>(name: string): Table<T> {
    return new Table<T>(this.api, name, this.auth);
  }
  
  async createTable(name: string, schema: TableSchema): Promise<Table> {
    const response = await this.api.post(`/tables`, {
      table_name: name,
      columns: schema.columns
    });
    return this.table(name);
  }
}
```

### Table Class with RLS Support

```typescript
// src/tables/Table.ts
export class Table<T> {
  constructor(
    private api: APIClient,
    private name: string,
    private auth?: AuthProvider
  ) {}
  
  async query(): Promise<T[]> {
    const params: any = {};
    
    // Apply RLS filter if user auth is active
    if (this.auth?.type === 'user') {
      const userId = await this.auth.getCurrentUserId();
      params.where = `user_id = '${userId}'`;
    }
    
    const response = await this.api.get(
      `/tables/${this.name}/rows`,
      params
    );
    return response.data.rows;
  }
  
  async insert(data: Partial<T>): Promise<string> {
    // Automatically add user_id for RLS
    if (this.auth?.type === 'user') {
      const userId = await this.auth.getCurrentUserId();
      data = { ...data, user_id: userId };
    }
    
    const response = await this.api.post(
      `/tables/${this.name}/rows`,
      { data }
    );
    return response.data.id;
  }
}
```

### Query Builder

```typescript
// src/queries/QueryBuilder.ts
export class QueryBuilder<T> {
  private conditions: string[] = [];
  private parameters: any[] = [];
  private _orderBy?: string;
  private _limit?: number;
  private _offset?: number;
  
  where(condition: string, ...params: any[]): this {
    this.conditions.push(condition);
    this.parameters.push(...params);
    return this;
  }
  
  orderBy(column: keyof T, direction: 'asc' | 'desc' = 'asc'): this {
    this._orderBy = `${String(column)} ${direction}`;
    return this;
  }
  
  limit(count: number): this {
    this._limit = count;
    return this;
  }
  
  async query(): Promise<T[]> {
    // Build and execute query
  }
}
```

### Authentication Providers

```typescript
// src/auth/providers.ts
interface AuthProvider {
  type: 'none' | 'apiKey' | 'user';
  getHeaders(): Promise<Record<string, string>>;
  getCurrentUserId?(): Promise<string>;
}

class JWTAuthProvider implements AuthProvider {
  type = 'user' as const;
  
  constructor(private token: string) {}
  
  async getHeaders() {
    return {
      'Authorization': `Bearer ${this.token}`
    };
  }
  
  async getCurrentUserId(): Promise<string> {
    // Decode JWT to get user ID
    const payload = decodeJWT(this.token);
    return payload.sub;
  }
}

class SessionAuthProvider implements AuthProvider {
  type = 'user' as const;
  
  async getHeaders() {
    // Include session cookie
    return {};
  }
  
  async getCurrentUserId(): Promise<string> {
    // Get from session endpoint
    const response = await fetch('/api/v1/auth/me');
    const data = await response.json();
    return data.user_id;
  }
}
```

## Usage Examples

### Example 1: Blog Application with RLS

```typescript
// Initialize with user authentication
const db = new SynthDB({
  url: 'https://api.myblog.com',
  database: 'blog.db',
  auth: {
    type: 'user',
    provider: 'jwt',
    token: localStorage.getItem('auth_token')
  }
});

// User can only see their own posts
const myPosts = await db.table<Post>('posts').query();

// Creating a post automatically sets user_id
const postId = await db.table<Post>('posts').insert({
  title: 'My First Post',
  content: 'Hello, world!'
  // user_id is automatically added
});

// Attempting to access another user's post throws error
try {
  await db.table<Post>('posts').update('other-user-post-id', {
    title: 'Hacked!'
  });
} catch (error) {
  // Error: Forbidden - cannot update posts for other users
}
```

### Example 2: Admin Dashboard without RLS

```typescript
// Admin access with API key
const db = new SynthDB({
  url: 'https://api.myapp.com',
  database: 'app.db',
  auth: {
    type: 'apiKey',
    key: process.env.ADMIN_API_KEY
  }
});

// Admin can see all users
const allUsers = await db.table<User>('users').query();

// Generate reports across all data
const stats = await db.table('orders')
  .where('created_at > ?', '2024-01-01')
  .query();
```

### Example 3: Public Read-Only Access

```typescript
// Public access for read-only data
const db = new SynthDB({
  url: 'https://api.publicdata.com',
  database: 'public.db'
  // No auth required
});

// Anyone can read public data
const publicPosts = await db.table('public_posts').query();

// But cannot modify
try {
  await db.table('public_posts').insert({ title: 'Spam' });
} catch (error) {
  // Error: Unauthorized - authentication required for write operations
}
```

## Package Structure

```json
{
  "name": "@synthdb/client",
  "version": "1.0.0",
  "main": "dist/index.js",
  "module": "dist/index.esm.js",
  "types": "dist/index.d.ts",
  "exports": {
    ".": {
      "require": "./dist/index.js",
      "import": "./dist/index.esm.js",
      "types": "./dist/index.d.ts"
    },
    "./auth": {
      "require": "./dist/auth/index.js",
      "import": "./dist/auth/index.esm.js",
      "types": "./dist/auth/index.d.ts"
    }
  },
  "peerDependencies": {
    "typescript": ">=4.5.0"
  },
  "dependencies": {
    "cross-fetch": "^3.1.5"
  },
  "devDependencies": {
    "@types/node": "^18.0.0",
    "typescript": "^5.0.0",
    "vitest": "^1.0.0",
    "rollup": "^3.0.0"
  }
}
```

## Testing Strategy

### Unit Tests

```typescript
// tests/table.test.ts
import { describe, it, expect, vi } from 'vitest';
import { SynthDB } from '../src';

describe('Table operations', () => {
  it('should apply RLS filters for user auth', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      json: async () => ({ data: { rows: [] } })
    });
    
    const db = new SynthDB({
      url: 'http://test.com',
      database: 'test.db',
      auth: {
        type: 'user',
        provider: 'jwt',
        token: 'mock-token'
      }
    });
    
    await db.table('posts').query();
    
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('where=user_id'),
      expect.any(Object)
    );
  });
});
```

### Integration Tests

```typescript
// tests/integration/rls.test.ts
describe('Row-level security', () => {
  it('should isolate user data', async () => {
    const user1 = new SynthDB({ auth: { token: 'user1-token' } });
    const user2 = new SynthDB({ auth: { token: 'user2-token' } });
    
    // User 1 creates data
    await user1.table('notes').insert({ content: 'User 1 note' });
    
    // User 2 cannot see it
    const user2Notes = await user2.table('notes').query();
    expect(user2Notes).toHaveLength(0);
    
    // User 1 can see their own data
    const user1Notes = await user1.table('notes').query();
    expect(user1Notes).toHaveLength(1);
  });
});
```

## Migration Path

For existing SynthDB users wanting to adopt the TypeScript SDK:

1. **Python to TypeScript Migration Guide**
   ```typescript
   // Python: db.table('users').insert({'name': 'John', 'age': 25})
   // TypeScript: 
   await db.table('users').insert({ name: 'John', age: 25 });
   ```

2. **Schema Generation Tool**
   ```bash
   npx @synthdb/cli generate-types --database app.db --output types.ts
   ```

3. **Compatibility Layer**
   ```typescript
   // Support Python-like API for easier migration
   const db = new SynthDB({ pythonCompat: true });
   db.query('users', "age > 25"); // Python style
   ```

## Performance Considerations

1. **Request Batching**: Combine multiple operations into single requests
2. **Query Caching**: Client-side caching with TTL
3. **Lazy Loading**: Only fetch data when needed
4. **Connection Pooling**: Reuse HTTP connections
5. **Bundle Size**: Tree-shaking for minimal client bundle

## Security Considerations

1. **Token Storage**: Secure storage recommendations for auth tokens
2. **CORS Configuration**: Proper CORS setup for browser usage
3. **Input Validation**: Client-side validation before API calls
4. **Rate Limiting**: Built-in retry logic with exponential backoff
5. **Audit Logging**: Track all operations for security audits

## Future Enhancements

1. **Offline Support**: Local caching and sync when online
2. **GraphQL Support**: Alternative to REST API
3. **React Hooks**: `useSynthDB`, `useTable`, `useQuery`
4. **Vue Composables**: Vue.js integration
5. **ORM Layer**: Active Record pattern support
6. **Schema Migrations**: Database version management
7. **Real-time Subscriptions**: WebSocket support
8. **Type Generation**: Auto-generate TypeScript types from database
9. **Query Optimization**: Automatic query optimization
10. **Multi-database**: Support for database sharding

## Conclusion

The TypeScript SDK will provide a modern, type-safe interface to SynthDB that supports various authentication models including no authentication for development, API keys for services, and user-based row-level security for multi-tenant applications. The SDK will be designed with developer experience in mind, offering intuitive APIs, comprehensive type safety, and seamless integration with modern JavaScript frameworks.