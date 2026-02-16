
import os

files = ['process_pathao_orders.py', 'app_modules/__init__.py', 'app_modules/processor.py', 'app_modules/utils.py', 'app_modules/zones.py']

for f in files:
    if os.path.exists(f):
        try:
            with open(f, 'rb') as fp:
                content = fp.read()
                print(f"File: {f}, Size: {len(content)}, Null Bytes: {b'\x00' in content}")
                if content.startswith(b'\xff\xfe'):
                    print(f"File: {f} has UTF-16 LE BOM")
                elif content.startswith(b'\xfe\xff'):
                    print(f"File: {f} has UTF-16 BE BOM")
                elif content.startswith(b'\xef\xbb\xbf'):
                    print(f"File: {f} has UTF-8 BOM")
        except Exception as e:
            print(f"Error reading {f}: {e}")
    else:
        print(f"File not found: {f}")
