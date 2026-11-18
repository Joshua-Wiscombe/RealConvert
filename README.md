# RealConvert

**Paste a link, get the file.** RealConvert is a free app that runs on your own computer and opens in
your browser. It downloads videos from YouTube, TikTok, Instagram, X (Twitter), Facebook, Vimeo,
Reddit, SoundCloud, Twitch and [1,000+ other sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md),
vertical or long-form, in their original quality, and saves them as the format you choose.

- **Video:** MP4, MOV, MKV, WEBM, at the best quality available (up to 4K/8K) or any lower quality
- **Audio:** MP3 (up to 320 kbps), WAV, M4A, FLAC, OPUS, or the original audio with no conversion
- **Trim:** save just part of a video (e.g. 1:30 to 2:05)
- **Batch:** paste several links, a playlist or a channel, and download them all at once
- **Posts with several videos** (like Instagram carousels) download every video
- **Private or members-only videos you can see in your browser:** use your browser's login (see below)
- No ads, no accounts, no upload limits. Nothing is sent anywhere except to the site you're downloading from.

It's built on [yt-dlp](https://github.com/yt-dlp/yt-dlp), the open-source downloader that keeps up
with site changes, and [ffmpeg](https://ffmpeg.org/) for converting. Both are installed for you.

---

## Start it

You need **Python 3.10 or newer** (free). The launcher offers to install it if it's missing.
The first start takes a minute or two while it sets things up. After that it starts in seconds.

### Windows
1. Download this project (green **Code** button → **Download ZIP**), then unzip it somewhere, such as your Documents folder.
2. Double-click **`RealConvert-Windows.bat`**.
   - If Windows shows "Windows protected your PC", click **More info → Run anyway**.
   - If you don't have Python, it offers to install it for you. Afterwards, double-click the file again.
     (If you install Python yourself from [python.org](https://www.python.org/downloads/), tick **"Add python.exe to PATH"**.)
3. Your browser opens RealConvert. Keep the black window open while you use it, and close it to quit.

### Mac
1. Download and unzip this project.
2. Double-click **`RealConvert-Mac.command`**.
   - If macOS says it can't be opened, **right-click → Open → Open**. You only need to do this once.
   - If it opens in a text editor instead, open **Terminal**, type `chmod +x ` (with a space), drag the
     file into the Terminal window, press Enter, then double-click it again.
   - No Python yet? Install it from [python.org](https://www.python.org/downloads/macos/) (or with Homebrew), then double-click again.
3. Your browser opens RealConvert. Keep the Terminal window open while you use it.

### Linux
```bash
./RealConvert-Linux.sh
```
(On Ubuntu/Debian you may first need `sudo apt install python3 python3-venv python3-tk`.)

**Tip:** bookmark `http://127.0.0.1:8765`. If RealConvert is already running, opening the launcher again just opens the page.

---

## Use it

1. Copy a video's link (Share → Copy link in most apps) and paste it into RealConvert.
   It starts reading the link as soon as you paste.
2. Pick **Video** or **Audio**, then a format and quality. "Best available" is the original quality.
3. Click **Download**. Files are saved to **Downloads/RealConvert** (change this in ⚙ Settings).
   Use the buttons next to each download to play it or show it in its folder.

### Which format should I pick?

| You want… | Pick |
|---|---|
| A video that plays on any phone, PC, TV or editor (CapCut, Premiere, iMovie…) | **MP4** (keep "Make it play everywhere" on) |
| Something for Final Cut / Apple apps | **MOV** |
| The exact original streams, with no conversion at all | **MKV** |
| Music or a podcast | **MP3** (320 kbps) |
| Audio for editing / a DAW | **WAV** (or **FLAC**, which is lossless and smaller) |

**About "Make it play everywhere (H.264)":** for 4K YouTube videos (and some TikToks) the best
version uses a newer codec (VP9/AV1/H.265) that some apps can't open. With this on, RealConvert
converts those to H.264 at the same resolution so they work everywhere. That takes extra time
for long 4K videos. Turn it off to keep the original stream as-is. Videos that are already H.264
(most TikTok, Instagram and ≤1080p YouTube videos) are never re-encoded.

---

## If something doesn't work

**"Sign in to confirm you're not a bot", private videos, age-restricted videos, Instagram asks you to log in**
Open ⚙ **Settings → Use cookies from** and pick the browser you're logged in with. RealConvert then
uses that login (read locally on your computer) to download videos you can see. On Windows, Chrome and
Edge lock their cookies while open, so **fully close them** first, or use **Firefox**, which works best.
You can also export a `cookies.txt` file with a browser extension and choose it in Settings.

**A link that used to work suddenly fails**
Sites change constantly. RealConvert checks for engine updates each time it starts (at most twice a day).
To update right away, click **Update engine** at the bottom of the page, then close and reopen RealConvert.

**YouTube gives low quality or errors**
Make sure the footer says **YouTube helper: deno**. If it doesn't, delete the `.venv` folder and start
RealConvert again to reinstall, or install [Deno](https://deno.com/) or [Node.js](https://nodejs.org/).

**Start over from scratch**
Close RealConvert, delete the `.venv` folder inside the RealConvert folder, and start it again.

---

## Extras

**Download to your phone:** start RealConvert with `--lan` (e.g. `python run.py --lan` from a terminal
in this folder). The window shows an address like `http://192.168.1.20:8765`. Open it on your phone
(same Wi-Fi) and finished downloads get a "Save to this device" button. Only use this on networks you trust.

**Other options:** `python run.py --port 9000` (different port) · `--no-browser` (don't open the browser) ·
`--no-update` (skip the update check).

## How it's put together

| File | What it does |
|---|---|
| `RealConvert-Windows.bat` / `-Mac.command` / `-Linux.sh` | Double-click launchers. They find Python and run `run.py` |
| `run.py` | Creates a private Python environment in `.venv`, installs/updates everything, starts the app |
| `app.py` | The local web server (only reachable from your own computer unless you use `--lan`) |
| `engine.py` | Downloading (yt-dlp), converting (ffmpeg), progress, file naming |
| `static/` | The web page you see |

Settings are saved in `settings.json`. Everything RealConvert installs lives in the `.venv` folder,
so deleting the RealConvert folder removes it completely.

## Fair use

RealConvert is meant for personal use: saving your own videos, or content you have permission to
download. Respect creators and each site's terms of service.
