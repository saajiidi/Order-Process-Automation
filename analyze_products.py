import pandas as pd
import os
import sys

# Set encoding for stdout
sys.stdout.reconfigure(encoding='utf-8')

fp = 'h:/Analysis/New_/orders-2026-02-15-12-20-32.xlsx'
output_csv = 'h:/Analysis/New_/product_analysis.csv'

if not os.path.exists(fp):
    print(f"File not found: {fp}")
else:
    try:
        df = pd.read_excel(fp)
        
        # Ensure Quantity is numeric
        df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
        
        # Clean Item Name
        df['Item Name'] = df['Item Name'].astype(str).str.strip()
        
        # Aggregation
        product_stats = df.groupby('Item Name').agg({
            'Quantity': 'sum',
            'Order Number': 'count' # Using count of order number to represent frequency
        }).rename(columns={'Order Number': 'Frequency'})
        
        # Sort by Quantity descending
        top_products = product_stats.sort_values(by='Quantity', ascending=False)
        
        print(f"Total Unique Products: {len(top_products)}")
        print("-" * 50)
        print("Top 10 Products by Total Quantity Sold:")
        print(top_products.head(10))
        
        # Save to CSV
        top_products.to_csv(output_csv)
        print("-" * 50)
        print(f"Full product analysis saved to: {output_csv}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
