import re
import pandas as pd
import numpy as np
import math
import os
from multiprocessing import Pool
from functools import partial


def compute_variables(df, formulas, id_col, time_col, progress_callback=None):
    """
    Compute all formula-based variables with parallel processing.

    Supports:
        - Mean aggregation by group
        - Row-by-row formulas using Column(x) syntax
        - Pandas eval expressions (regular Excel-like formulas)
        - Parallel computation with automatic chunking
        - Chaining: variables computed in order, later vars can reference earlier ones

    Args:
        df: pandas DataFrame (original, not modified).
        formulas: list of formula dicts.
        id_col: primary ID column name.
        time_col: time column name.
        progress_callback: Optional callable(formula_idx, total_formulas, formula_name)

    Returns:
        A new DataFrame with ID, Time, and all calculated variables.
    """
    result_df = df[[id_col, time_col]].copy()
    total_formulas = len(formulas)
    computed_vars = []  # Track names of computed variables

    for idx, f in enumerate(formulas):
        formula_name = f['name']
        
        # Progress callback
        if progress_callback:
            progress_callback(idx + 1, total_formulas, formula_name)
        
        # Create context: original columns + previously computed variables
        context_df = df.copy()
        for var_name in computed_vars:
            context_df[var_name] = result_df[var_name]
        
        # Resolve formula type — also detect by expression pattern as fallback
        # (handles edge case where formula dict was re-created without the type field)
        if f.get('type') not in ('mean', 'stdev'):
            m = re.match(r'^\s*mean\s*\((.+?)\)\s*by\s*(.+)$', f.get('expression', ''))
            if m:
                print(f"[WARN] Formula '{formula_name}' missing type field; detected as mean from expression.")
                f = dict(f, type='mean',
                         mean_var=m.group(1).strip(),
                         mean_groups=[g.strip() for g in m.group(2).split(',')])
            else:
                # Try to detect stdev pattern
                m = re.match(r'^\s*stdev\s*\((.+?)\)(?:\s*by\s*(.+))?$', f.get('expression', ''))
                if m:
                    print(f"[WARN] Formula '{formula_name}' missing type field; detected as stdev from expression.")
                    groups_str = m.group(2)
                    stdev_groups = [g.strip() for g in groups_str.split(',')] if groups_str else []
                    f = dict(f, type='stdev',
                             stdev_var=m.group(1).strip(),
                             stdev_groups=stdev_groups)

        if f.get('type') == 'mean':
            result_df[formula_name] = _sanitize_result(_compute_mean(context_df, f, time_col))
        elif f.get('type') == 'stdev':
            result_df[formula_name] = _sanitize_result(_compute_stdev(context_df, f, time_col))
        elif _is_row_formula(f['expression']):
            # Row-by-row formula with Column(x) syntax (parallel groups)
            result_df[formula_name] = _sanitize_result(_compute_row_formula_parallel(
                context_df, f['expression'], id_col, time_col
            ))
        else:
            # Regular pandas eval expression (parallel chunks)
            expr = f['expression']
            result_df[formula_name] = _sanitize_result(_compute_eval_formula_parallel(
                context_df, expr
            ))
        
        computed_vars.append(formula_name)

    return result_df


def _compute_mean(df, formula, time_col):
    """
    Compute a grouped mean variable and return the result series.

    Groups are taken exactly as configured by the user (no automatic additions).
    Rows whose group column contains NaN are still assigned a mean computed
    from the non-NaN groups (dropna=False).
    """
    mean_var = formula['mean_var']
    groups = formula['mean_groups']

    print(f"[MEAN] Computing mean({mean_var}) grouped by {groups}")
    return df.groupby(groups, dropna=False)[mean_var].transform('mean')


def _compute_stdev(df, formula, time_col):
    """
    Compute a grouped STDEV.S (sample standard deviation) variable and return the result series.

    - If stdev_groups is specified: compute std dev per group
    - If stdev_groups is empty: compute std dev across entire column (ungrouped)
    - Null/NaN values are skipped in calculation (like Excel STDEV.S)
    - Uses ddof=1 for sample standard deviation (divides by n-1, not n)
    """
    stdev_var = formula['stdev_var']
    groups = formula.get('stdev_groups', [])

    if groups:
        print(f"[STDEV] Computing stdev({stdev_var}) grouped by {groups}")
        return df.groupby(groups, dropna=False)[stdev_var].transform(lambda x: x.std(ddof=1))
    else:
        # Ungrouped: compute std dev across entire column
        print(f"[STDEV] Computing ungrouped stdev({stdev_var})")
        stdev_value = df[stdev_var].std(ddof=1)
        return pd.Series([stdev_value] * len(df), index=df.index)


