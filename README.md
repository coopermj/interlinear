# Interlinear Bible Generator

Generate beautifully typeset interlinear Bible PDFs with Greek text, English glosses, and multiple translations.

## Features

- **Greek Interlinear**: Greek text with context-sensitive English glosses above each word
- **Multiple Translations**: ESV, NET, and KJV side-by-side
- **Greek Lexicon**: Clickable glosses link to appendix with Strong's and Liddell & Scott definitions
- **Navigation**: Table of contents, chapter links, running headers
- **Optimized for E-readers**: Sized for Remarkable Paper Pro (179mm x 239mm)

## Layouts

| Layout | Description |
|--------|-------------|
| `esv-portrait` | Greek + ESV (2 columns, portrait) |
| `multi-landscape` | Greek + ESV + NET + KJV (4 columns, landscape) |

## Requirements

### Python
- Python 3.10+
- Dependencies: `pip install -r requirements.txt`

### System
- LuaLaTeX (via TeX Live or MacTeX)
- Fonts: Gentium Plus, Bembo Book MT Pro (or substitute)

### API Key
- ESV API key from [api.esv.org](https://api.esv.org/)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/coopermj/interlinear.git
   cd interlinear
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your ESV API key:
   ```bash
   cp config.py.example config.py
   # Edit config.py and add your API key
   ```

4. Download Greek text data (automatic on first run):
   ```bash
   python -m src.download_data
   ```

## Usage

```bash
# Single passage (ESV Portrait layout)
python generate.py "John 1:1-18"

# Full book
python generate.py "Ephesians"

# Multi-translation landscape layout
python generate.py "Romans" --layout multi-landscape

# Generate LaTeX only (no PDF compilation)
python generate.py "Galatians 5" --latex-only
```

### Options

| Option | Description |
|--------|-------------|
| `--layout` | Choose layout: `esv-portrait` (default) or `multi-landscape` |
| `--latex-only` | Generate .tex file without compiling to PDF |
| `--api-key` | Override ESV API key from config |
| `--keep-aux` | Keep LaTeX auxiliary files after compilation |

## Output

Generated files are saved to the `output/` directory:
- `{Passage}.tex` - LaTeX source
- `{Passage}.pdf` - Compiled PDF

## Data Sources

- **Greek Text**: [OpenGNT](https://github.com/eliranwong/OpenGNT) (CC BY-SA 4.0)
- **Strong's Dictionary**: [OpenScriptures](https://github.com/openscriptures/strongs)
- **Liddell & Scott**: [LSJ via Perseids Project](https://github.com/perseids-project/lsj-js) (Perseus Digital Library)
- **ESV**: [ESV API](https://api.esv.org/)
- **NET**: [NET Bible API](https://labs.bible.org/)
- **KJV**: [bible-api.com](https://bible-api.com/)

## Project Structure

```
interlinear/
├── generate.py              # Main CLI entry point
├── config.py                # ESV API key (gitignored)
├── requirements.txt
├── data/                    # Greek text and Strong's data
├── src/
│   ├── download_data.py     # Download OpenGNT
│   ├── parse_greek.py       # Parse Greek text with Strong's numbers
│   ├── fetch_esv.py         # ESV API client
│   ├── fetch_net.py         # NET API client
│   ├── fetch_bibleapi.py    # bible-api.com client (KJV)
│   ├── strongs_lookup.py    # Strong's and LSJ dictionary lookup
│   ├── generate_latex.py    # ESV Portrait LaTeX generation
│   ├── generate_multi_latex.py  # Multi Landscape LaTeX generation
│   └── build_pdf.py         # LuaLaTeX compilation
├── templates/
│   ├── esv_portrait/        # 2-column portrait templates
│   └── multi_landscape/     # 4-column landscape templates
└── output/                  # Generated .tex and .pdf files
```

## License

Code is provided as-is. Greek text from OpenGNT is CC BY-SA 4.0. Bible translations are subject to their respective licenses.
