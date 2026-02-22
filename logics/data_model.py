class DataModel:
    """Shared state container for the application."""

    def __init__(self):
        self.df = None                              # Merged DataFrame (original data)
        self.calculated_df = None                   # DataFrame with only calculated variables
        self.dfs_by_type = {}                       # Individual DFs before merge (BS, IS, CF)
        self.file_paths = {'BS': None, 'IS': None, 'CF': None}
        self.column_sources = {}                    # Maps column name to file type(s)
        self.id_col = None                          # Primary ID column
        self.time_col = None                        # Time/Year column
        self.group_cols = []                        # Optional grouping columns
        self.available_vars = []                    # All unique columns from loaded files
        self.formulas = []                          # List of formulas to compute
