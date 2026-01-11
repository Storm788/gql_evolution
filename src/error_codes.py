"""
Error Code Dictionary for Asset Management API

All error codes are UUIDs for unique identification.
Format: {code: (category, description)}
"""

from uuid import UUID

ERROR_CODES = {
    # Asset Loan Errors (3xxx...)
    UUID("3f7a1b2c-4e5d-4a6b-8c9d-0e1f2a3b4c5d"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze administrátor může vytvářet zápůjčky majetku"
    ),
    UUID("3f7a1b2c-4e5d-4a6b-8c9d-0e1f2a3b4c5e"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO", 
        "Pouze administrátor může upravovat zápůjčky majetku"
    ),
    UUID("3f7a1b2c-4e5d-4a6b-8c9d-0e1f2a3b4c5f"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze administrátor může mazat zápůjčky majetku"
    ),
    UUID("3f7a1b2c-4e5d-4a6b-8c9d-0e1f2a3b4c60"): (
        "NENALEZENO",
        "Zápůjčka majetku nebyla nalezena"
    ),
    UUID("3f7a1b2c-4e5d-4a6b-8c9d-0e1f2a3b4c61"): (
        "VALIDAČNÍ_CHYBA",
        "Neplatná data zápůjčky majetku"
    ),
    
    # Asset Errors (4xxx...)
    UUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d6e"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze administrátor může vytvářet majetek"
    ),
    UUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d6f"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze správce (custodian) nebo administrátor může upravit majetek"
    ),
    UUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d70"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze administrátor může mazat majetek"
    ),
    UUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d71"): (
        "NENALEZENO",
        "Majetek nebyl nalezen"
    ),
    UUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d72"): (
        "VALIDAČNÍ_CHYBA",
        "Neplatná data majetku"
    ),
    
    # Inventory Record Errors (5xxx...)
    UUID("5b9c3d4e-6f7a-4c8d-0e1f-2a3b4c5d6e7f"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze administrátor může vytvářet inventarizační záznamy"
    ),
    UUID("5b9c3d4e-6f7a-4c8d-0e1f-2a3b4c5d6e80"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze administrátor může upravovat inventarizační záznamy"
    ),
    UUID("5b9c3d4e-6f7a-4c8d-0e1f-2a3b4c5d6e81"): (
        "OPRÁVNĚNÍ_ZAMÍTNUTO",
        "Pouze administrátor může mazat inventarizační záznamy"
    ),
    UUID("5b9c3d4e-6f7a-4c8d-0e1f-2a3b4c5d6e82"): (
        "NENALEZENO",
        "Inventarizační záznam nebyl nalezen"
    ),
    UUID("5b9c3d4e-6f7a-4c8d-0e1f-2a3b4c5d6e83"): (
        "VALIDAČNÍ_CHYBA",
        "Neplatná data inventarizačního záznamu"
    ),
    
    # Authentication Errors (1xxx...)
    UUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3d"): (
        "VYŽADOVÁNA_AUTENTIZACE",
        "Uživatel musí být autentizován"
    ),
    UUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3e"): (
        "NEPLATNÝ_TOKEN",
        "Neplatný autentizační token"
    ),
    
    # General Errors (2xxx...)
    UUID("2b1c2d3e-4f5a-4b6c-7d8e-9f0a1b2c3d4e"): (
        "CHYBA_DATABÁZE",
        "Databázová operace selhala"
    ),
    UUID("2b1c2d3e-4f5a-4b6c-7d8e-9f0a1b2c3d4f"): (
        "PORUŠENÍ_CIZÍHO_KLÍČE",
        "Reference odkazuje na neexistující entitu"
    ),
}

def get_error_info(code: UUID) -> tuple[str, str]:
    """Get error category and description for a given error code."""
    return ERROR_CODES.get(code, ("NEZNÁMÁ_CHYBA", "Došlo k neznámé chybě"))

def format_error_message(code: UUID, additional_context: str = "") -> str:
    """Format complete error message with code, category and description."""
    category, description = get_error_info(code)
    base_msg = f"[{category}] {description}"
    return f"{base_msg} – {additional_context}" if additional_context else base_msg
