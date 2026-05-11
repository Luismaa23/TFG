# MenuMatch — Tu menú del día óptimo

MenuMatch es una aplicación web de recomendación de menús del día desarrollada con Python y Streamlit. Su objetivo es ayudar a los usuarios a elegir el menú más adecuado según sus preferencias dietéticas, restricciones alimentarias y presupuesto disponible. Este proyecto forma parte de un Trabajo de Fin de Grado (TFG).

## Características Principales

La aplicación conecta dos tipos de actores principales:
* **Restaurantes**: suben sus platos diarios a la plataforma (manual o CSV).
* **Usuarios**: reciben recomendaciones personalizadas de menú.

### Motores de Recomendación y Evaluación
* **Motor Heurístico**: Basado en reglas estrictas (filtrado por presupuesto, restricciones y alérgenos) y un sistema de *soft scoring* basado en las calorías y el precio.
* **Motor de Machine Learning (ML)**: Integración de un modelo de Regresión Logística, entrenado utilizando las evaluaciones recopiladas de los usuarios como dataset.
* **A/B Testing**: Validación en doble carril (heurístico vs. modelo ML) en producción para medir el rendimiento de ambos sistemas.

### Sistema de Roles
La aplicación implementa un sistema de acceso basado en roles con autenticación segura (hash bcrypt):
* **Usuario**: Puede configurar restricciones, recibir recomendaciones, evaluar menús, hacer pedidos libres en la "Carta Completa" y ver su historial de pedidos.
* **Restaurante**: Puede cargar y gestionar los menús disponibles.
* **Admin**: Acceso completo, incluyendo un panel de administración para el CRUD de usuarios.

## Arquitectura y Tecnologías

* **Lenguaje**: Python 3.10+
* **Framework Web**: Streamlit 1.54+
* **Base de Datos Local**: SQLite (módulo `sqlite3` nativo)
* **Base de Datos Externa (Backup)**: Google Sheets (a través de `gspread`)
* **Machine Learning**: `scikit-learn` y `joblib`
* **Arquitectura**: Sigue un patrón análogo a **MVVM** (Model-View-ViewModel) adaptado a Streamlit, separando la UI (`pages/`), la lógica de negocio (`utils/`) y el acceso a datos.
* **Diseño Visual**: Tema oscuro profesional inspirado en Tailwind CSS (Slate/Blue).

## Estructura del Proyecto

* `app.py`: Punto de entrada de la aplicación, configuración global y enrutamiento (`st.navigation`).
* `pages/`: Vistas de Streamlit para las diferentes pantallas (Login, Inicio, Carga de Menú, Recomendaciones, Admin, etc.).
* `utils/`: Módulos de lógica de negocio (autenticación, base de datos, motor heurístico, almacenamiento de menús, componentes de UI y tema).
* `data/`: Contiene la base de datos SQLite (`menumatch.db`).
* `models/`: Modelos de Machine Learning entrenados y serializados.

## Ejecución Local

1. Clona el repositorio.
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación de Streamlit:
   ```bash
   streamlit run app.py
   ```

## Documentación Adicional

Para más detalles sobre la arquitectura, decisiones de diseño y estado de desarrollo, consulta los siguientes archivos:
* `CONTEXTO_PROYECTO.txt`: Resumen global del proyecto, estructura y flujos.
* `DECISIONES_PROYECTO.txt`: Registro de decisiones arquitectónicas (ADRs) que justifican el "por qué" de cada implementación técnica.
