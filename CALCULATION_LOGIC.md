# Row-by-Row Formula Calculation Logic

## Grouping by ID (Firm)

When calculating formulas with row offsets like `Column(x)` and `Column(x-1)`, the system uses **grouping by ID** to ensure calculations are contained within each entity.

### How It Works

1. **Set ID Column = Firm** (during column selection)
2. **System detects multiple firms** in the data
3. **Data is split by firm** - each firm gets independent calculation group
4. **Row indices reset per firm** - each firm starts at row 0
5. **Formulas calculate independently** within each firm only

### Example

**Data Structure:**
```
Firm A: rows 0-4
Firm B: rows 0-5
Firm C: rows 0-3
```

**Formula:** `Revenue(x) - Revenue(x-1)`

**Calculation Results:**
```
Firm A:
  - Row 0: x-1 = out of bounds → None
  - Row 1: Revenue(1) - Revenue(0) → Calculated
  - Row 2: Revenue(2) - Revenue(1) → Calculated
  
Firm B:
  - Row 0: x-1 = out of bounds → None
  - Row 1: Revenue(1) - Revenue(0) → Calculated
  - Row 2: Revenue(2) - Revenue(1) → Calculated
```

### Key Points

- ✓ No cross-firm mixing
- ✓ Each firm's data is isolated
- ✓ `(x-1)` only looks within same firm
- ✓ First row of each firm returns None (no previous row)
- ✓ Out-of-bounds references return None

### Null Handling

If **any referenced cell is blank/null**, the entire row returns `None`:
```
Formula: A(x) + B(x)
Row 5: A=100, B=null → Returns None
```

This prevents arithmetic errors and ensures data integrity.
