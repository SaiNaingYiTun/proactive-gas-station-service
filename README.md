# RCVCI: Restricted Camera View Car Identification

Senior project, Vincent Mary School of Engineering, Science and Technology, Assumption University.

RCVCI watches a single fixed camera with a limited view of a lane and turns each passing car into a record: Thai licence plate, colour, brand, entry time and exit time. Staff then see and correct those records in a web dashboard.

The project began as a gas-station service (hence the repository name, `proactive-gas-station-service`). Testing at the station proved impractical, so with our advisor's agreement we retitled it to focus on car identification from a restricted camera view.

## How it works

```
IP camera (RTSP) ──► AI module (edge PC, GPU) ──HTTPS events──► FastAPI backend ──► Supabase (PostgreSQL)
                                                                      ▲
                                        React dashboard (browser) ────┘  REST + JWT
```

- **AI module** (`ai-module/`) detects and tracks cars, reads the plate, and classifies colour and brand. It votes across several frames before trusting a result, then sends entry, update and exit events to the backend.
- **Backend** (`backend/`) stores visits, pairs each exit with its entry, flags uncertain matches for review, and serves the dashboard API. Every event carries a UUID, so a retried request never creates a duplicate.
- **Frontend** (`frontend/`) is the staff dashboard: Overview, Vehicles (search and correct records), Analytics, Settings, and Staff Management (owner only).

### Models

| File | Task | Classes |
| --- | --- | --- |
| `yolov8n.pt` | Vehicle detection + ByteTrack tracking | car, truck, bus (COCO) |
| `best.pt` | Licence plate detection | 1 |
| `character.pt` | Thai plate characters and province | 125 (digits, consonants, 77 provinces) |
| `color.pt` | Vehicle colour | 15 |
| `brand.pt` | Vehicle brand | 11 makes |

Model weights are **not stored in Git**. Get them from the team's shared storage and place them in `ai-module/`.

## Repository layout

```
ai-module/
  app.py                  Desktop operator app (Tkinter): start/stop, stream link, save crops
  main.py                 Detection pipeline: main loop + OCR, attribute and backend worker threads
  config.py               All thresholds, regions of interest and model paths
  detector.py             Plate detector
  vehicle_detector.py     Vehicle detector and tracker
  thai_plate_recognizer.py  Thai character model reader
  color_classification.py   Colour classifier with HSV fallback
  make_model_classifier.py  Brand classifier
  stabilizer.py, make_model_stabilizer.py  Multi-frame voting
  train_brand.py, split_brand_val.py, eval_brand_own_crops.py  Brand model training tools
  brand_dataset/          Folder structure for brand training data (images are not committed)
  Start Live Detection.bat  Launches the desktop app
backend/
  main.py                 FastAPI app (all endpoints)
  auth.py                 bcrypt password hashing and JWT sessions
  create_owner_account.py Creates the first owner login
  migrations/             SQL migrations
frontend/
  src/pages/              Dashboard pages
  src/lib/                API client, auth and helpers
vercel.json               Deploys frontend and backend together; /api/* goes to the backend
```

## Setup

### Requirements

- Python 3.11
- Node.js 20 or later
- An NVIDIA GPU with CUDA for live detection (CPU works, but too slowly for live video)
- A Supabase project

### 1. Database (Supabase)

Create the two core tables, then run the files in `backend/migrations/` in order.

```sql
CREATE TABLE vehicle_visits (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plate_number text,
    vehicle_type text,
    vehicle_color text DEFAULT 'unknown',
    entry_time timestamptz,
    exit_time timestamptz,
    visit_status text,
    created_at timestamptz DEFAULT now()
);

CREATE TABLE detection_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    visit_id bigint REFERENCES vehicle_visits(id),
    camera_id integer,
    event_type text,
    confidence double precision,
    vehicle_color text,
    source_event_id uuid,
    created_at timestamptz DEFAULT now()
);
```

The migrations add `vehicle_make` and `match_status` to `vehicle_visits` and create `staff_accounts`.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows; use source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service role key>
JWT_SECRET=<random string>
```

Generate a secret with `python -c "import secrets; print(secrets.token_hex(32))"`.

Create the first owner account, then start the API:

```bash
python create_owner_account.py
uvicorn main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Check it with `http://localhost:8000/api/health`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

