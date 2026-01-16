"""
Příklad implementace RBAC v GraphQL mutations
==============================================

Tento soubor ukazuje různé způsoby použití role-based access control
v GraphQL schema pomocí nového permission systému.
"""

import typing
import strawberry
from src.GraphTypeDefinitions.permissions import (
    RequireAdmin,
    RequireEditor,
    RequireViewer,
    RequireRole,
    user_has_role,
    user_has_any_role,
)
from src.GraphTypeDefinitions.context_utils import ensure_user_in_context


# ============================================================================
# Příklad 1: Admin-only mutation s permission class
# ============================================================================

@strawberry.type
class ExampleMutation1:
    @strawberry.field(
        description="Smazat asset - pouze administrátor",
        permission_classes=[RequireAdmin]  # ← Automatická kontrola role
    )
    async def delete_asset(
        self, 
        info: strawberry.types.Info, 
        asset_id: strawberry.ID
    ) -> bool:
        # Pokud user nemá admin roli, nikdy se sem nedostane
        # Strawberry vrátí chybu automaticky
        
        # Tady můžeme bezpečně smazat asset
        # loader = getLoadersFromInfo(info).AssetModel
        # await loader.delete(asset_id)
        return True


# ============================================================================
# Příklad 2: Editor or Admin s permission class
# ============================================================================

@strawberry.type
class ExampleMutation2:
    @strawberry.field(
        description="Upravit asset - editor nebo admin",
        permission_classes=[RequireEditor]  # ← Admin NEBO Editor
    )
    async def update_asset(
        self, 
        info: strawberry.types.Info, 
        asset_id: strawberry.ID,
        name: str
    ) -> bool:
        # Tuto mutaci mohou volat uživatelé s rolí:
        # - administrátor
        # - editor
        # - Estera (admin by ID)
        
        return True


# ============================================================================
# Příklad 3: Vlastní kombinace rolí
# ============================================================================

@strawberry.type
class ExampleMutation3:
    @strawberry.field(
        description="Speciální operace pro planning admin nebo system admin",
        permission_classes=[
            RequireRole(roles=["plánovací administrátor", "administrátor"])
        ]
    )
    async def special_planning_operation(
        self, 
        info: strawberry.types.Info
    ) -> str:
        return "Operace úspěšná"


# ============================================================================
# Příklad 4: Dynamická kontrola rolí uvnitř resolveru
# ============================================================================

@strawberry.type
class ExampleQuery:
    @strawberry.field(description="Získat assets s různým obsahem podle role")
    async def assets_by_permission(
        self, 
        info: strawberry.types.Info
    ) -> typing.List[str]:
        user = ensure_user_in_context(info)
        
        # Kontrola jedné konkrétní role
        if await user_has_role(user, "administrátor", info):
            # Admin vidí všechny assets včetně archived
            return ["Asset 1", "Asset 2", "Asset 3 (archived)"]
        
        # Kontrola více rolí najednou
        if await user_has_any_role(user, ["editor", "viewer"], info):
            # Editor/Viewer vidí jen aktivní assets
            return ["Asset 1", "Asset 2"]
        
        # Ostatní nevidí nic
        return []


# ============================================================================
# Příklad 5: Field-level permissions
# ============================================================================

@strawberry.type
class AssetType:
    id: strawberry.ID
    name: str
    
    # Toto pole mohou vidět jen adminové
    @strawberry.field(
        description="Cena assetu (pouze admin)",
        permission_classes=[RequireAdmin]
    )
    def price(self) -> float:
        return 1000.0
    
    # Toto pole mohou vidět editor+
    @strawberry.field(
        description="Serial number (editor nebo admin)",
        permission_classes=[RequireEditor]
    )
    def serial_number(self) -> str:
        return "SN-123456"
    
    # Toto pole mohou vidět všichni autentizovaní
    @strawberry.field(
        description="Popis (všichni)",
        permission_classes=[RequireViewer]
    )
    def description(self) -> str:
        return "Popis assetu"


# ============================================================================
# Příklad 6: Kombinace permission class + manuální kontrola
# ============================================================================

