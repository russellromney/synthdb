# Feature Proposal: Column Type Changes

## Overview

This proposal explores implementing the ability to change column data types in SynthDB after a column has been created and populated with data. This feature would allow users to convert existing columns from one type to another (e.g., from text to integer, or from integer to real).

## Current Architecture

SynthDB currently uses a type-separated storage architecture:
- Column definitions store the data type in the `column_definitions` table
- Values are stored in type-specific tables: `text_values`, `integer_values`, `real_values`, `timestamp_values`
- Each value is versioned with an `is_current` flag and version number
- Views are dynamically generated to join data from appropriate type tables based on column definitions

## Implementation Approaches

### Approach 1: Migration-Based Type Change
Create a new column with the new type and migrate all existing data.

**Implementation:**
1. Create a new column definition with the new type
2. For each row with a value in the old column:
   - Convert the value to the new type
   - Insert into the appropriate new type table
3. Mark the old column as deleted
4. Update views to use the new column

**Pros:**
- Clean separation of old and new data
- Full history preservation
- Rollback possible by undeleting old column
- No modifications to existing data

**Cons:**
- Requires column rename if maintaining same name
- More complex for user-facing API
- Temporary duplication of data

### Approach 2: In-Place Type Conversion
Update the column definition and move data between type tables.

**Implementation:**
1. Update `data_type` in `column_definitions`
2. For each current value in the old type table:
   - Convert the value to the new type
   - Insert into new type table with incremented version
   - Mark old value as `is_current = 0`
3. Regenerate views

**Pros:**
- Maintains column identity and name
- Cleaner user experience
- Leverages existing versioning system

**Cons:**
- No automatic rollback mechanism
- Mixed type history in different tables
- More complex history queries

### Approach 3: Dual-Type Support
Allow columns to have multiple active types simultaneously.

**Implementation:**
1. Add `type_version` to column definitions
2. Store new type as additional column version
3. Views could expose both types or prefer newest
4. Values remain in original tables with type metadata

**Pros:**
- Maximum flexibility
- No data migration needed
- Gradual transition possible

**Cons:**
- Significant schema changes required
- Complex view generation
- Confusing user experience

### Approach 4: Virtual Type Columns
Create computed columns that convert on read.

**Implementation:**
1. Add concept of virtual/computed columns
2. Define transformation from source column
3. No data storage, only view-level conversion

**Pros:**
- No data migration
- Zero storage overhead
- Easy to experiment with types

**Cons:**
- Performance overhead on every query
- Limited to conversions possible in SQL
- Not a true type change

## Type Conversion Matrix

| From Type | To Type | Conversion Strategy | Potential Issues |
|-----------|---------|-------------------|------------------|
| text | integer | Parse as integer | Invalid format, overflow |
| text | real | Parse as float | Invalid format, precision |
| text | timestamp | Parse as ISO date | Invalid format |
| integer | text | ToString | None |
| integer | real | Cast | None |
| integer | timestamp | Unix timestamp | Range limitations |
| real | text | Format | Precision loss |
| real | integer | Round/truncate | Data loss |
| real | timestamp | Unix timestamp | Range limitations |
| timestamp | text | ISO format | None |
| timestamp | integer | Unix timestamp | Precision loss |
| timestamp | real | Unix timestamp | None |

## Recommended Approach

**Approach 2 (In-Place Type Conversion)** is recommended for the following reasons:

1. **Consistency with existing patterns**: SynthDB already uses versioning for all data changes
2. **User experience**: Clean API that matches user mental model
3. **Performance**: Leverages existing optimized view system
4. **Flexibility**: Can support rollback via version history if needed

## Proposed API

```python
# Basic type change
db.change_column_type("users", "age", "real")

# With conversion options
db.change_column_type(
    table="products", 
    column="price",
    new_type="integer",
    conversion="round",  # or "truncate", "ceil", "floor"
    on_error="skip"     # or "fail", "null", "default"
)

# Bulk type changes
db.change_column_types("users", {
    "age": "real",
    "created_at": "text",
    "score": {"type": "integer", "conversion": "round"}
})
```

## Implementation Plan

1. **Core Functionality**
   - Add type conversion utilities for all type pairs
   - Implement `change_column_type` in core.py
   - Add transaction support for atomic changes

2. **Safety Features**
   - Pre-flight validation to check conversion feasibility
   - Dry-run mode to preview changes
   - Detailed error reporting for failed conversions

3. **API Layer**
   - Add methods to Connection class
   - CLI command support
   - Proper error handling and user feedback

4. **Testing**
   - Comprehensive conversion tests
   - Edge case handling (nulls, extreme values)
   - Performance benchmarks for large datasets

## Considerations

### Data Loss Prevention
- Warn when conversions may lose precision (real→integer)
- Provide preview of changes before execution
- Option to create backup column before conversion

### Performance
- Batch conversions to minimize transaction overhead
- Consider progress reporting for large tables
- Optimize view regeneration

### Compatibility
- Ensure history queries still work correctly
- Handle mixed-type history gracefully
- Document behavior changes clearly

## Conclusion

Implementing column type changes would significantly enhance SynthDB's flexibility while maintaining its core principles of versioning and data integrity. The in-place conversion approach offers the best balance of usability, performance, and consistency with existing architecture.

The feature would position SynthDB as a more complete solution for evolving schemas, particularly valuable for:
- Data exploration and cleaning workflows
- Schema evolution in production systems
- ETL and data integration scenarios