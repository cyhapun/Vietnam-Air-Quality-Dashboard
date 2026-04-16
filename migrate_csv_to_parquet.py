import os
import glob
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

base_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(base_dir, "data")

csv_files = glob.glob(os.path.join(data_dir, "**", "*.csv"), recursive=True)

def convert_to_parquet(file_path):
    try:
        if not str(file_path).lower().endswith(".csv"):
            return
        
        target_path = file_path[:-4] + ".parquet"
        
        df = pd.read_csv(file_path, low_memory=False)
        df.to_parquet(target_path, index=False)
        os.remove(file_path)
        return True
    except Exception as e:
        print(f"Error migrating {file_path}: {e}")
        return False

if __name__ == "__main__":
    if not csv_files:
        print("No CSV files found in data directory.")
    else:
        print(f"Found {len(csv_files)} CSV files. Starting migration to Parquet...")
        success = 0
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(tqdm(executor.map(convert_to_parquet, csv_files), total=len(csv_files)))
        
        for r in results:
            if r: success += 1
            
        print(f"Migration completed. Converted {success} / {len(csv_files)} files.")