def _is_row_formula(expr):
    """Check if expression uses Column(x) offset syntax."""
    return bool(re.search(r'\w+\s*\(x[-+]?\d*\)', expr))


def _compute_row_formula(df, formula_expr, id_col, time_col=None):
    """
    Compute row-by-row formula with Column(x) offset syntax.

    Supports:
        - Column(x) = current row
        - Column(x+N) = N rows forward
        - Column(x-N) = N rows backward
        - IF(condition, value_true, value_false)

    Example: IF(Revenue(x+1) == Revenue(x), Profit(x), 0)

    Args:
        df: DataFrame
        formula_expr: Formula string with Column(x) references
        id_col: Primary ID column (for grouping if multiple entities)
        time_col: Time column name (used for error context)

    Returns:
        Series with computed values
    """
    results = []

    # Check if we need grouping (multiple IDs)
    if df[id_col].nunique() > 1:
        print("Multiple entities detected, applying row-by-row formula within each group.")
        # Group by ID and process each group separately
        for entity_id, group_df in df.groupby(id_col, sort=False):
            group_df_reset = group_df.reset_index(drop=True)
            group_results = [
                _evaluate_single_row(formula_expr, group_df_reset, idx, id_col=id_col, time_col=time_col)
                for idx in range(len(group_df_reset))
            ]
            results.extend(group_results)
    else:
        # No grouping needed
        results = [
            _evaluate_single_row(formula_expr, df, idx, id_col=id_col, time_col=time_col)
            for idx in range(len(df))
        ]

    return pd.Series(results, index=df.index)