In development the dashboard calls `http://localhost:8000`. To point it elsewhere, set `VITE_API_BASE` in `frontend/.env`. In a production build it calls `/api` on its own domain.

### 4. AI module

```bash
cd ai-module
python -m venv .venv
.venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu126
pip install ultralytics opencv-python easyocr requests pillow numpy
```

Copy the model weights into `ai-module/`, then start the desktop app:

```bash
python app.py
```

On Windows you can also double-click `Start Live Detection.bat`.

In the app:

1. Enter the camera's RTSP link, or click **Browse video...** to run on a recorded file.
2. Set **Backend** to your API address. The dot turns green when the backend is reachable.
3. Tick **Save events to backend** to record visits. Tick **Save crops** to keep plate and car images for training.
4. Click **Start**.

To run without the desktop app, use `python main.py`. It reads the stream from the `CAMERA_RTSP_URL` environment variable and sends events to `API_BASE` in `config.py`.

## Configuration

Everything the AI module depends on lives in `ai-module/config.py`:

- **Regions of interest:** `DETECTION_ROI`, `VEHICLE_ENTRY_ROI`, `EXIT_TRACK_ROI`, `EXIT_ARM_Y` and `EXIT_CROSS_Y` are pixel coordinates in the 1500 x 890 processing frame. Redraw them whenever the camera moves.
- **Confidence thresholds:** for example `CONF_THRESHOLD` (plates), `COLOR_MODEL_MIN_CONF` and `MAKE_MODEL_MIN_CONF`.
- **Feature switches:** brand recognition is off unless the `ENABLE_MAKE_MODEL` environment variable is set.

Debug output is enabled through environment variables such as `DEBUG_OCR`, `DEBUG_COLOR`, `DEBUG_THAI_PLATE` and `DEBUG_MAKE_MODEL`.

## Training the brand model

1. Run live detection with brand recognition and crop saving on, or collect car images some other way.
2. Sort images into `ai-module/brand_dataset/train/<Make>/`.
3. Move 20% of each make into the validation set: `python split_brand_val.py --apply`.
4. Train: `python train_brand.py`. Results go to `runs/brand_finetune/`.
5. Check accuracy on your own crops: `python eval_brand_own_crops.py runs/brand_finetune/station_makes/weights/best.pt`.
6. Copy the new `best.pt` over `ai-module/brand.pt`.

## Deployment

`vercel.json` deploys the frontend and backend as two Vercel services on one domain, routing `/api/*` to the backend. Set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` and `JWT_SECRET` as environment variables in the Vercel project. The AI module always runs on a local PC next to the camera.

## API overview

| Method | Path | Used by | Auth |
| --- | --- | --- | --- |
| POST | `/api/detection` | AI module: new entry | none |
| PATCH | `/api/entry/{event_id}` | AI module: late colour or brand | none |
| PUT | `/api/exit` | AI module: exit | none |
| GET | `/api/health` | dashboard, desktop app | none |
| POST | `/api/auth/login` | dashboard | none |
| GET | `/api/auth/me` | dashboard | staff |
| POST | `/api/auth/change-password` | dashboard | staff |
| GET, POST | `/api/auth/staff` | dashboard | owner |
| PATCH | `/api/auth/staff/{id}` | dashboard | owner |
| GET | `/api/visits` | dashboard | staff |
| PATCH | `/api/visits/{id}` | dashboard: correct a record | staff |
| GET | `/api/visits/{id}/events` | dashboard | staff |
| GET | `/api/analytics/summary?days=30` | dashboard | staff |

## Known limitations

- Plates that are small or at a steep angle in the camera view are often not read; those cars are still recorded with colour, brand and times.
- The three AI endpoints have no authentication yet.
- Visits with an exit but no entry are not counted in the Analytics "Needs Review" figure.
- Events are lost if the AI PC has no internet connection while running.

## Privacy

Camera links, plate images, training datasets and model weights are kept out of Git (see `.gitignore`). Licence plates are personal data under Thailand's PDPA, so only run this system where people are told that cameras are recording.

## Team

- Sai Naing Yi Tun
- [Team member]
- [Team member]

Advisor: [Advisor name]
