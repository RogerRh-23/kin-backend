import re

def generate_username(nombre_completo: str, employee_id: int) -> str:
    """
    Genera un usuario tipo: RPEREZ-05
    """
    # Limpiar nombre (quitar acentos, etc) y tomar primer nombre y apellido
    parts = nombre_completo.upper().split()
    if len(parts) >= 2:
        base = f"{parts[0][0]}{parts[1]}" # RPEREZ
    else:
        base = parts[0]
        
    # Limpiamos caracteres raros
    base = re.sub(r'[^A-Z0-9]', '', base)
    
    # Añadimos el ID para evitar duplicados (Juan Perez 1 y Juan Perez 2)
    return f"{base}-{employee_id}"