CORREOS FORMAT:
📁 *Novedades en *

Mostrando últimos X correos no leídos
📄 Página 1 de 4 · Mostrando 1–10 de 37

📩 (correo@ejemplo.com) [dd/mm/aaaa - hh:mm] **Asunto**
- Punto importante
- Punto importante
- Punto importante

📩 (correo2@ejemplo.com) [dd/mm/aaaa - hh:mm] **Asunto**
- Punto importante
- Punto importante
➡️ Hay más correos disponibles.

También quedó guardado que:
- Se ordenan del más reciente al más antiguo.
- Usar el correo del remitente entre paréntesis.
- Sin límite explícito, muestro los últimos 10 correos no leídos.
- Resumir cada correo con puntos de viñeta.
- Con límite, muestro exactamente esa cantidad, respetando el máximo configurado.
- No añadiré un comentario introductorio separado.
- Si existen más resultados, indicar página actual, rango mostrado y total.
- Si no existen más páginas, no mostrar "Hay más correos disponibles".

TRELLO FORMAT POR TABLERO:
📊 <Tablero en mayúsculas>
<Resumen corto tuyo de lo más prioritario>
📋 [<lista 1>] - X cards totales asignadas a mi usuario (🔴 si tengo tareas vencidas/ 🟡 si tengo tareas pendientes no vencidas / 🟢 si no tengo tareas pendientes)
📋 [<lista 2>] - X cards totales asignadas a mi usuario (🔴 si tengo tareas vencidas/ 🟡 si tengo tareas pendientes no vencidas / 🟢 si no tengo tareas pendientes)
...

TRELLO FORMAT POR LISTA:
📋 [TABLERO EN MAYÚSCULAS] - <NOMBRE LISTA EN MAYÚSCULAS>

🔴 Vencidas: X
🟡 Pendientes: X
🟢 Completadas: X

X cards asignadas a mi usuario
📄 Página 1 de 4 · Mostrando 1–10 de 34

- <Card 1> - <nombre card> (<link corto>) - 🕐 [dd/mm/aaaa hh:mm]
- <Card 2> - <nombre card> (<link corto>) - 🕐 [dd/mm/aaaa hh:mm]
- <Card 3> - <nombre card> (<link corto>)
...

➡️ Hay más cards disponibles.


CORRECCIONES:
X Actualizar el formato en la SKILL
X Limitar la cantidad de correos que te puede mostrar el list all correos MAX 100 CORREOS (CAMBIABLE POR .ENV)
X PAGINACION PARA EL METODO DE LIST ALL CORREOS
X AGREGAR UN FILTRO LIKE EN PARA LOS FILTROS EN CORREO

X Permitir que el update de cards sea masivo CON STRING DE IDS Y SOBREESCRIBIENDO CAMPOS INDICADOS
X Agregar el url como campo a las cards
X Agregar el campo dateLastActivity en cada card y ordenarlos descendentemente 
X Al listar cards en una lista -> Ordenar primero por estado: no completadas y completadas, ordenar por fecha de vencimiento; las que no tengan fecha van al final, luego por dateLastActivity,
X Limitar la cantidad de cards que te puede mostrar el list all cards MAX 100 CARDS (CAMBIABLE POR .ENV)
X PAGINACION PARA EL METODO DE LIST ALL CARDS TRELLO
X Cambiar los formatos para reflejar paginación

X Funciones tool count para no listar las cards en cada lista (tmb count con ids separados por string)
NA truncar todos los campos usando máx. length para list all y para los details (deben ser mayores pero no infinitos)
NA Si detail tuviera MUCHOS DATOS se envía como archivo de texto. ETIQUETADO COMO UNTRUSTED CONTENT

X RESUMEN DEL TABLERO PARA QUE EL MODELO NO CONSUMA TANTOS TOKENS ARMANDOLO SIEMPRE (TOKENSSS)
X AGREGAR UN FILTRO LIKE PARA LOS FILTROS EN LIST CARDS

- LIMITAR CADENAS DE 5 TOOLS TAN RAPIDO (MESSAGES RATE LIMIT) (TOOL CALL RATE LIMIT) (USAR METODO TOKEN BUCKET DE STRIPE)
- OPENCLAW (MSG RATE LIMIT) (TOKEN LIMITS IN TIME - USAR MÉTODO DE TOKEN BUCKET TAMBIEN DE STRIPE)
- VALIDAR QUE UN USUARIO TENGA PERMISO DE EJECUTAR TOOLS
- Una vez concluido lo previo probar en consola de hooks IMPRIMIR LOS DATOS DEL USUARIO QE MANDO UN MENSAJE, CANAL, PERFIL Y PERMISOS

- En formato resumen de tableros trello por defecto ocultar archivados agg parametro para mostrarlos opcional
- Para las tareas de Office usar subagente, considerar y medir gpt-5-nano si no con gpt-4o-mini tamos bien
