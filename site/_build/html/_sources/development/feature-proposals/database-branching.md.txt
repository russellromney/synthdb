# Feature Proposal: Database Branching

<div class="status-badge status-proposed">Proposed</div>

**Authors**: SynthDB Development Team  
**Created**: 2024-06-26  
**Status**: Proposal  
**Complexity**: High  

## Summary

Add branching capabilities to SynthDB, allowing users to create isolated copies of database files, perform operations on them, and optionally merge changes back to the main database. This would enable safe experimentation, parallel development workflows, and atomic multi-operation transactions.

## Motivation

### Use Cases

1. **Experimental Development**: Test schema changes or data transformations without affecting production data
2. **Parallel Workflows**: Multiple developers or processes working on different features simultaneously
3. **Atomic Complex Operations**: Perform multiple related operations that should succeed or fail together
4. **Rollback Scenarios**: Easy rollback to previous states before applying risky operations
5. **A/B Testing**: Compare different data processing approaches on the same dataset
6. **Backup and Restore**: Create point-in-time snapshots for recovery

### Current Limitations

- All operations are performed directly on the main database file
- No way to test operations without affecting live data
- Complex multi-step operations can leave database in inconsistent state if interrupted
- No built-in backup/restore mechanism

## Detailed Design

### Core Concepts

#### Branch
A branch is an independent copy of a database file that can be modified without affecting the original. Branches maintain metadata about their origin and changes.

#### Branch Types
1. **Feature Branch**: Full copy for development work
2. **Snapshot Branch**: Read-only copy for backup/analysis
3. **Temporary Branch**: Auto-deleted after session
4. **Merge Branch**: Specifically for merging changes

### API Design

#### Core Branch Operations

```python
import synthdb

# Create main connection
main_db = synthdb.connect('app.limbo')  # Uses Limbo by default

# Create a branch
branch_db = main_db.create_branch('feature-user-profiles')
# or
branch_db = main_db.branch('feature-user-profiles')

# Work on the branch
branch_db.create_table('user_profiles')
branch_db.add_columns('user_profiles', {'bio': 'text', 'avatar': 'text'})

# List branches
branches = main_db.list_branches()
# Returns: [{'name': 'feature-user-profiles', 'created_at': '...', 'size': '...'}]

# Switch between branches
current_branch = main_db.get_current_branch()  # 'main'
main_db.checkout_branch('feature-user-profiles')

# Merge branch back to main
merge_result = main_db.merge_branch('feature-user-profiles')
# Returns: {'success': True, 'conflicts': [], 'changes_applied': 15}

# Delete branch
main_db.delete_branch('feature-user-profiles')
```

#### Advanced Branch Operations

```python
# Create branch from specific point in time
branch_db = main_db.create_branch('rollback-test', from_timestamp='2024-06-25 10:00:00')

# Create branch with copy strategy
branch_db = main_db.create_branch('experiment', strategy='copy')  # Full copy
branch_db = main_db.create_branch('snapshot', strategy='readonly')  # Read-only reference

# Branch with auto-cleanup
with main_db.temporary_branch('temp-operations') as temp_db:
    temp_db.insert('users', {'name': 'test'})
    # Branch automatically deleted when exiting context

# Compare branches
diff = main_db.compare_branches('main', 'feature-user-profiles')
# Returns detailed diff of schema and data changes
```

### Implementation Architecture

#### File System Structure

```
app.db                    # Main database file
.synthdb/
  branches/
    feature-user-profiles.db     # Branch database file
    experiment.db                # Another branch
  metadata/
    branches.json               # Branch metadata
    main.json                  # Main database metadata
  locks/
    feature-user-profiles.lock  # Branch locks for concurrent access
```

#### Metadata Schema

```python
# branches.json structure
{
  "branches": {
    "feature-user-profiles": {
      "created_at": "2024-06-26T10:00:00Z",
      "created_from": "main",
      "strategy": "copy",
      "size_bytes": 1048576,
      "last_modified": "2024-06-26T11:30:00Z",
      "description": "Adding user profile features",
      "auto_delete": false
    }
  },
  "main": {
    "file": "app.db",
    "last_branched": "2024-06-26T10:00:00Z"
  }
}
```

#### Branch Strategies

1. **Full Copy (`copy`)**
   - Complete file copy
   - Independent operations
   - Higher disk usage
   - Safest option

2. **Copy-on-Write (`cow`)**
   - Shared data, separate changes
   - More complex implementation
   - Better disk efficiency
   - Requires filesystem support

3. **Read-Only Reference (`readonly`)**
   - Shared file access
   - No modifications allowed
   - Minimal overhead
   - Good for snapshots

### Merge Strategies

#### Simple Merge (Non-Conflicting)
- Schema additions (new tables, columns)
- Data additions (new rows with unique IDs)
- Compatible data type changes

