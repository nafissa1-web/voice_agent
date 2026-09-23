# 🎙️ Voice-to-Insight AI Agent

A fully local voice agent: record your voice → transcribe with **Whisper** →
extract intent/priority/platform with a local LLM (**Ollama + Qwen**) → save
it as a **mission** you can browse, mark done, or delete → optionally push
it straight into a **Notion** database.

Built on top of the original single-file prototype, split into a small,
readable pipeline: `core/transcribe.py` → `core/analyze.py` →
`core/storage.py` → `core/notion_sync.py`, orchestrated by `app.py`.

## What changed from the original prototype

- Fixed a bug where `response.choices.message.content` was used instead of
  `response.choices[0].message.content` (would crash on every real call).
- The AI's JSON output is now validated/normalized, so a malformed response
  from the model can never crash the UI.
- Added a **mission log** (`missions.json`) so every recorded task/idea is
  saved locally and browsable in the sidebar — sorted by priority, filterable
  by type, with done/delete controls. This is what lets you "come back and
  see your missions easily."
- Added a real **Notion integration**: push any mission to a Notion database
  with one click, or auto-sync every new task as you record it.
- Split the single 100-line script into small modules so it reads well in a
  portfolio/GitHub repo.

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run a local model with Ollama

```bash
ollama pull qwen2.5:0.5b
ollama serve
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Leave `NOTION_TOKEN` / `NOTION_DATABASE_ID` blank if you just want the local
pipeline — Notion sync will simply be disabled in the sidebar.

### 4. (Optional) Connect Notion

1. Create an integration at <https://www.notion.so/my-integrations> and copy
   its **Internal Integration Secret** → `NOTION_TOKEN`.
2. Create a Notion database (table) with these properties:

   | Property | Type     | Options                                |
   |----------|----------|-----------------------------------------|
   | Name     | Title    | —                                        |
   | Priority | Select   | High, Medium, Low                        |
   | Intent   | Select   | task, content_creation, summary          |
   | Platform | Select   | Notion, Instagram, Trello                |
   | Status   | Checkbox | —                                        |
   | Details  | Text     | —                                        |

3. Open the database → `···` → **Connections** → add your integration.
4. Copy the database ID out of its URL
   (`notion.so/yourspace/<DATABASE_ID>?v=...`) → `NOTION_DATABASE_ID`.

### 5. Run the app

```bash
streamlit run app.py
```

## How it works

1. `mic_recorder` captures audio in the browser.
2. `core/transcribe.py` loads Whisper once (`st.cache_resource`) and
   transcribes the recording to text.
3. `core/analyze.py` sends the text to a local Qwen model via Ollama's
   OpenAI-compatible API and gets back structured JSON
   (`intent`, `title`, `priority`, `action_platform`, `summary_or_caption`).
4. `core/storage.py` saves the result as a "mission" in `missions.json`.
5. The sidebar renders every mission, sorted by priority, so you always know
   what's outstanding.
6. `core/notion_sync.py` can push any mission into your Notion database,
   either manually (per-mission button) or automatically on every recording.

## Ideas for extending this further (nice for a portfolio write-up)

- Swap `missions.json` for SQLite so it scales past a few hundred entries.
- Add authentication if you deploy it beyond your own machine.
- Use a bigger Whisper model (`base`/`small`) for noisier audio.
- Add a "weekly digest" that summarizes all missions from the past 7 days.
- Two-way sync: pull "done" checkbox changes back from Notion.
