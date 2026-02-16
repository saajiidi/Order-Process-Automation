
import pandas as pd
import datetime
import re
from pathlib import Path
from app_modules.processor import process_orders_dataframe

# --- Configuration ---
INPUT_FILENAME = 'Test_beta.xlsx'

def process_pathao_orders_cli(input_path):
    """
    CLI wrapper for processing orders using the modular logic.
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: Source file not found at {input_file.resolve()}")
        # Check if user wants to input path
        try:
             # Timeout logic isn't standard here, just ask
             pass
        except:
             pass 
        return

    print(f"Reading from: {input_file}")
    try:
        if input_file.suffix.lower() == '.csv':
            df = pd.read_csv(input_file)
        else:
            df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Process using modular logic
    print("Processing orders...")
    try:
        result_df = process_orders_dataframe(df)
    except Exception as e:
        print(f"Error during processing: {e}")
        return
        
    # Generate Filename
    # Format: Pathao_Bulk_(total number of order)_time
    total_orders = len(result_df)
    current_time = datetime.datetime.now().strftime("%I_%M_%p")
    output_filename = f"Pathao_Bulk_({total_orders})_{current_time}"
    
    csv_output = Path(f"{output_filename}.csv")
    xlsx_output = Path(f"{output_filename}.xlsx")
    
    try:
        # Save CSV - Use standard utf-8 (no BOM)
        result_df.to_csv(csv_output, index=False, encoding='utf-8')
        print(f"Saved CSV to: {csv_output.resolve()}")
        
        result_df.to_excel(xlsx_output, index=False, engine='openpyxl')
        print(f"Saved XLSX to: {xlsx_output.resolve()}")
        
        print(f"\nSuccessfully processed {len(df)} rows into {len(result_df)} unique orders.")
        
        print("\nNOTE for Windows/Excel Users:")
        print("1. If you open the CSV in Excel, Bangla characters might look strange. This is expected as we removed the BOM signature to support the Pathao Uploader.")
        print("2. The actual file content is correct UTF-8.")
        print("3. Please use the .xlsx file to view/check the data locally with correct Bangla display.")
        
    except Exception as e:
        print(f"Error saving files: {e}")

if __name__ == "__main__":
    process_pathao_orders_cli(INPUT_FILENAME)
