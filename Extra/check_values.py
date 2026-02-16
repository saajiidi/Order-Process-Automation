import pandas as pd

fp = 'h:/Analysis/New_/orders-2026-02-14-16-09-28.xlsx'
df = pd.read_excel(fp)
print(df[['Item Name', 'Quantity', 'Item Cost']].head())
