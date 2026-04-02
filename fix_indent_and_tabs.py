import os

# 1. Fix indent in distribution_tab.py
dist_path = 'app_modules/distribution_tab.py'
with open(dist_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(44, len(lines)):
    if lines[i].startswith('    '):
        lines[i] = lines[i][4:]

with open(dist_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

# 2. Update ui_config.py
ui_path = 'app_modules/ui_config.py'
with open(ui_path, 'r', encoding='utf-8') as f:
    ui_c = f.read()

ui_c = ui_c.replace(
    '"Orders",\n    "Inventory Distribution",',
    '"Pathao Panel",\n    "Text Parser",\n    "Inventory Distribution",'
)
with open(ui_path, 'w', encoding='utf-8') as f:
    f.write(ui_c)


# 3. Update app.py
app_path = 'app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    app_c = f.read()

old_app = """    with nav_tabs[1]:
        orders_tabs = st.tabs(["Pathao Processor", "Delivery Text Parser"])
        with orders_tabs[0]:
            render_pathao_tab()
        with orders_tabs[1]:
            render_fuzzy_parser_tab()

    with nav_tabs[2]:
        render_distribution_tab(
            search_q=st.session_state.get("inv_matrix_search", "")
        )

    with nav_tabs[3]:
        render_wp_tab()"""

new_app = """    with nav_tabs[1]:
        render_pathao_tab()

    with nav_tabs[2]:
        render_fuzzy_parser_tab()

    with nav_tabs[3]:
        render_distribution_tab(
            search_q=st.session_state.get("inv_matrix_search", "")
        )

    with nav_tabs[4]:
        render_wp_tab()"""

app_c = app_c.replace(old_app, new_app)

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(app_c)

print("Patch applied successfully.")
