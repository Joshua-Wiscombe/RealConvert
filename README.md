# RealConvert

**Paste a link, get the file.** RealConvert is a free desktop app: it runs on your own computer,
opens in its own window from an icon on your desktop, and needs no account. It downloads videos from YouTube, TikTok, Instagram, X (Twitter), Facebook, Vimeo,
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

You need **Python 3.10 or newer** (free). The start file offers to install it if it's missing.

**The first time only**, open the start file for your computer (below). It spends a minute or two
setting up, then adds a **RealConvert icon** and opens the app. **From then on, just open
RealConvert from that icon** like any other app.

### Windows
1. Download this project (green **Code** button → **Download ZIP**). Right-click the ZIP and choose
   **Extract All…**, then **Extract**. Put the folder somewhere it can stay, such as your Documents folder.
2. Open the folder and double-click **`RealConvert-Windows.bat`**.
   - If Windows shows "Windows protected your PC", click **More info → Run anyway**.
   - If you don't have Python, it offers to install it for you. Afterwards, double-click the file again.
     (If you install Python yourself from [python.org](https://www.python.org/downloads/), tick **"Add python.exe to PATH"**.)
3. A black window shows the setup, then closes by itself, and RealConvert opens in its own window.
4. **Next time:** use the **RealConvert** icon on your desktop or in the Start menu.
   (You can right-click it in the Start menu to **Pin to taskbar**.)

### Mac
1. Download and unzip this project. Move the folder somewhere it can stay, such as your Documents folder.
2. Right-click **`RealConvert-Mac.command`** and choose **Open**, then **Open** again.
   - If it opens in a text editor instead, open **Terminal**, type `chmod +x ` (with a space), drag the
     file into the Terminal window, press Enter, then try again.
   - No Python yet? Install it from [python.org](https://www.python.org/downloads/macos/) (or with Homebrew), then try again.
3. After setup, RealConvert opens in its own window and you can close the Terminal window.
4. **Next time:** open **RealConvert** from Launchpad, Spotlight or your Applications folder. You can
   drag it to your Dock.

On a Mac, RealConvert opens in its own window if you have Chrome, Edge or Brave installed.
With only Safari, it opens as a Safari tab instead. It works the same either way.

### Linux
```bash
./RealConvert-Linux.sh
```
This adds RealConvert to your applications menu. (On Ubuntu/Debian you may first need
`sudo apt install python3 python3-venv python3-tk`.)

**Closing the RealConvert window quits the app.** If a download is still running, it finishes first.
**Don't move or delete the RealConvert folder** after setup, because the icon runs the app from there.
If you do move it, open the start file again, then run `python run.py --make-shortcuts` from that
folder to point the icon at the new place.

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

**RealConvert doesn't open from its icon**
Open the start file (`RealConvert-Windows.bat` / `RealConvert-Mac.command`) instead. It shows what's
happening. There's also a log file, `realconvert.log`, in the RealConvert folder.

**The icon is missing**
Run `python run.py --make-shortcuts` from a terminal in the RealConvert folder.

**Start over from scratch**
Close RealConvert, delete the `.venv` folder inside the RealConvert folder, and open the start file again.

---

## Extras

**Download to your phone:** start RealConvert with `--lan` (e.g. `python run.py --lan` from a terminal
in this folder). This runs it inside the terminal instead of its own window. The window shows an address like `http://192.168.1.20:8765`. Open it on your phone
(same Wi-Fi) and finished downloads get a "Save to this device" button. Only use this on networks you trust.

**Other options:** `python run.py --console` (run inside the terminal with a browser tab) ·
`--port 9000` (different port) · `--no-update` (skip the update check) · `--make-shortcuts` (add the icon again).

## How it's put together

| File | What it does |
|---|---|
| `RealConvert-Windows.bat` / `-Mac.command` / `-Linux.sh` | First-time start files. They find Python and run `run.py` |
| `run.py` | Creates a private Python environment in `.venv`, installs/updates everything, starts the app |
| `desktop.py` | The app window, the desktop/Start menu/Applications icon, and error pop-ups |
| `app.py` | The local web server (only reachable from your own computer unless you use `--lan`) |
| `engine.py` | Downloading (yt-dlp), converting (ffmpeg), progress, file naming |
| `static/` | The web page you see |

Settings are saved in `settings.json`. Everything RealConvert installs lives in the `.venv` folder.
To remove RealConvert completely, delete its folder and its icon (desktop + Start menu on Windows,
`RealConvert.app` in Applications on a Mac).

## Fair use

RealConvert is meant for personal use: saving your own videos, or content you have permission to
download. Respect creators and each site's terms of service.
