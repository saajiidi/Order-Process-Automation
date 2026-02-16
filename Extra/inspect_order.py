import pandas as pd

df = pd.read_excel('Test_beta.xlsx')
row = df[df['Order Number'] == 191280]
print(row[['Order Number', 'Payment Method Title', 'trxId']])
