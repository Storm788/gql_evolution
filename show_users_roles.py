import json
from collections import defaultdict

# Načti systemdata
with open('systemdata.combined.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Vytvoř mapy pro rychlé vyhledávání
users_map = {u['id']: u for u in data['users']}
roletypes_map = {r['id']: r for r in data['roletypes']}

# Role IDs
ADMIN_ROLE_ID = "ced46aa4-3217-4fc1-b79d-f6be7d21c6b6"
EDITOR_ROLE_ID = "ed1707aa-0000-4000-8000-000000000001"
VIEWER_ROLE_ID = "ed1707aa-0000-4000-8000-000000000002"
READER_ROLE_ID = "ed1707aa-0000-4000-8000-000000000003"

# Seskupi uživatele podle rolí
users_by_role = defaultdict(list)

for role in data['roles']:
    if role.get('valid') == True:
        user_id = role['user_id']
        roletype_id = role['roletype_id']
        
        if user_id in users_map:
            user = users_map[user_id]
            users_by_role[roletype_id].append({
                'id': user_id,
                'name': user.get('name', ''),
                'surname': user.get('surname', ''),
                'email': user.get('email', '')
            })

# Zobraz výsledky
print("\n" + "="*80)
print("👑 ADMINISTRÁTOŘI (administrátor role)")
print("="*80)
if ADMIN_ROLE_ID in users_by_role:
    for i, user in enumerate(users_by_role[ADMIN_ROLE_ID][:15], 1):
        print(f"{i:2}. {user['name']} {user['surname']:<20} {user['email']}")
        print(f"    ID: {user['id']}")
else:
    print("  Žádní uživatelé")

print("\n" + "="*80)
print("✏️  EDITORI (editor role)")
print("="*80)
if EDITOR_ROLE_ID in users_by_role:
    for i, user in enumerate(users_by_role[EDITOR_ROLE_ID][:15], 1):
        print(f"{i:2}. {user['name']} {user['surname']:<20} {user['email']}")
        print(f"    ID: {user['id']}")
else:
    print("  Žádní uživatelé")

print("\n" + "="*80)
print("👁️  VIEWEŘI (viewer role)")
print("="*80)
if VIEWER_ROLE_ID in users_by_role:
    for i, user in enumerate(users_by_role[VIEWER_ROLE_ID][:15], 1):
        print(f"{i:2}. {user['name']} {user['surname']:<20} {user['email']}")
        print(f"    ID: {user['id']}")
else:
    print("  Žádní uživatelé")

print("\n" + "="*80)
print("📖 ČTENÁŘI (reader role)")
print("="*80)
if READER_ROLE_ID in users_by_role:
    for i, user in enumerate(users_by_role[READER_ROLE_ID][:15], 1):
        print(f"{i:2}. {user['name']} {user['surname']:<20} {user['email']}")
        print(f"    ID: {user['id']}")
else:
    print("  Žádní uživatelé")

print("\n" + "="*80)
print("📊 STATISTIKA")
print("="*80)
print(f"Celkem uživatelů: {len(data['users'])}")
print(f"Celkem typů rolí: {len(data['roletypes'])}")
print(f"Celkem přiřazení rolí: {len([r for r in data['roles'] if r.get('valid') == True])}")
print(f"\nPočty uživatelů v jednotlivých rolích:")
for roletype_id, users in sorted(users_by_role.items(), key=lambda x: -len(x[1]))[:10]:
    roletype = roletypes_map.get(roletype_id, {})
    role_name = roletype.get('name_en', roletype.get('name', 'Neznámá role'))
    print(f"  - {role_name:<30} {len(users):3} uživatelů")
