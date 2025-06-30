# aemet-recolector
A Python Script intended to gather data from AEMET Stations status along time in Valladolid 

README - Proyecto AEMET Recolector
==================================

Este proyecto permite recolectar automáticamente observaciones meteorológicas de AEMET para la estación de Valladolid y guardar los datos en un fichero SQLite accesible por Power BI.

ESTADO ACTUAL DEL PROYECTO
---------------------------
✔️ Código fuente y lógica de recolección disponibles en GitHub.
✔️ Copia de seguridad automática desactivada (puede lanzarse manualmente).
✔️ Web service en Render ELIMINADO para evitar consumo de horas gratuitas.
✔️ Cron-job de activación deshabilitado temporalmente.

CÓMO REACTIVAR EL PROYECTO
---------------------------
1. **Crear nuevo Web Service en Render:**
   - Tipo: Web Service (Python)
   - Origen: este repositorio de GitHub
   - Entrar a: https://dashboard.render.com/
   - Añadir variable de entorno obligatoria:
     - AEMET_API_KEY = <tu clave de AEMET>

2. **Activar el cron-job de recolección:**
   - URL del endpoint: `https://aemet-recolector.onrender.com/recolectar`
   - Frecuencia recomendada: **cada hora al minuto 35**
   - Plataforma: https://cron-job.org/
   - Motivo: mantener activo el servicio de Render y recuperar nuevos datos.

3. **(Opcional) Reactivar backups automáticos:**
   - Editar `.github/workflows/backup.yml`
   - Cambiar sección `on:` de:
     ```
     on:
       workflow_dispatch:
     ```
     a:
     ```
     on:
       schedule:
         - cron: '30 22 * * *'  # Cada día a las 00:30 hora peninsular (22:30 UTC)
       workflow_dispatch:
     ```

4. **Visualización de los datos:**
   - Descargar manualmente el `.db` desde el endpoint `/descargar-db`
   - Conectar Power BI a ese archivo
   - Los datos se actualizan cada hora (ventana móvil de 12h)

CONSIDERACIONES
---------------
- El servicio Render gratuito ofrece 750h mensuales. Si se mantiene el cron cada hora, el consumo es bajo.
- No es necesario ejecutar el cron con más frecuencia, ya que AEMET actualiza datos 1 vez por hora.
- Si el cron falla muchas veces seguidas, cron-job.org lo desactiva automáticamente (reactivarlo desde el panel).
- Si Render agota horas gratuitas, el servicio se suspende hasta el próximo mes.

CONTACTO
--------
Mantenedor: ecarran (GitHub)
Última revisión: Junio 2025
