# Misión Unattended — Fase B0 (iteración autónoma)

## Calibración B0-a: APROBADA
SRS-APR.md y SRS-MIT.md quedan aprobados tal como están en feature/phase-b0-srs.
Los 2 requisitos PROPOSED de FINDINGS se aceptan como cierre a nivel SRS.

## Modo de operación
Opero sin checkpoints humanos hasta terminar B0. En lugar de detenerme:
1. Ante ambigüedad: elijo la interpretación conservadora, marco PROPOSED,
   registro la decisión en DECISIONS.md y continúo.
2. Al terminar cada documento: commit individual + entrada en REVIEW_INDEX.md
   con lo que un revisor humano debe verificar.
3. Verificación manual de trazabilidad por documento (mismo protocolo que
   reports/feature-phase-b0-srs.md) hasta que exista tools/trace-check.

## Alcance de esta iteración (en orden)
1. srs/SRS-AGT.md — derivación completa desde SyRS-AGP-001_EN.md
2. srs/SRS-RET.md
3. srs/SRS-EVH.md
4. tools/trace-check/ — implementación mínima + correr contra los 5 SRS
5. Si queda ventana: re-verificar SRS-APR y SRS-MIT con trace-check,
   consolidar FINDINGS.md y DEFERRED.md

## Prohibido (fusibles duros)
- Merge o push a main. Todo vive en feature/phase-b0-srs.
- Modificar SyRS-AGP-001_EN.md o cualquier artefacto de Fase A.
- Borrar o reescribir requisitos ya aprobados (SRS-APR, SRS-MIT); solo additivo.
- push a remoto de cualquier tipo (trabajo local; el humano hace push al volver).

## Estado
El estado real es git + este archivo + REVIEW_INDEX.md. Cada corrida empieza
leyendo `git log --oneline -10` y REVIEW_INDEX.md para saber dónde retomar.
