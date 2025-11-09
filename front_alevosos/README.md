# Alevosos Front (Vite + React + Tailwind)

Frontend mínimo para la API de Alevosos Studio (FastAPI). Incluye **Login**, **Clientes**, **Ventas** y **Reportes**.

## Requisitos
- Node.js 18+ y npm

## Configuración
```bash
npm install
cp .env.example .env        # (opcional) ajustar VITE_API_URL
npm run dev
```
Abrí: http://localhost:5173

> Asegurate de tener la API levantada en `http://localhost:8000` y haber corrido el seeder (`python -m app.initial_data`).

## Build
```bash
npm run build
npm run preview
```

## Notas
- Las credenciales por defecto: `admin@alevosos.local` / `admin123`
- Cambiá `VITE_API_URL` en `.env` si tu backend corre en otra URL.