@strawberry.type
class ExampleMutation6:
    @strawberry.field(
        description="Upravit asset s pokročilou kontrolou",
        permission_classes=[RequireEditor]  # Základní kontrola: musí být editor+
    )
    async def advanced_update_asset(
        self, 
        info: strawberry.types.Info, 
        asset_id: strawberry.ID,
        price: typing.Optional[float] = None
    ) -> bool:
        user = ensure_user_in_context(info)
        
        # Základní update může dělat každý editor
        # ... update basic fields ...
        
        # Ale změnu ceny může dělat jen admin
        if price is not None:
            if not await user_has_role(user, "administrátor", info):
                raise ValueError("Změna ceny vyžaduje roli administrátor")
            # ... update price ...
        
        return True


# ============================================================================
# Příklad 7: Vlastní permission class
# ============================================================================

from strawberry.permission import BasePermission

class RequireAssetOwner(BasePermission):
    """
    Permission class, která kontroluje, zda je user vlastníkem assetu
    nebo má admin roli.
    """
    message = "Nemáte oprávnění: musíte být vlastník assetu nebo administrátor"
    
    async def has_permission(
        self, 
        source, 
        info: strawberry.types.Info, 
        asset_id: strawberry.ID,
        **kwargs
    ) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        
        # Admin má vždy přístup
        if await user_has_role(user, "administrátor", info):
            return True
        
        # Zkontroluj, zda je user vlastníkem assetu
        # loader = getLoadersFromInfo(info).AssetModel
        # asset = await loader.load(asset_id)
        # return asset.owner_id == user.get("id")
        
        return True  # Pro příklad


@strawberry.type
class ExampleMutation7:
    @strawberry.field(
        description="Upravit asset (jen vlastník nebo admin)",
        permission_classes=[RequireAssetOwner]
    )
    async def update_own_asset(
        self, 
        info: strawberry.types.Info, 
        asset_id: strawberry.ID
    ) -> bool:
        return True


# ============================================================================
# Příklad 8: Zabezpečení mutace pro "přidělení půjčené věci"
# ============================================================================

@strawberry.type
class AssetLoanAssignResponse:
    """Odpověď pro úspěšné přiřazení zápůjčky."""
    id: strawberry.ID
    asset_id: strawberry.ID
    user_id: strawberry.ID
    startdate: str

@strawberry.type
class ExampleMutation8:
    @strawberry.field(
        description="Přiřadit půjčenou věc jinému uživateli (pouze admin)",
        permission_classes=[RequireAdmin]  # <-- TADY JE TO KOUZLO!
    )
    async def asset_loan_assign(
        self,
        info: strawberry.types.Info,
        asset_id: strawberry.ID,
        user_id: strawberry.ID
    ) -> AssetLoanAssignResponse:
        # Díky `permission_classes=[RequireAdmin]` se tento kód spustí,
        # jen pokud má přihlášený uživatel roli "administrátor".
        # Není potřeba žádná další manuální kontrola.
        print(f"Admin user is assigning asset {asset_id} to user {user_id}")
        # Zde by byla logika pro vytvoření zápůjčky v databázi...
        return AssetLoanAssignResponse(id="new-loan-123", asset_id=asset_id, user_id=user_id, startdate="2026-01-15")

# ============================================================================
# Shrnutí best practices
# ============================================================================

"""
✅ DOPORUČENÉ POUŽITÍ:

1. Pro jednoduché kontroly rolí použijte permission_classes:
   - RequireAdmin
   - RequireEditor
   - RequireViewer
   - RequireRole(roles=["role1", "role2"])

2. Pro dynamickou logiku použijte helper funkce:
   - user_has_role(user, "role_name", info)
   - user_has_any_role(user, ["role1", "role2"], info)

3. Pro složitější permission logiku vytvořte vlastní BasePermission class

4. Admin by ID (Estera) má vždy přístup automaticky

❌ NEDOPORUČENÉ:

1. Hardcoded user IDs:
   if user.get("id") == "76dac14f-7114-4bb2-882d-0d762eab6f4a":

2. Kontrola rolí bez pomocných funkcí:
   # Špatně - kontrola ID role
   if user_role_id == "ced46aa4-3217-4fc1-b79d-f6be7d21c6b6":
   
   # Správně - použití helper funkce
   if await user_has_role(user, "administrátor", info):

3. Duplikování permission logiky:
   - Používejte znovupoužitelné permission classes
"""
