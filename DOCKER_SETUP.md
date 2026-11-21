# Docker – lokalne uruchomienie (Windows 11)

## 1. Jednorazowa instalacja
1. PowerShell **jako administrator**: `wsl --install` → restart komputera.
2. Docker Desktop: `winget install -e --id Docker.DockerDesktop` (albo instalator ze strony Dockera). Zaznacz „Use WSL 2 based engine”.
3. Uruchom Docker Desktop, poczekaj aż status = „Engine running”.
4. Test: `docker --version` oraz `docker run hello-world`.

## 2. Uruchomienie projektu (w folderze `hackhathon`)
1. Plik `.env` w katalogu głównym (jest w .gitignore) – wartości dla compose, m.in. `ADMIN_PASSWORD`.
   Brak `.env` = działa na domyślnych, konto admina: `admin` / `admin`.
2. `docker compose up -d --build`
3. Backend przy starcie sam wykonuje migracje bazy i tworzy konto admina (domyślnie `admin` / `admin`, nadpisz przez `ADMIN_LOGIN` / `ADMIN_PASSWORD`). Jeśli migracja się nie uda, backend nie wstanie – błąd w `docker compose logs backend`.
4. Dane demo (Pizzeria Amalfi): `docker compose exec backend python -m app.services.seed`.

## 3. Adresy
- Frontend: http://localhost:3000
- Backend / Swagger: http://localhost:8000/docs
- Postgres: localhost:5432 (cfo_user / cfo_password / cfo_db) – tylko lokalnie; na klaster nie kopiuj portu, hasła ani montowania kodu z compose.
- Model AI: `MODEL_ENDPOINT_URL` – lokalnie wymaga port-forwardu z OpenShift na port 8080.

## 4. Przydatne komendy
- Logi: `docker compose logs -f backend`
- Stop: `docker compose down` (dane zostają), reset bazy: `docker compose down -v`
- Backend ma hot-reload (zamontowany `./backend`); zmiany we frontendzie wymagają `docker compose up -d --build frontend`.

## 5. Typowe problemy
- Port 5432 zajęty (lokalny Postgres) → zmień w compose na `"5433:5432"`.
- „WSL 2 installation is incomplete” → `wsl --update`.
- Firmowy laptop: instalacja wymaga admina; Docker Desktop płatny dla dużych firm (alternatywa: Podman Desktop / Rancher Desktop).
