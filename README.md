# Quran Trainer — Image-Based Mushaf (Pre-Rendered Pages)

## The Architecture

This is the **ultimate** approach for exact Mushaf appearance + zero client weight:

```
Your Server / CDN                          Mobile User
├─ 604 PNG/WebP images (~30MB total)  ──>  ├─ 34KB HTML viewer
├─ Python backend (Whisper ASR)       ──>  ├─ Sends 50-200KB audio clips
└─ Image generator script                    ├─ Caches pages forever
                                             └─ Works fully offline after first visit
```

**The mobile never processes text, fonts, or AI. It just displays images.**

---

## Files in this Package

| File | Size | Purpose |
|------|------|---------|
| `quran_mushaf_viewer.html` | **34 KB** | Frontend app — open this in any browser |
| `server.py` | **7 KB** | Backend API — runs on your server/VPS |
| `generate_mushaf_pages.py` | **12 KB** | Generates the 604 Mushaf page images |
| `requirements.txt` | — | Python dependencies |

---

## How It Works

### 1. Generate 604 Page Images (One-time, on your server)

```bash
# 1. Install dependencies
pip install Pillow requests

# 2. Download the exact Mushaf font
wget https://cdn.jsdelivr.net/npm/kfgqpc-uthmanic-hafs@1.0.0/UthmanicHafs1Ver18.ttf

# 3. Download Quran text
wget https://tanzil.net/res/text/uthmani/quran-uthmani.txt

# 4. Generate pages
python generate_mushaf_pages.py
# Output: mushaf_pages/page_001.png ... page_604.png
```

**For production-quality exact pages**, download the exact page boundaries from Tanzil:
```bash
wget https://tanzil.net/res/text/metadata/page-boundaries.xml
```

This XML tells you precisely which ayah starts each of the 604 pages. Modify `generate_mushaf_pages.py` to use these exact boundaries instead of the demo placeholder logic.

### 2. Host Images on CDN

Upload the 604 images to any static host:
- **Cloudflare R2** (free, 10GB)
- **AWS S3 + CloudFront**
- **Your own VPS** with nginx
- **GitHub Pages** (if <1GB)

Get a base URL like: `https://your-cdn.com/mushaf/`

### 3. Run the Backend

```bash
pip install -r requirements.txt
python server.py
# Runs on http://0.0.0.0:8000
```

### 4. Users Open the Viewer

1. Open `quran_mushaf_viewer.html` on their phone
2. Tap **⚙ Settings** → enter:
   - **Backend URL**: `http://YOUR_SERVER:8000`
   - **Image CDN URL**: `https://your-cdn.com/mushaf/`
3. Browse exact Mushaf pages, swipe to navigate
4. Tap **🎯 آية** → select an ayah → tap **🎙 سجّل** → recite → get accuracy score

---

## Viewer Features

| Feature | How it works |
|---------|-------------|
| **Exact Mushaf pages** | Pre-rendered PNGs — pixel perfect, no font issues |
| **604-page navigation** | Swipe left/right, keyboard arrows, or index jump |
| **Smart caching** | Pages download once, stored in browser Cache API forever |
| **Offline mode** | After viewing a page once, it works without internet |
| **Surah index** | Tap ☰ to jump to any Surah instantly |
| **Juz index** | Tap 📑 to jump to any of the 30 Ajzaa |
| **Memorization cover** | Tap 👁 to cover the page and test yourself from memory |
| **Ayah selection** | Tap 🎯 to see all ayahs on current page, pick one to evaluate |
| **Audio recording** | Tap 🎙 to record recitation, sent to backend for Whisper analysis |
| **Word-level results** | Green (correct) / Red (wrong) / Yellow (extra) highlighting |
| **Zoom** | Double-tap to zoom, +/- buttons in settings |
| **Lite mode fallback** | If no image CDN configured, shows authentic demo SVG pages |

---

## Image Specifications

| Property | Value |
|----------|-------|
| Format | PNG or WebP |
| Dimensions | 800×1200 px (2:3 ratio) |
| File size | 30-80 KB per page (WebP) |
| Total for 604 pages | ~20-40 MB |
| Font | KFGQPC Uthmanic Hafs v18 |
| Lines per page | 15 (matching Madinah Mushaf) |
| Color | Cream paper #f5f0e1, black text |

---

## Why This Beats Text-Based Rendering

| | Text-Based (CSS/Font) | Image-Based (Pre-Rendered) |
|---|---|---|
| **Exact appearance** | ❌ Font rendering varies by device | ✅ Pixel-identical on all devices |
| **Line breaks** | ❌ Browser decides, often wrong | ✅ Exact Mushaf line breaks |
| **Tashkeel position** | ❌ Slightly off on some devices | ✅ Exact as printed |
| **Client download** | ❌ Must download font (~120KB) | ✅ No font needed |
| **Client processing** | ❌ Browser renders text + layout | ✅ Just display an image |
| **Offline after cache** | ✅ Works | ✅ Works (images cached) |
| **File size per page** | ~3KB text + processing | ~40KB image |
| **Searchability** | ✅ Text is selectable | ❌ Requires OCR layer (can be added) |
| **Zoom quality** | ✅ Infinite | ⚠️ Slight pixelation at 3x+ |

**The image approach wins on accuracy, consistency, and simplicity.**

---

## Adding Interactivity Over Images

Since images are static, how do we add word-level blanking or tapping?

### Option A: Text Overlay (Recommended)
- Server also generates a JSON file per page with word bounding boxes
- Client loads image + invisible HTML divs positioned over each word
- Memorization modes toggle div visibility
- **Best of both worlds**: exact visual + full interactivity

### Option B: OCR + Dynamic Overlay
- Run OCR on generated images to detect word positions
- Auto-generate bounding box JSON
- More work, but fully automated

### Option C: Simpler Cover Modes (Current implementation)
- **Full page cover**: Black overlay hides entire page
- **Ayah-based evaluation**: User selects ayah from list, records audio, gets result
- No need for word coordinates — sufficient for memorization training

---

## Deployment Checklist

- [ ] Generate 604 page images using `generate_mushaf_pages.py`
- [ ] Upload images to CDN with CORS headers
- [ ] Deploy `server.py` on VPS with `WHISPER_MODEL=base`
- [ ] Configure frontend Settings with Backend URL + Image CDN URL
- [ ] Test recording + evaluation on mobile
- [ ] Enable HTTPS (Cloudflare Tunnel or nginx + Let's Encrypt)

---

## Cost Estimate

| Component | Monthly Cost |
|-----------|-------------|
| VPS (2GB RAM, Hetzner/DigitalOcean) | $3-5 |
| CDN/Storage (Cloudflare R2, 40GB) | $0 (free tier) |
| Domain (optional) | $10/year |
| **Total** | **~$5/month** |

---

## Next Enhancements

1. **Tajweed color images**: Generate separate set with tajweed rules colored (red, blue, green)
2. **Audio overlay**: Show waveform or tajweed markers synchronized with sheikh recitation MP3
3. **Page coordinates JSON**: Add invisible word boxes for tap-to-reveal memorization
4. **Multi-font support**: Generate Warsh, Qaloon, and other riwayah variants
5. **Print-quality PDF**: Bundle 604 pages into single PDF for physical printing