def _compute_row_formula_parallel(df, formula_expr, id_col, time_col=None):
    """
    Compute row-by-row formula in parallel by splitting groups across processes.
    """
    results_dict = {}
    
    # Check if we need grouping (multiple IDs)
    if df[id_col].nunique() > 1:
        print("Multiple entities detected, computing in parallel...")
        # Split groups into chunks for parallel processing
        groups_list = list(df.groupby(id_col, sort=False))
        
        # Determine number of workers
        num_workers = os.cpu_count() or 4
        
        # Use partial to create worker function
        worker_func = partial(_compute_group_chunk, formula_expr=formula_expr, id_col=id_col, time_col=time_col)
        
        # Process groups in parallel
        with Pool(processes=num_workers) as pool:
            chunk_results = pool.map(worker_func, groups_list)
        
        # Combine results
        for group_id, group_results, group_indices in chunk_results:
            for idx, result in zip(group_indices, group_results):
                results_dict[idx] = result
    else:
        # No grouping - process in parallel chunks
        num_workers = os.cpu_count() or 4
        chunk_size = max(1, len(df) // num_workers)
        
        # Create index ranges for chunks
        chunks = []
        for i in range(0, len(df), chunk_size):
            end = min(i + chunk_size, len(df))
            chunks.append((i, end))
        
        # Process chunks in parallel
        worker_func = partial(_compute_row_chunk, df=df, formula_expr=formula_expr, id_col=id_col, time_col=time_col)
        
        with Pool(processes=num_workers) as pool:
            chunk_results = pool.map(worker_func, chunks)
        
        # Combine chunk results
        for chunk_rows in chunk_results:
            for idx, result in chunk_rows:
                results_dict[idx] = result
    
    # Convert to Series in original order
    results = [results_dict.get(i) for i in range(len(df))]
    return pd.Series(results, index=df.index)


def _compute_eval_formula_parallel(df, expr):
    """
    Compute eval formula in parallel by splitting rows into chunks.
    
    Auto-chunks data based on CPU cores for optimal parallel performance.
    """
    num_workers = os.cpu_count() or 4
    
    # Edge case: fewer rows than cores
    if len(df) < num_workers:
        print(f"Dataset has {len(df)} rows, fewer than {num_workers} cores. Using sequential processing.")
        return df.eval(expr)
    
    # Calculate chunk size
    chunk_size = max(1, len(df) // num_workers)
    
    # Create chunks with index ranges
    chunks = []
    for i in range(0, len(df), chunk_size):
        end = min(i + chunk_size, len(df))
        chunks.append((i, end))
    
    print(f"[Parallel] Processing {len(chunks)} chunks across {num_workers} workers...")
    
    # Process chunks in parallel
    worker_func = partial(_compute_eval_chunk, df=df, expr=expr)
    
    with Pool(processes=num_workers) as pool:
        chunk_results = pool.map(worker_func, chunks)
    
    # Combine chunk results into single series
    combined = pd.concat(chunk_results, ignore_index=False)
    return combined.sort_index()


def _compute_group_chunk(group_tuple, formula_expr, id_col=None, time_col=None):
    """
    Process a single group for row-by-row formula (for multiprocessing).
    """
    entity_id, group_df = group_tuple
    group_df_reset = group_df.reset_index(drop=True)
    group_results = [
        _evaluate_single_row(formula_expr, group_df_reset, idx, id_col=id_col, time_col=time_col)
        for idx in range(len(group_df_reset))
    ]
    original_indices = group_df.index.tolist()
    return entity_id, group_results, original_indices


def _compute_row_chunk(chunk_range, df, formula_expr, id_col=None, time_col=None):
    """
    Process a single chunk of rows for row-by-row formula (for multiprocessing).
    """
    start, end = chunk_range
    results = []
    for idx in range(start, end):
        result = _evaluate_single_row(formula_expr, df, idx, id_col=id_col, time_col=time_col)
        results.append((idx, result))
    return results


def _compute_eval_chunk(chunk_range, df, expr):
    """
    Process a single chunk for eval formula (for multiprocessing).
    """
    start, end = chunk_range
    chunk_df = df.iloc[start:end]
    result = chunk_df.eval(expr)
    return result


class _SafeMathError(Exception):
    """Raised by safe math helpers to signal an undefined mathematical operation (log(0), sqrt(-1), etc.)."""
    pass


def _sanitize_result(series):
    """
    Replace inf and nan values with None in a pandas Series.
    
    Converts inf, -inf, and nan to None so they don't appear in Excel output.
    """
    result = series.copy()
    result = result.replace([np.inf, -np.inf], None)
    result = result.where(pd.notna(result), None)
    return result


def _evaluate_single_row(formula_expr, df, row_idx, id_col=None, time_col=None):
    """
    Evaluate formula for a single row.

    Replaces Column(x+offset) references with actual values and evaluates.
    Handles optional spaces before parentheses: Column(x) or Column (x).

    Supported functions:
        - Conditional: IF(condition, value_true, value_false)
        - Math: log(x), Ln(x), log10(x), log2(x), exp(x), sqrt(x), sin(x), cos(x), tan(x), pow(x, y)
        - Utility: abs(x), round(x)
        - Operators: +, -, *, /, ** (exponentiation)

    Examples:
        - IF(A(x+1) == A(x), B(x), 0)
        - Ln(Revenue(x)) ** 2 + sqrt(Cost(x))
        - round(abs(Profit(x-1)) / Revenue(x), 2)
        - IF(exp(GrowthRate(x)) > 1.5, sin(Price(x)) + cos(Price(x+1)), 0)

    Args:
        formula_expr: Formula string like "IF(A(x+1) == A(x), B(x), 0)"
        df: DataFrame (should be reset index for group processing)
        row_idx: Current row index

    Returns:
        Evaluated result or None if error/out of bounds
    """
    # Pattern: ColumnName(x) or ColumnName (x) with optional space
    col_pattern = r'(\w+)\s*\(x([-+]\d+)?\)'

    # Build evaluation namespace
    local_ns = {}
    eval_expr = formula_expr

    matches = re.findall(col_pattern, formula_expr)

    for col_name, offset_str in matches:
        offset = int(offset_str) if offset_str else 0
        target_row = row_idx + offset

        # Create safe variable name (no +/- allowed in Python identifiers)
        if offset == 0:
            var_name = f'__{col_name}__'
        else:
            # Use 'p' for plus, 'm' for minus: __ColName__p1 or __ColName__m2
            sign = 'p' if offset > 0 else 'm'
            var_name = f'__{col_name}__{sign}{abs(offset)}__'

        # Get value with bounds check
        if target_row < 0 or target_row >= len(df):
            # Out of bounds - return None to indicate formula can't be computed
            return None
        else:
            try:
                value = df.iloc[target_row][col_name]
                # Handle NaN - if cell is blank/null, return None (can't compute)
                if pd.isna(value):
                    return None
            except (KeyError, IndexError) as e:
                print(f"Error: Column '{col_name}' not found in DataFrame at row {target_row}")
                return None

        local_ns[var_name] = value

        # Replace in expression - use flexible pattern with optional space and closing paren
        original_pattern = rf'{re.escape(col_name)}\s*\(x{re.escape(offset_str or "")}\)'
        eval_expr = re.sub(original_pattern, var_name, eval_expr)

    # Add IF function to namespace
    def IF(condition, value_if_true, value_if_false):
        """Excel-like IF function."""
        if condition:
            return value_if_true
        else:
            return value_if_false

    local_ns['IF'] = IF
    local_ns['abs'] = abs
    local_ns['round'] = round
    
    # Math functions with safety checks — raise _SafeMathError to stop evaluation cleanly
    def safe_log(x):
        """Natural log (log base e / ln); returns error for x <= 0 or non-finite input."""
        if x is None or (isinstance(x, float) and not math.isfinite(x)) or x <= 0:
            raise _SafeMathError(f"log({x}) is undefined")
        return math.log(float(x))

    def safe_log10(x):
        """Base-10 log; returns None for x <= 0."""
        if x is None or (isinstance(x, float) and not math.isfinite(x)) or x <= 0:
            raise _SafeMathError(f"log10({x}) is undefined")
        return math.log10(float(x))

    def safe_log2(x):
        """Base-2 log; returns None for x <= 0."""
        if x is None or (isinstance(x, float) and not math.isfinite(x)) or x <= 0:
            raise _SafeMathError(f"log2({x}) is undefined")
        return math.log2(float(x))

    def safe_sqrt(x):
        """Square root; returns None for x < 0."""
        if x is None or (isinstance(x, float) and not math.isfinite(x)) or x < 0:
            raise _SafeMathError(f"sqrt({x}) is undefined")
        return math.sqrt(float(x))

    def safe_exp(x):
        """Exponential; returns None on overflow."""
        try:
            return math.exp(float(x))
        except OverflowError:
            raise _SafeMathError(f"exp({x}) overflowed")

    local_ns['log'] = safe_log
    local_ns['Ln'] = safe_log  # Excel Ln() = natural log
    local_ns['log10'] = safe_log10
    local_ns['log2'] = safe_log2
    local_ns['exp'] = safe_exp
    local_ns['sqrt'] = safe_sqrt
    local_ns['sin'] = math.sin
    local_ns['cos'] = math.cos
    local_ns['tan'] = math.tan
    local_ns['pow'] = pow

    # Evaluate safely
    try:
        # Use empty globals dict — Python auto-injects real __builtins__, which numpy
        # C-extensions need internally. Our local_ns still shadows all names we care about.
        # np.errstate promotes numpy divide-by-zero/invalid warnings to FloatingPointError
        # so they are caught cleanly below instead of printing RuntimeWarning.
        with np.errstate(divide='raise', invalid='raise'):
            result = eval(eval_expr, {}, local_ns)
        # Guard against inf/nan produced by non-numpy float arithmetic
        if result is None:
            return None
        if isinstance(result, (int, float, np.integer, np.floating)):
            result_float = float(result)
            # Check for inf, -inf, or nan
            if not math.isfinite(result_float):
                print(f"Non-finite result ({result_float}) at row {row_idx} -> None")
                return None
        return result
    except (_SafeMathError, ZeroDivisionError, FloatingPointError) as e:
        # Undefined math: log(0), sqrt(-1), exp overflow, or any division by zero
        firm = df.iloc[row_idx][id_col] if id_col and id_col in df.columns else None
        year = df.iloc[row_idx][time_col] if time_col and time_col in df.columns else None
        ctx = f"row {row_idx}"
        if firm is not None:
            ctx += f", {id_col}={firm}"
        if year is not None:
            ctx += f", {time_col}={year}"
        print(f"Math error at {ctx}: {str(e)} -> None")
        return None
    except Exception as e:
        firm = df.iloc[row_idx][id_col] if id_col and id_col in df.columns else None
        year = df.iloc[row_idx][time_col] if time_col and time_col in df.columns else None
        ctx = f"row {row_idx}"
        if firm is not None:
            ctx += f", {id_col}={firm}"
        if year is not None:
            ctx += f", {time_col}={year}"
        print(f"Evaluation error at {ctx}: {str(e)}")
        print(f"Expression: {eval_expr}")
        return None

