import json
from collections import defaultdict

def analyze_users_and_roles():
    try:
        with open('systemdata.combined.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: systemdata.combined.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from systemdata.combined.json.")
        return

    users = data.get('users', [])
    roles = data.get('roles', [])
    roletypes = data.get('roletypes', [])

    user_map = {user['id']: user for user in users}
    roletype_map = {roletype['id']: roletype['name'] for roletype in roletypes}

    roles_to_users = defaultdict(list)
    for role in roles:
        user_id = role.get('user_id')
        roletype_id = role.get('roletype_id')
        
        if user_id in user_map and roletype_id in roletype_map:
            user = user_map[user_id]
            role_name = roletype_map[roletype_id]
            roles_to_users[role_name].append(user)

    print("Zde jsou příklady uživatelů s různými rolemi:")
    print("============================================\n")

    # Display one user for each role found
    for role_name, user_list in roles_to_users.items():
        if user_list:
            user = user_list[0] # Just take the first one as an example
            print(f"Role: {role_name}")
            print(f"  Jméno: {user.get('name', 'N/A')} {user.get('surname', 'N/A')}")
            print(f"  Email: {user.get('email', 'N/A')}")
            print(f"  ID: {user.get('id')}")
            print("-" * 20)

if __name__ == "__main__":
    analyze_users_and_roles()
