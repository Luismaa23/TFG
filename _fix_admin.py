"""Script temporal para reparar la línea corrupta en 6_Admin.py."""
import re

path = "pages/6_Admin.py"
content = open(path, "r", encoding="utf-8").read()
lines = content.split("\n")

# Buscar la línea corrupta (la que empieza con el comentario escapeado)
target_idx = None
for i, line in enumerate(lines):
    if r"\u2500\u2500 Bot" in line or (
        "btn_train_ml" in line and len(line) > 300
    ):
        target_idx = i
        break

if target_idx is None:
    # Buscar por el comentario de entrenamiento con escapados literales
    for i, line in enumerate(lines):
        if "\\\\u2500" in line and "Bot" in line:
            target_idx = i
            break

print(f"Línea corrupta encontrada en índice: {target_idx}")
if target_idx is not None:
    print(f"Preview: {repr(lines[target_idx][:100])}")

# Bloque correcto como lista de líneas (sin problemas de escape en PowerShell)
new_lines = [
    "            # \u2500\u2500 Bot\u00f3n de entrenamiento \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
    '            if st.button("\U0001f9e0 Entrenar Modelo de IA", type="primary", key="btn_train_ml", use_container_width=True):',
    "                try:",
    '                    with st.spinner("Entrenando modelo..."):',
    "                        resultado = train_and_evaluate_model()",
    "",
    '                    if resultado.get("warning"):',
    "                        st.warning(resultado[\"warning\"])",
    "",
    '                    st.success("\u2705 \u00a1Modelo entrenado y guardado con \u00e9xito!")',
    "",
    "                    col_acc, col_n, col_train, col_test = st.columns(4)",
    "                    with col_acc:",
    "                        st.metric(",
    '                            label="Accuracy",',
    "                            value=f\"{resultado['accuracy'] * 100:.1f}%\",",
    '                            help="Porcentaje de predicciones correctas sobre el conjunto de test.",',
    "                        )",
    "                    with col_n:",
    "                        st.metric(",
    '                            label="Dataset total",',
    '                            value=resultado["n_total"],',
    '                            help="N\u00famero total de evaluaciones usadas.",',
    "                        )",
    "                    with col_train:",
    "                        st.metric(",
    '                            label="Muestras train",',
    '                            value=resultado["n_train"],',
    '                            help="Registros usados para entrenar el modelo (80%).",',
    "                        )",
    "                    with col_test:",
    "                        st.metric(",
    '                            label="Muestras test",',
    '                            value=resultado["n_test"],',
    '                            help="Registros usados para evaluar el modelo (20%).",',
    "                        )",
    "",
    '                    st.markdown("#### Matriz de Confusi\u00f3n")',
    '                    cm_data = resultado["confusion_matrix"]',
    "                    df_cm = pd.DataFrame(",
    "                        cm_data,",
    '                        index=["Real: No satisfecho (0)", "Real: Satisfecho (1)"],',
    '                        columns=["Pred: No satisfecho (0)", "Pred: Satisfecho (1)"],',
    "                    )",
    "                    st.dataframe(df_cm, use_container_width=True)",
    "                    st.markdown(",
    '                        \'<p style="color:#8B949E;font-size:0.8rem;margin-top:0.5rem;">\'',
    '                        "Diagonal principal = predicciones correctas. "',
    '                        "Fuera de la diagonal = errores del modelo.</p>",',
    "                        unsafe_allow_html=True,",
    "                    )",
    "",
    '                    with st.expander("\U0001f4c1 Archivos del modelo guardados"):',
    "                        st.code(",
    "                            f\"Modelo:    {resultado['model_path']}\\n\"",
    "                            f\"Escalador: {resultado['scaler_path']}\",",
    '                            language="bash",',
    "                        )",
    "",
    "                except ValueError as e:",
    "                    st.warning(f\"\u26a0\ufe0f {e}\")",
    "                except Exception as e:",
    "                    st.error(f\"\u274c Error durante el entrenamiento: {e}\")",
]

if target_idx is not None:
    lines[target_idx : target_idx + 1] = new_lines
    result = "\n".join(lines)
    open(path, "w", encoding="utf-8").write(result)
    print(f"Archivo reparado. Total líneas ahora: {len(lines)}")
else:
    print("ERROR: No se encontró la línea corrupta.")
