import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path


class GestorLicencias:
    """Gestor de licencias con sistema de cache local"""

    def __init__(self, nombre_app="MensajesBiblicos"):
        self.nombre_app = nombre_app
        self.url_backend = "https://automapro-backend.onrender.com/api/public/verificar-licencia"
        
        # Código developer maestro (funciona para todas las apps)
        self.codigo_developer_master = "LIC-MASTER-WELLI"
        
        # Ruta del archivo de configuración local
        if os.name == 'nt':  # Windows
            base_path = Path(os.environ.get('USERPROFILE', '~'))
        else:  # Linux/Mac
            base_path = Path.home()
        
        self.carpeta_config = base_path / '.config' / 'AutomaPro' / nombre_app
        self.archivo_config = self.carpeta_config / 'config.json'
        self.dias_revalidacion = 7  # Re-verificar cada 7 días (solo TRIAL)

        # Respaldo permanente en AppData (más resistente a limpiadores)
        if os.name == 'nt':
            appdata = Path(os.environ.get('LOCALAPPDATA', base_path / 'AppData' / 'Local'))
        else:
            appdata = Path.home() / '.local' / 'share'
        self.carpeta_respaldo = appdata / 'AutomaPro' / nombre_app
        self.archivo_respaldo = self.carpeta_respaldo / 'lic.json'

    def _es_codigo_developer_permanente(self, codigo):
        """Verifica si es un código developer master"""
        return codigo == self.codigo_developer_master

    def obtener_uuid_dispositivo(self):
        """Genera un UUID único y estable basado en el hardware del dispositivo"""
        import hashlib
        import socket
        import uuid as uuid_mod
        try:
            # Combinar múltiples identificadores del dispositivo
            nombre_pc = socket.gethostname()
            usuario_win = os.environ.get('USERNAME', 'unknown')
            mac = ':'.join(['{:02x}'.format((uuid_mod.getnode() >> i) & 0xff)
                           for i in range(0, 48, 8)][::-1])
            identificador = f"{nombre_pc}_{usuario_win}_{mac}_{self.nombre_app}"
            return hashlib.sha256(identificador.encode()).hexdigest()[:32]
        except Exception:
            # Fallback — usar UUID guardado localmente
            archivo_uuid = self.carpeta_config / 'device.uuid'
            if archivo_uuid.exists():
                return archivo_uuid.read_text().strip()
            nuevo_uuid = str(uuid_mod.uuid4()).replace('-', '')[:32]
            self.carpeta_config.mkdir(parents=True, exist_ok=True)
            archivo_uuid.write_text(nuevo_uuid)
            return nuevo_uuid

    def registrar_instalacion(self, email=None):
        """Registra la instalación en el backend y obtiene código TRIAL automáticamente"""
        try:
            device_uuid = self.obtener_uuid_dispositivo()
            payload = {'deviceUuid': device_uuid, 'nombreApp': self.nombre_app}
            if email:
                payload['email'] = email
            response = requests.post(
                f"{self.url_backend.replace('/verificar-licencia', '')}/registrar-instalacion",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            if response.status_code == 200:
                datos = response.json()
                codigo = datos.get('codigo')
                if codigo:
                    self.guardar_codigo_licencia(codigo)
                    return codigo
        except Exception as e:
            print(f"⚠️  Error registrando instalación: {e}")
        return None

    def recuperar_licencia_full_por_email(self, email):
        """Recupera licencia FULL por email (para reinstalaciones)"""
        try:
            url = self.url_backend.replace('/verificar-licencia', '/licencia-por-email')
            response = requests.get(
                url,
                params={'email': email, 'app': self.nombre_app},
                timeout=10
            )
            if response.status_code == 200:
                datos = response.json()
                codigo = datos.get('codigo')
                if codigo:
                    self.guardar_codigo_licencia(codigo)
                    return codigo
        except Exception as e:
            print(f"⚠️  Error recuperando licencia: {e}")
        return None

    def verificar_actualizacion(self, version_actual):
        """
        Consulta al backend si hay una versión más reciente disponible.
        Retorna dict con: hay_actualizacion, version_actual, version_nueva
        """
        try:
            url = "https://automapro-backend.onrender.com/api/public/version?nombre=MensajesBiblicos"
            respuesta = requests.get(url, timeout=10)
            if respuesta.status_code == 200:
                datos = respuesta.json()
                version_nueva = datos.get('version', version_actual)
                url_descarga = datos.get('rutaArchivo', '')
                hay_actualizacion = self._es_version_mayor(version_nueva, version_actual)
                return {
                    'hay_actualizacion': hay_actualizacion,
                    'version_actual': version_actual,
                    'version_nueva': version_nueva,
                    'url_descarga': url_descarga,
                    'ruta_archivo': url_descarga
                }
        except Exception as e:
            print(f"ℹ️  No se pudo consultar actualizaciones, se intentará la próxima vez ({type(e).__name__})")
        return {'hay_actualizacion': False}

    @staticmethod
    def _es_version_mayor(nueva, actual):
        """Compara por números: 1.10.0 es mayor que 1.9.2, y 1.0.2 no es mayor que 1.1.0"""
        def partes(version):
            try:
                numeros = [int(p) for p in str(version).strip().split('.')]
            except ValueError:
                return None
            return tuple(numeros + [0] * (3 - len(numeros)))

        n, a = partes(nueva), partes(actual)
        if n is None or a is None:
            return False
        return n > a

    def obtener_codigo_guardado(self):
        """Obtiene el código de licencia guardado localmente"""
        try:
            if self.archivo_config.exists():
                contenido = self.archivo_config.read_text(encoding='utf-8').strip()
                if not contenido:
                    return ''
                datos = json.loads(contenido)
                return datos.get('codigo_licencia', '')
        except Exception as e:
            print(f"Error leyendo configuración local: {e}")
        return ''

    def guardar_codigo_licencia(self, codigo):
        """Guarda el código de licencia localmente"""
        try:
            self.carpeta_config.mkdir(parents=True, exist_ok=True)
            
            datos = {}
            if self.archivo_config.exists():
                with open(self.archivo_config, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
            
            datos['codigo_licencia'] = codigo
            
            with open(self.archivo_config, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error guardando código de licencia: {e}")
            return False

    def _obtener_cache_local(self):
        """Obtiene la información de cache local, con fallback a respaldo AppData"""
        cache = self._leer_cache(self.archivo_config)
        if cache:
            return cache

        # Fallback: restaurar desde respaldo AppData
        cache_respaldo = self._leer_cache(self.archivo_respaldo, es_respaldo=True)
        if cache_respaldo:
            try:
                self.carpeta_config.mkdir(parents=True, exist_ok=True)
                config = {'datos_licencia': cache_respaldo}
                with open(self.archivo_respaldo, 'r', encoding='utf-8') as f:
                    respaldo = json.load(f)
                if respaldo.get('codigo_licencia'):
                    config['codigo_licencia'] = respaldo['codigo_licencia']
                with open(self.archivo_config, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            except Exception:
                pass
            return cache_respaldo

        return None

    def _leer_cache(self, archivo, es_respaldo=False):
        """Lee y valida cache desde un archivo"""
        try:
            archivo = Path(archivo)
            if not archivo.exists():
                return None
            contenido = archivo.read_text(encoding='utf-8').strip()
            if not contenido:
                return None
            datos = json.loads(contenido)
            cache = datos.get('datos_licencia')
            if not cache:
                return None
            if cache.get('es_developer_permanente'):
                return cache
            if cache.get('tipo') in ['FULL', 'MASTER'] and cache.get('valida'):
                return cache
            fecha_verificacion = cache.get('fecha_verificacion')
            if fecha_verificacion:
                fecha_cache = datetime.fromisoformat(fecha_verificacion)
                dias = (datetime.now() - fecha_cache).days
                if dias <= self.dias_revalidacion:
                    return cache
        except Exception as e:
            print(f"Error leyendo cache: {e}")
        return None

    def _guardar_cache_local(self, datos_licencia):
        """Guarda los datos de la licencia en cache local y respaldo"""
        datos_cache = {
            'tipo': datos_licencia.get('tipo'),
            'valida': datos_licencia.get('valida'),
            'expirada': datos_licencia.get('expirada'),
            'dias_restantes': datos_licencia.get('diasRestantes'),
            'fecha_verificacion': datetime.now().isoformat(),
            'es_developer_permanente': datos_licencia.get('developer_permanente', False)
        }

        # Guardar en ubicación principal
        try:
            self.carpeta_config.mkdir(parents=True, exist_ok=True)
            config = {}
            if self.archivo_config.exists():
                contenido = self.archivo_config.read_text(encoding='utf-8').strip()
                if contenido:
                    config = json.loads(contenido)
            config['datos_licencia'] = datos_cache
            with open(self.archivo_config, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando cache principal: {e}")

        # Guardar respaldo en AppData solo para FULL/MASTER/developer
        tipo = datos_licencia.get('tipo', 'TRIAL')
        es_full = tipo in ['FULL', 'MASTER'] or datos_licencia.get('developer_permanente', False)
        if es_full:
            try:
                self.carpeta_respaldo.mkdir(parents=True, exist_ok=True)
                respaldo = {
                    'codigo_licencia': self.obtener_codigo_guardado(),
                    'datos_licencia': datos_cache
                }
                with open(self.archivo_respaldo, 'w', encoding='utf-8') as f:
                    json.dump(respaldo, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error guardando respaldo: {e}")

        return True

    def verificar_licencia(self, codigo_licencia, mostrar_mensajes=True, forzar_backend=False):
        """
        Verifica la licencia contra el backend
        
        CRÍTICO: Si el backend NO está disponible:
        - CON cache válido → Acepta la licencia (modo offline)
        - SIN cache válido → RECHAZA TODO (seguridad)
        
        Args:
            codigo_licencia: Código a verificar
            mostrar_mensajes: Si mostrar mensajes de debug
            
        Returns:
            dict: Información de la licencia
        """
        # Verificar si es código developer master (funciona sin backend)
        if self._es_codigo_developer_permanente(codigo_licencia):
            datos_permanente = {
                'tipo': 'FULL',
                'valida': True,
                'expirada': False,
                'diasRestantes': 999,
                'developer_permanente': True
            }
            self._guardar_cache_local(datos_permanente)
            
            if mostrar_mensajes:
                print("👑 Licencia MASTER permanente activada")
            
            return {
                'tipo': 'FULL',
                'valida': True,
                'expirada': False,
                'diasRestantes': 999,
                'mensaje': 'Licencia MASTER permanente',
                'desde_cache': False,
                'developer_permanente': True
            }
        
        # Intentar verificar contra backend SIEMPRE primero
        # El cache solo se usa como fallback cuando el backend no está disponible
        cache = self._obtener_cache_local()
        
        try:
            if mostrar_mensajes:
                print(f"🔍 Verificando licencia: {codigo_licencia}")
            
            response = requests.post(
                self.url_backend,
                json={'codigoLicencia': codigo_licencia},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                datos = response.json()
                
                # Guardar en cache
                self._guardar_cache_local(datos)
                
                if mostrar_mensajes:
                    if datos.get('valida'):
                        tipo = datos.get('tipo', 'TRIAL')
                        print(f"✅ Licencia {tipo} verificada correctamente")
                    else:
                        print("❌ Licencia inválida o expirada")
                
                return {
                    'tipo': datos.get('tipo', 'TRIAL'),
                    'valida': datos.get('valida', False),
                    'expirada': datos.get('expirada', False),
                    'diasRestantes': datos.get('diasRestantes'),
                    'mensaje': datos.get('mensaje', ''),
                    'desde_cache': False,
                    'developer_permanente': False
                }
            else:
                raise Exception(f"Error del servidor: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            # Backend no disponible — solo FULL/MASTER pueden usar cache offline
            tipo_cache = cache.get('tipo', 'TRIAL') if cache else 'TRIAL'
            es_full_cache = tipo_cache in ['FULL', 'MASTER'] or (cache and cache.get('es_developer_permanente'))
            if not forzar_backend and cache and cache.get('valida') and es_full_cache:
                # SI hay cache válido → Modo offline permitido
                if mostrar_mensajes:
                    print("⚠️  Backend no disponible. Usando cache local.")
                
                # Extender fecha de verificación
                if not cache.get('es_developer_permanente'):
                    cache['fecha_verificacion'] = datetime.now().isoformat()
                    try:
                        with open(self.archivo_config, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        config['datos_licencia'] = cache
                        with open(self.archivo_config, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                
                return {
                    'tipo': cache.get('tipo', 'TRIAL'),
                    'valida': True,
                    'expirada': False,
                    'diasRestantes': cache.get('dias_restantes'),
                    'mensaje': 'Licencia válida (backend no disponible, usando cache)',
                    'desde_cache': True,
                    'developer_permanente': cache.get('es_developer_permanente', False)
                }
            else:
                # SIN cache válido → RECHAZAR TODO (SEGURIDAD)
                if mostrar_mensajes:
                    print("❌ Backend no disponible y no hay cache válido")
                    print("❌ No se puede verificar la licencia")
                
                return {
                    'tipo': 'TRIAL',
                    'valida': False,
                    'expirada': False,
                    'diasRestantes': None,
                    'mensaje': 'No se pudo verificar la licencia. Servidor no disponible.',
                    'desde_cache': False,
                    'developer_permanente': False
                }
                
        except requests.exceptions.Timeout:
            # Timeout — solo FULL/MASTER pueden usar cache offline
            tipo_cache = cache.get('tipo', 'TRIAL') if cache else 'TRIAL'
            es_full_cache = tipo_cache in ['FULL', 'MASTER'] or (cache and cache.get('es_developer_permanente'))
            if not forzar_backend and cache and cache.get('valida') and es_full_cache:
                if mostrar_mensajes:
                    print("⚠️  Timeout al verificar. Usando cache local.")
                
                # Extender fecha de verificación
                if not cache.get('es_developer_permanente'):
                    cache['fecha_verificacion'] = datetime.now().isoformat()
                    try:
                        with open(self.archivo_config, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        config['datos_licencia'] = cache
                        with open(self.archivo_config, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                
                return {
                    'tipo': cache.get('tipo', 'TRIAL'),
                    'valida': True,
                    'expirada': False,
                    'diasRestantes': cache.get('dias_restantes'),
                    'mensaje': 'Licencia válida (timeout, usando cache)',
                    'desde_cache': True,
                    'developer_permanente': cache.get('es_developer_permanente', False)
                }
            else:
                if mostrar_mensajes:
                    print("❌ Timeout y no hay cache disponible")
                
                return {
                    'tipo': 'TRIAL',
                    'valida': False,
                    'expirada': False,
                    'diasRestantes': None,
                    'mensaje': 'Timeout al verificar licencia',
                    'desde_cache': False,
                    'developer_permanente': False
                }
                
        except Exception as e:
            # Error general — solo FULL/MASTER pueden usar cache offline
            tipo_cache = cache.get('tipo', 'TRIAL') if cache else 'TRIAL'
            es_full_cache = tipo_cache in ['FULL', 'MASTER'] or (cache and cache.get('es_developer_permanente'))
            if not forzar_backend and cache and cache.get('valida') and es_full_cache:
                if mostrar_mensajes:
                    print(f"⚠️  Error al verificar ({e}). Usando cache local.")
                
                # Extender fecha de verificación
                if not cache.get('es_developer_permanente'):
                    cache['fecha_verificacion'] = datetime.now().isoformat()
                    try:
                        with open(self.archivo_config, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                        config['datos_licencia'] = cache
                        with open(self.archivo_config, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                
                return {
                    'tipo': cache.get('tipo', 'TRIAL'),
                    'valida': True,
                    'expirada': False,
                    'diasRestantes': cache.get('dias_restantes'),
                    'mensaje': f'Licencia válida (error: {e}, usando cache)',
                    'desde_cache': True,
                    'developer_permanente': cache.get('es_developer_permanente', False)
                }
            else:
                # SIN cache → RECHAZAR (CRÍTICO PARA SEGURIDAD)
                if mostrar_mensajes:
                    print(f"❌ Error: {e}")
                    print("❌ No hay cache válido, licencia rechazada")
                
                return {
                    'tipo': 'TRIAL',
                    'valida': False,
                    'expirada': False,
                    'diasRestantes': None,
                    'mensaje': f'Error al verificar: {e}',
                    'desde_cache': False,
                    'developer_permanente': False
                }

    def verificar_e_iniciar(self, mostrar_mensajes=True):
        """
        Verifica la licencia guardada e inicia la aplicación
        
        Returns:
            dict: Datos de la licencia verificada
        """
        codigo = self.obtener_codigo_guardado()
        
        if not codigo:
            if mostrar_mensajes:
                print("❌ No hay código de licencia guardado")
            return {
                'tipo': 'TRIAL',
                'valida': False,
                'expirada': False,
                'diasRestantes': None,
                'mensaje': 'No hay código de licencia',
                'desde_cache': False,
                'developer_permanente': False
            }
        
        return self.verificar_licencia(codigo, mostrar_mensajes)

    def limpiar_cache(self):
        """Elimina el cache local (fuerza re-verificación)"""
        try:
            if self.archivo_config.exists():
                self.archivo_config.unlink()
                print("✅ Cache eliminado correctamente")
                return True
        except Exception as e:
            print(f"❌ Error al eliminar cache: {e}")
            return False


# Función de compatibilidad para código existente
def verificar_licencia_inicio():
    """Función helper para verificar licencia al inicio (mantiene compatibilidad)"""
    from dialogos_licencia import DialogosLicencia
    
    gestor = GestorLicencias()
    codigo_guardado = gestor.obtener_codigo_guardado()
    
    if not codigo_guardado:
        codigo = DialogosLicencia.solicitar_codigo_licencia()
        if codigo:
            gestor.guardar_codigo_licencia(codigo)
            codigo_guardado = codigo
        else:
            print("❌ No se ingresó código de licencia")
            return None
    
    resultado = gestor.verificar_licencia(codigo_guardado)
    
    if not resultado['valida']:
        DialogosLicencia.mostrar_trial_expirado()
        return None
    
    if resultado.get('developer_permanente'):
        print("👑 Licencia developer permanente activada")
    elif resultado['tipo'] == 'TRIAL':
        DialogosLicencia.mostrar_banner_trial(resultado.get('diasRestantes', 0))
    else:
        print(f"✅ Licencia FULL activada")
    
    return resultado


if __name__ == "__main__":
    # Prueba del gestor
    print("=== Prueba del Gestor de Licencias con Cache ===\n")
    
    gestor = GestorLicencias()
    
    # Opción 1: Probar con código guardado
    print("1. Verificando con código guardado...")
    resultado = gestor.verificar_e_iniciar()
    print(f"Resultado: {resultado}\n")
    
    # Opción 2: Probar con código developer
    print("2. Probando código LIC-MASTER-WELLI...")
    resultado = gestor.verificar_licencia("LIC-MASTER-WELLI")
    print(f"Resultado: {resultado}\n")