#### Conflict Resolution
- Schema conflicts (same column, different types)
- Data conflicts (same row ID, different values)
- Deletion conflicts (data deleted in one branch, modified in another)

```python
# Manual conflict resolution
conflicts = main_db.merge_branch('feature-branch', dry_run=True)
for conflict in conflicts:
    if conflict.type == 'schema_conflict':
        # Choose resolution strategy
        conflict.resolve('prefer_branch')  # or 'prefer_main', 'manual'
    elif conflict.type == 'data_conflict':
        # Provide resolution data
        conflict.resolve_with_data({'column': 'new_value'})

# Apply merge with resolutions
merge_result = main_db.merge_branch('feature-branch', conflicts=conflicts)
```

### CLI Integration

```bash
# Branch operations
sdb branch create feature-auth
sdb branch list
sdb branch switch feature-auth
sdb branch delete feature-auth

# Work on branches
sdb branch create experiment
sdb --branch experiment table create test_table
sdb --branch experiment add test_table '{"name": "test"}'

# Merge operations
sdb branch merge feature-auth
sdb branch merge feature-auth --dry-run
sdb branch diff main feature-auth

# Snapshot operations
sdb branch snapshot backup-before-migration
sdb branch restore backup-before-migration
```

## Implementation Plan

### Phase 1: Basic Branching (4-6 weeks)
- [ ] File copying mechanism
- [ ] Branch metadata management
- [ ] Basic create/switch/delete operations
- [ ] CLI integration
- [ ] Simple merge (non-conflicting)

### Phase 2: Advanced Features (3-4 weeks)
- [ ] Conflict detection and resolution
- [ ] Branch comparison and diff
- [ ] Temporary branches
- [ ] Copy-on-write strategy

### Phase 3: Production Features (2-3 weeks)
- [ ] Concurrent access handling
- [ ] Performance optimization
- [ ] Advanced merge strategies
- [ ] Documentation and examples

## Considerations

### Performance
- **File Copy Overhead**: Large databases will have slow branch creation
- **Disk Space**: Multiple branches can consume significant storage
- **Merge Complexity**: Large diffs may be slow to process

**Mitigations**:
- Implement copy-on-write for supported filesystems
- Add disk usage monitoring and warnings
- Provide progress indicators for long operations
- Implement incremental/streaming merges

### Concurrency
- **Branch Access**: Multiple connections to same branch
- **Merge Conflicts**: Concurrent modifications during merge
- **File Locking**: Platform-specific file locking mechanisms

**Mitigations**:
- Implement branch-level locking
- Use atomic file operations
- Provide clear error messages for lock conflicts

### Data Integrity
- **Partial Merges**: Ensure atomic merge operations
- **Corruption**: Protect against file corruption during operations
- **Metadata Consistency**: Keep branch metadata in sync with actual files

**Mitigations**:
- Use database transactions for merge operations
- Implement checksum verification
- Regular metadata validation

## Alternative Approaches

### 1. Transaction-Based Approach
Instead of file-level branching, use database transactions with savepoints.

**Pros**: 
- No file copying overhead
- Native database support
- Better performance

**Cons**: 
- Limited by database transaction capabilities
- No persistent branches
- Complex rollback scenarios

### 2. Schema Versioning
Track schema changes and data migrations without full branching.

**Pros**: 
- Lightweight implementation
- Good for schema evolution
- Fits existing SynthDB architecture

**Cons**: 
- Limited to schema changes
- No data experimentation
- Complex conflict resolution

### 3. Virtual Branching
Use overlays and views instead of physical copies.

**Pros**: 
- No disk overhead
- Fast branch creation
- Complex query optimization

**Cons**: 
- Very complex implementation
- Performance overhead on queries
- Limited by SQL capabilities

## Success Metrics

- **Usability**: Branch operations complete in <5 seconds for databases <100MB
- **Reliability**: 99.9% success rate for merge operations without conflicts
- **Performance**: <10% overhead for operations on branched databases
- **Adoption**: Feature used in >30% of SynthDB projects within 6 months

## Future Enhancements

- **Remote Branches**: Sync branches across multiple machines
- **Automated Merging**: AI-assisted conflict resolution
- **Branch Templates**: Predefined branch configurations
- **Integration**: Git-like workflow with external version control
- **Compression**: Efficient storage for similar branches

## Related Work

- **Git**: File-based version control inspiration
- **SQLite Backup API**: Technical implementation reference  
- **Database Replication**: Multi-master conflict resolution patterns
- **Copy-on-Write Filesystems**: ZFS, Btrfs implementation examples

## Conclusion

Database branching would significantly enhance SynthDB's utility for development, testing, and production workflows. While implementation is complex, the benefits for safe experimentation and parallel development justify the effort.

The proposed design balances functionality with implementation complexity, providing a foundation for both simple use cases and advanced workflows. Starting with basic file copying and expanding to more sophisticated strategies allows for iterative development and user feedback integration.