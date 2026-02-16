import pandas as pd

df = pd.read_excel('Test_beta.xlsx')
print("Columns:", df.columns.tolist())
if 'trxId' in df.columns:
    print("trxId values:", df['trxId'].unique())
else:
    print("trxId column not found exactly.")
    # check for similar
    for c in df.columns:
        if 'trx' in c.lower():
            print(f"Found similar column: {c}")
