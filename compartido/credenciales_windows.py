# Archivo: credenciales_windows.py
# Ruta: compartido/credenciales_windows.py
# Uso: from compartido.credenciales_windows import guardar_credencial, leer_credencial, borrar_credencial
# Guarda contraseñas en el Administrador de credenciales de Windows (cifradas por Windows para el usuario actual)
import ctypes
from ctypes import wintypes

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2


class _CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ('Flags', wintypes.DWORD),
        ('Type', wintypes.DWORD),
        ('TargetName', wintypes.LPWSTR),
        ('Comment', wintypes.LPWSTR),
        ('LastWritten', wintypes.FILETIME),
        ('CredentialBlobSize', wintypes.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)),
        ('Persist', wintypes.DWORD),
        ('AttributeCount', wintypes.DWORD),
        ('Attributes', ctypes.c_void_p),
        ('TargetAlias', wintypes.LPWSTR),
        ('UserName', wintypes.LPWSTR),
    ]


def _advapi32():
    advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
    advapi32.CredWriteW.argtypes = [ctypes.POINTER(_CREDENTIAL), wintypes.DWORD]
    advapi32.CredWriteW.restype = wintypes.BOOL
    advapi32.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                   ctypes.POINTER(ctypes.POINTER(_CREDENTIAL))]
    advapi32.CredReadW.restype = wintypes.BOOL
    advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    advapi32.CredDeleteW.restype = wintypes.BOOL
    advapi32.CredFree.argtypes = [ctypes.c_void_p]
    advapi32.CredFree.restype = None
    return advapi32


def guardar_credencial(destino, usuario, contrasena):
    """Crea o reemplaza la credencial. Retorna True si Windows la guardó"""
    try:
        datos = contrasena.encode('utf-16-le')
        blob = (ctypes.c_ubyte * len(datos)).from_buffer_copy(datos)
        cred = _CREDENTIAL()
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = destino
        cred.UserName = usuario
        cred.CredentialBlobSize = len(datos)
        cred.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_ubyte))
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE
        return bool(_advapi32().CredWriteW(ctypes.byref(cred), 0))
    except Exception:
        return False


def leer_credencial(destino):
    """Retorna (usuario, contraseña) o (None, None) si no existe"""
    try:
        advapi32 = _advapi32()
        puntero = ctypes.POINTER(_CREDENTIAL)()
        if not advapi32.CredReadW(destino, CRED_TYPE_GENERIC, 0, ctypes.byref(puntero)):
            return None, None
        try:
            cred = puntero.contents
            datos = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
            return cred.UserName, datos.decode('utf-16-le')
        finally:
            advapi32.CredFree(puntero)
    except Exception:
        return None, None


def borrar_credencial(destino):
    try:
        return bool(_advapi32().CredDeleteW(destino, CRED_TYPE_GENERIC, 0))
    except Exception:
        return False
