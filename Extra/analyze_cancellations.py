import pandas as pd
import os
import sys

# Set encoding for stdout to handle special characters
sys.stdout.reconfigure(encoding='utf-8')

fp = 'h:/Analysis/New_/merged_orders_2026-02-15.xlsx'
output_csv = 'h:/Analysis/New_/cancellation_summary.csv'

if not os.path.exists(fp):
    print(f"File not found: {fp}")
else:
    try:
        df = pd.read_excel(fp)
        
        # Filter for non-empty notes
        # Convert to string to avoid issues, strip whitespace
        df['Customer Note'] = df['Customer Note'].astype(str).str.strip()
        notes_df = df[df['Customer Note'] != 'nan'].copy()
        
        if notes_df.empty:
            print("No customer notes found.")
        else:
            # Normalize notes for better counting (lowercase)
            notes_df['Normalized Note'] = notes_df['Customer Note'].str.lower()
            
            # Count the reasons
            counts = notes_df['Normalized Note'].value_counts()
            
            print(f"Found {len(counts)} unique cancellation reasons.")
            print("-" * 30)
            
            # Print top 20 to console, ensuring safe printing
            for note, count in counts.head(20).items():
                try:
                    print(f"{note}: {count}")
                except UnicodeEncodeError:
                    print(f"[Special Chars]: {count}")
            
            # Save full counts to CSV
            counts.to_csv(output_csv, header=['Count'])
            print("-" * 30)
            print(f"Full breakdown saved to: {output_csv}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
