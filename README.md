# 🏠 BAÑO DOMÓTICO

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=rect&color=FCEE0A&height=3" width="100%">
</p>

<p align="center">
  <b>SISTEMA DOMÓTICO PARA LA AUTOMATIZACIÓN DE UN BAÑO</b>
</p>

<p align="center">
  <code>Python</code> &nbsp;•&nbsp;
  <code>Arduino</code> &nbsp;•&nbsp;
  <code>Automatización</code> &nbsp;•&nbsp;
  <code>Domótica</code>
</p>

---

## 🧠 Descripción

El **Baño Domótico** es un proyecto de automatización desarrollado para integrar diferentes funciones de un baño mediante el uso de **Arduino y Python**.

El sistema busca automatizar diferentes procesos y facilitar la interacción del usuario con los elementos del baño, integrando sensores, actuadores y programación.

Este proyecto fue desarrollado como parte de la formación en **Ingeniería Mecatrónica**.

---

## 🎯 Objetivo

Diseñar e implementar un sistema domótico capaz de automatizar diferentes funciones de un baño mediante la integración de:

- 🔌 Electrónica
- 🤖 Automatización
- 💻 Programación
- 📡 Sensores
- ⚙️ Actuadores
- 🖥️ Interfaz desarrollada en Python

---

## ⚙️ Funcionamiento

El sistema utiliza **Arduino** para controlar e interactuar con los diferentes componentes electrónicos.

Por otro lado, **Python** permite desarrollar la comunicación y/o interfaz utilizada para interactuar con el sistema.

La integración entre ambos permite controlar y monitorear las diferentes funciones automatizadas del baño.

---

## 🧩 Componentes

### 🔧 Hardware

- Arduino
- Sensores
- Actuadores
- LEDs
- Motores
- Pulsadores
- Componentes electrónicos

> Los componentes específicos pueden variar dependiendo de la implementación final del proyecto.

### 💻 Software

- Python
- Arduino IDE
- C/C++
- Comunicación serial

---

## 🖥️ Tecnologías

<p align="center">

<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg" width="60" height="60" alt="Python"/>

<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/arduino/arduino-original.svg" width="60" height="60" alt="Arduino"/>

<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/c/c-original.svg" width="60" height="60" alt="C"/>

</p>

<p align="center">

`Python` &nbsp;&nbsp;
`Arduino` &nbsp;&nbsp;
`C/C++` &nbsp;&nbsp;
`Comunicación Serial` &nbsp;&nbsp;
`Domótica` &nbsp;&nbsp;
`Automatización`

</p>

---

## 🔌 Arquitectura del sistema

```text
                    ┌─────────────────────┐
                    │       USUARIO       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       PYTHON        │
                    │ Interfaz / Control  │
                    └──────────┬──────────┘
                               │
                         Comunicación
                           Serial
                               │
                               ▼
                    ┌─────────────────────┐
                    │      ARDUINO        │
                    │ Control del sistema │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
           ┌─────────┐   ┌─────────┐   ┌─────────┐
           │Sensores │   │Actuadores│  │  LEDs   │
           └─────────┘   └─────────┘   └─────────┘
