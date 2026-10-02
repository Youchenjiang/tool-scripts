# Slide Deck Auditor

`slide-deck-auditor` is a zero-dependency static analysis and quality assurance tool designed for modern slide presentations, handouts, and UI component decks (React/TSX/JSX, Vue, Svelte, HTML/CSS).

It automatically flags **Dead Space Voids**, **Elevator Shaft Traps**, **Letterboxing Image Voids**, **Semantic Color Inversions**, and **AI Marketing Fluff**.

---

## ✨ Core Audit Engines

| Rule ID | Severity | Description |
| :--- | :---: | :--- |
| `elevator_shaft` | **ERROR** | **Elevator Shaft Trap**: Flags vertical flexbox containers (`column` / `flex-col`) combined with `space-between`. When content is sparse, this pushes headers to the top and footers to the bottom, creating a massive (>40%) hollow void in the middle. |
| `letterboxing_void` | **ERROR** | **Letterboxing Screenshot Void**: Flags image containers configured with a pitch-black background (`#000`, `bg-black`) and `objectFit: 'contain'`. When non-16:9 images (e.g. 2.32:1 ultrawide lab captures) are placed inside tall boxes, this creates jarring 300px+ black dead zones. |
| `semantic_color_inversion` | **ERROR** | **Semantic Color Inversion**: Flags defense, patch, mitigation, or hardening sections styled with threat/danger red accents (`c.accent`, `red`), violating cybersecurity visual hierarchy where defense must be green. |
| `ai_fluff` | **WARN** | **AI Buzzword / Fluff Detector**: Filters out dramatic metaphors, empty hype, and overused AI marketing cliches ("驚人心智模型", "科學驗證法則", "震撼發現", "Game Changer") to enforce professional engineering instructor voice. |
| `typography_floor` | **WARN** | **Typography Floor Guard**: Ensures fonts meet 1080p full-bleed projection readability standards (titles ≥ 32px, body ≥ 22px). |

---

## 🚀 Quick Start

### Requirements
- Python 3.8+ (**Zero external dependencies**, uses Python standard library only)

### Usage

```bash
# Scan current directory
python slide_deck_auditor.py

# Scan specific directories or files
python slide_deck_auditor.py path/to/slides/

# Output as GitHub Actions workflow annotations
python slide_deck_auditor.py path/to/slides/ --format github

# Output as structured JSON for CI pipelines
python slide_deck_auditor.py path/to/slides/ --format json

# Fail on any warning (strict mode)
python slide_deck_auditor.py path/to/slides/ --fail-on warn
```

---

## ⚙️ Custom Configuration (`rules.json`)

You can provide a custom configuration file:

```json
{
  "rules": {
    "elevator_shaft": { "enabled": true, "severity": "ERROR" },
    "letterboxing_void": { "enabled": true, "severity": "ERROR" },
    "semantic_color_inversion": { "enabled": true, "severity": "ERROR" },
    "ai_fluff": { "enabled": true, "severity": "WARN" },
    "typography_floor": { "enabled": true, "severity": "WARN" }
  },
  "ai_fluff_keywords": [
    "Mind Blowing",
    "Game Changer"
  ]
}
```

Run with custom config:
```bash
python slide_deck_auditor.py -c my-rules.json src/
```

---

## 🛡️ Inline Suppression

Suppress specific checks for legitimate edge cases using inline comments:

```tsx
// slide-audit-ignore: elevator_shaft
<div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
  ...
</div>

// slide-audit-ignore: all
```

---

## 🧪 Unit Tests

Run the built-in test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```
