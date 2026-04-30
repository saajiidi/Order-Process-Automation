import pandas as pd
import requests

url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO/pub?gid=1805297117&single=true&output=csv'

print('Loading data from Google Sheet...')
resp = requests.get(url)
df = pd.read_csv(pd.io.common.StringIO(resp.text), dtype=str)

print(f'Total rows: {len(df):,}')
print(f'Columns: {list(df.columns)}')

# Find email column
email_col = None
for col in df.columns:
    if 'email' in col.lower():
        email_col = col
        break

if email_col:
    print(f'\nFound email column: {email_col}')
    # Get unique emails (non-null, non-empty)
    emails = df[email_col].dropna()
    emails = emails[emails.str.strip() != '']
    unique_emails = sorted(emails.str.strip().str.lower().unique())
    print(f'Total unique emails: {len(unique_emails)}')
    
    # Create DataFrame and export to CSV
    emails_df = pd.DataFrame({'email': unique_emails, 'id': range(1, len(unique_emails) + 1)})
    output_file = 'unique_emails.csv'
    emails_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f'\nExported to: {output_file}')
    
    # Show first 10 emails
    print('\n--- First 10 Unique Emails ---')
    for email in unique_emails[:10]:
        print(email)
else:
    print('No email column found!')
