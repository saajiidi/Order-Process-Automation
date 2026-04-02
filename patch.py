import os
for filename in os.listdir('app_modules'):
    if filename.endswith('.py'):
        path = os.path.join('app_modules', filename)
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        if c:
            c = c.replace(', hide_index=True', '').replace('hide_index=True', '')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)
