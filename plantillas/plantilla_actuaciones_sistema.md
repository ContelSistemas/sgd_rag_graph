---
id: hotel_corales_villa_switches_ejemplo
title: Hotel Corales Villa - Switches (Ejemplo)
cliente: Hotel Corales Villa
sistema: switches
categoria: infraestructura_red
criticidad: alta
autor: Departamento TI
tags:
  - "#HOTEL_CORALES_VILLA"
  - "#switch"
  - "#red"
  - "#vlan"
  - "#dante"
link_to: "[[hotel_corales_villa]]"
fecha_actualizacion: 2026-11-04
---

# hotel_corales_villa_switches

## Índice de actuaciones

| Fecha      | Tipo          | Resumen                                          | Intervinientes  |
| ---------- | ------------- | ------------------------------------------------ | --------------- |
| 2024-10-16 | Incidencia    | Configuración puerto PC monitorización Red Dante | Emilio, Roberto |
| 2024-10-20 | Mantenimiento | Cambio de VLAN en switch HCY-SW03-CPD            | Roberto         |
| 2024-10-25 | Incidencia    | Fallo puerto XGE1/0/25 tras tormenta eléctrica   | Ana, Luis       |

---

## 2024-10-16 - Configuración PC monitorización Red Dante

### Tipo
Incidencia

### Sistema afectado
Switches / Red Dante

### Intervinientes
Emilio, Roberto

### Descripción / Acciones realizadas
Se habilitó la interfaz eth16 del switch HCY-SW03-CPD en modo acceso de la VLAN 1820 para conectar el PC de monitorización (alojará Dante Controller y Ecler Management). Se configuró reserva DHCP en Mikrotik para asignar la IP 172.16.97.29 a la interfaz de red (adaptador USB) del PC.

### Resolución
Los cambios a nivel de red (asignación de VLAN en el switch y reserva de IP en el Mikrotik) se aplicaron de forma exitosa. Se realizaron comprobaciones junto a Roberto, confirmando que la conexión es estable y que los trabajos se encuentran en correcto funcionamiento operativo.

### Enlaces relacionados
[[hotel_corales_villa]]

---

## 2024-10-20 - Cambio de VLAN en switch HCY-SW03-CPD

### Tipo
Mantenimiento

### Sistema afectado
Switches

### Intervinientes
Roberto

### Descripción / Acciones realizadas
Se modificó la VLAN del puerto XGE1/0/25 del switch HCY-SW03-CPD de la VLAN 100 a la VLAN 200 para separar el tráfico de gestión del tráfico de usuarios.

### Resolución
Cambio aplicado y verificado. Ping exitoso desde la nueva VLAN 200. Sin interrupciones de servicio reportadas.

### Enlaces relacionados
[[hotel_corales_villa]]

---

## 2024-10-25 - Fallo puerto XGE1/0/25 tras tormenta eléctrica

### Tipo
Incidencia

### Sistema afectado
Switches

### Intervinientes
Ana, Luis

### Descripción / Acciones relacionadas
Tras tormenta eléctrica, el puerto XGE1/0/25 del switch HCY-SW03-CPD dejó de responder. Se descartó fallo de cableado y se procedió a reiniciar la interfaz. Se sustituyó el transceptor SFP por unidad de repuesto.

### Resolución
Puerto restaurado tras reemplazo del SFP. Se dejó el transceptor dañado para análisis técnico externo. Servicio restablecido a las 11:30 AM.

### Enlaces relacionados
[[hotel_corales_villa]]
