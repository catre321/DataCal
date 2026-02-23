import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


def load_individual_files(file_paths, progress_callback=None):
    """
    Load selected files in parallel (multi-threaded) to speed up loading.

    Args:
        file_paths: dict mapping file type ('BS', 'IS', 'CF') to file path.
        progress_callback: Optional callable(current_idx, total, filename) for progress updates.

    Returns:
        tuple: (dfs_by_type, column_sources, available_vars)
        - dfs_by_type: dict of DataFrames keyed by file type
        - column_sources: dict mapping column name to file type(s)
        - available_vars: list of all unique column names

    Raises:
        ValueError: If no files were selected.
        Exception: On file read errors.
    """
    selected_files = {k: v for k, v in file_paths.items() if v is not None}
    if not selected_files:
        raise ValueError("Không có file được chọn.")

    dfs_by_type = {}
    column_sources = {}
    
    total_files = len(selected_files)
    completed = 0
    
    def load_single_file(ft, path):
        """Load a single file - can be called in parallel."""
        filename = path.split('\\')[-1] if '\\' in path else path.split('/')[-1]
        
        if path.endswith('.csv'):
            # Try multiple encodings to handle international characters
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
            df_temp = None
            
            for enc in encodings:
                try:
                    df_temp = pd.read_csv(path, encoding=enc)
                    print(f"[DEBUG] {filename} loaded with encoding: {enc}")
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if df_temp is None:
                raise ValueError(f"Could not load {filename} with any supported encoding")
        else:
            df_temp = pd.read_excel(path)
        
        return ft, df_temp, filename
    
    # Load all files concurrently using ThreadPoolExecutor
    # max_workers = CPU cores count for optimal parallel loading
    print(f"[DEBUG] Starting parallel load with {os.cpu_count()} workers...")
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Submit all file loading tasks
        futures = {
            executor.submit(load_single_file, ft, path): ft 
            for ft, path in selected_files.items()
        }
        
        print(f"[DEBUG] Submitted {len(futures)} file loading tasks")
        
        # Process completed tasks as they finish
        for future in as_completed(futures):
            completed += 1
            ft, df_temp, filename = future.result()
            
            # Call progress callback
            if progress_callback:
                progress_callback(completed, total_files, filename)
            
            print(f"[DEBUG] Completed {completed}/{total_files}: {filename}")
            
            dfs_by_type[ft] = df_temp
            
            # Build column sources
            for col in df_temp.columns:
                if col not in column_sources:
                    column_sources[col] = ft
                else:
                    if ft not in column_sources[col]:
                        column_sources[col] += f"/{ft}"
    
    available_vars = sorted(set(column_sources.keys()))
    
    return dfs_by_type, column_sources, available_vars


def merge_files_on_keys(dfs_by_type, id_col, time_col):
    """
    Merge all DataFrames on ID and time columns.

    Duplicate columns (same name in multiple files) are resolved by keeping
    the value from the first file that introduced the column (_x wins, _y dropped).

    Args:
        dfs_by_type: dict of DataFrames keyed by file type.
        id_col: primary ID column name.
        time_col: time column name.

    Returns:
        Merged DataFrame with all rows/columns from all files.

    Raises:
        ValueError: If no valid DFs to merge.
    """
    merge_keys = [id_col, time_col]
    dfs_list = list(dfs_by_type.values())

    if not dfs_list:
        raise ValueError("Không có file để merge.")

    merged = dfs_list[0].copy()
    for df in dfs_list[1:]:
        merged = merged.merge(df, on=merge_keys, how='outer', suffixes=('', '_dup'))

        # Drop _dup columns — keep the first file's version for every duplicate
        dup_cols = [c for c in merged.columns if c.endswith('_dup')]
        if dup_cols:
            print(f"[MERGE] Dropping duplicate columns (keeping first file's version): {dup_cols}")
            merged.drop(columns=dup_cols, inplace=True)

    merged = merged.sort_values(merge_keys, ignore_index=True)
    return merged


def export_to_file(df, path, formulas=None, source_df=None):
    """
    Export results to Excel.

    Sheet layout:
        - "Results": full computed DataFrame (ID, time, all variables).
        - One sheet per mean formula: unique group combinations and their mean value.
          Sheet name = variable name (truncated to 31 chars for Excel limit).

    Args:
        df: Computed result DataFrame (ID, time, all computed vars).
        path: Output .xlsx file path.
        formulas: List of formula dicts; used to build per-mean summary sheets.
        source_df: Original merged DataFrame used to compute group summaries.
    """
    with pd.ExcelWriter(path, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Results', index=False)

        if formulas and source_df is not None:
            for f in formulas:
                if f.get('type') != 'mean':
                    continue
                mean_var = f['mean_var']
                groups = f['mean_groups']
                var_name = f['name']
                try:
                    summary = (
                        source_df.groupby(groups, dropna=False)[mean_var]
                        .mean()
                        .reset_index()
                        .rename(columns={mean_var: var_name})
                    )
                    sheet_name = var_name[:31]
                    summary.to_excel(writer, sheet_name=sheet_name, index=False)
                    print(f"[EXPORT] Summary sheet '{sheet_name}' written ({len(summary)} rows)")
                except Exception as e:
                    print(f"[EXPORT] Could not build summary for {var_name}: {e}")
