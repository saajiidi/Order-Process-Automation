import pandas as pd
import os
import re

fp = 'h:/Analysis/New_/orders-2026-02-15-12-20-32.xlsx'
output_fp = 'h:/Analysis/New_/product_segments_analysis.xlsx'

if not os.path.exists(fp):
    print(f"File not found: {fp}")
else:
    try:
        df = pd.read_excel(fp)
        
        # Ensure Quantity is numeric
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        df['Item Name'] = df['Item Name'].astype(str).str.strip()
        df['SKU'] = df['SKU'].astype(str).str.strip()
        
        # --- Segment 2: Without Variation (Unique SKU) ---
        # Group by SKU
        sku_stats = df.groupby(['SKU', 'Item Name']).agg({
            'Quantity': 'sum',
            'Order Number': 'nunique'
        }).reset_index().rename(columns={'Order Number': 'Unique Orders'})
        
        sku_stats = sku_stats.sort_values(by='Quantity', ascending=False)
        
        # --- Segment 1: With Variation (Same Product Aggregated) ---
        # Extract Base Name
        # Logic: Split by the last occurrence of " - " to separate size/variation
        def get_base_name(name):
            if " - " in name:
                return name.rsplit(" - ", 1)[0]
            return name

        df['Base Product Name'] = df['Item Name'].apply(get_base_name)
        
        base_product_stats = df.groupby('Base Product Name').agg({
            'Quantity': 'sum',
            'Order Number': 'nunique'
        }).reset_index().rename(columns={'Order Number': 'Unique Orders'})
        
        base_product_stats = base_product_stats.sort_values(by='Quantity', ascending=False)
        
        # --- Save to Excel with Multiple Sheets ---
        with pd.ExcelWriter(output_fp, engine='openpyxl') as writer:
            base_product_stats.to_excel(writer, sheet_name='By Base Product (Aggregated)', index=False)
            sku_stats.to_excel(writer, sheet_name='By Unique SKU (Variations)', index=False)
            
        print("Analysis complete.")
        print(f"Top 5 Base Products:\n{base_product_stats.head(5)}")
        print(f"\nTop 5 SKUs:\n{sku_stats.head(5)}")
        print(f"\nSaved report to: {output_fp}")

    except Exception as e:
        print(f"An error occurred: {e}")
