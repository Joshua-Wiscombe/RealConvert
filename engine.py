"""RealConvert engine: turns a link into a file on disk.

yt-dlp does the downloading (it supports YouTube, TikTok, Instagram, X,
Facebook, Vimeo, Reddit, SoundCloud and well over a thousand other sites)
and ffmpeg does the merging and converting.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import threading
import time
import urllib.parse
import urllib.request
import uuid
from collections import OrderedDict
from pathlib import Path

import yt_dlp
from yt_dlp.utils import download_range_func, parse_duration

APP_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = APP_DIR / 'settings.json'
TEMP_DIRNAME = '.realconvert-temp'

VIDEO_FORMATS = ('mp4', 'mov', 'mkv', 'webm')
AUDIO_FORMATS = ('mp3', 'wav', 'm4a', 'flac', 'opus', 'original')
AUDIO_BITRATES = ('320', '256', '192', '128')
COOKIE_BROWSERS = ('chrome', 'edge', 'firefox', 'brave', 'opera', 'vivaldi', 'chromium', 'safari')

NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')
MEDIA_JUNK_SUFFIXES = {
    '.part', '.ytdl', '.json', '.jpg', '.jpeg', '.png', '.webp', '.vtt', '.srt',
    '.ass', '.lrc', '.temp', '.tmp', '.description', '.url',
}


def log(msg: str) -> None:
    stamp = time.strftime('%H:%M:%S')
    try:
        print(f'[{stamp}] {msg}', flush=True)
    except Exception:
        pass


# --------------------------------------------------------------------------
# Tools: ffmpeg and a JavaScript runtime (YouTube needs one these days)
# --------------------------------------------------------------------------

def _which(name: str) -> str | None:
    """Find a program on PATH, or in this Python's Scripts/bin folder."""
    return shutil.which(name) or shutil.which(name, path=sysconfig.get_path('scripts'))


def find_ffmpeg() -> str | None:
    override = os.environ.get('REALCONVERT_FFMPEG')
    if override and Path(override).exists():
        return override
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg and shutil.which('ffprobe'):
        return system_ffmpeg
    try:
        import imageio_ffmpeg  # ships a ready-made ffmpeg for Windows, macOS and Linux
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return system_ffmpeg


def find_js_runtimes() -> dict:
    runtimes = {}
    deno = _which('deno')
    if not deno:
        try:
            import deno as deno_pkg  # the "deno" package from PyPI bundles the binary
            deno = deno_pkg.find_deno_bin()
        except Exception:
            deno = None
    if deno:
        runtimes['deno'] = {'path': deno}
    for name in ('node', 'bun'):
        path = shutil.which(name)
        if path:
            runtimes[name] = {'path': path}
    return runtimes


def _has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


FFMPEG = find_ffmpeg()
JS_RUNTIMES = find_js_runtimes()
HAS_EJS = _has_module('yt_dlp_ejs')


def ssl_context():
    """HTTPS settings that work everywhere (python.org's macOS build has no system certificates)."""
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def ffmpeg_version() -> str | None:
    if not FFMPEG:
        return None
    try:
        out = subprocess.run([FFMPEG, '-version'], capture_output=True, text=True,
                             timeout=15, creationflags=NO_WINDOW).stdout
        m = re.match(r'ffmpeg version (\S+)', out)
        return m.group(1) if m else 'unknown'
    except Exception:
        return None


def ytdlp_version() -> str:
    return yt_dlp.version.__version__


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

def default_output_dir() -> str:
    downloads = Path.home() / 'Downloads'
    base = downloads if downloads.is_dir() else Path.home()
    return str(base / 'RealConvert')


class Settings:
    DEFAULTS = {
        'output_dir': '',
        'cookies_browser': '',
        'cookies_file': '',
        'max_parallel': 2,
    }

    def __init__(self, path: Path = SETTINGS_FILE):
        self.path = path
        self.lock = threading.Lock()
        self.data = dict(self.DEFAULTS, output_dir=default_output_dir())
        try:
            saved = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(saved, dict):
                for key in self.DEFAULTS:
                    if key in saved:
                        self.data[key] = saved[key]
        except FileNotFoundError:
            pass
        except Exception as exc:
            log(f'Could not read settings ({exc}); using defaults.')
        if not self.data.get('output_dir'):
            self.data['output_dir'] = default_output_dir()

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.data)

    def update(self, patch: dict) -> dict:
        clean = {}
        if 'output_dir' in patch:
            value = str(patch['output_dir'] or '').strip().strip('"')
            if not value:
                raise ValueError('Choose a folder to save downloads in.')
            path = Path(os.path.expandvars(os.path.expanduser(value)))
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                raise ValueError(f"Can't use that folder: {exc}") from None
            clean['output_dir'] = str(path)
        if 'cookies_browser' in patch:
            value = str(patch['cookies_browser'] or '').strip().lower()
            if value and value not in COOKIE_BROWSERS:
                raise ValueError('Unknown browser.')
            clean['cookies_browser'] = value
        if 'cookies_file' in patch:
            value = str(patch['cookies_file'] or '').strip().strip('"')
            if value and not Path(os.path.expanduser(value)).is_file():
                raise ValueError("That cookies.txt file doesn't exist.")
            clean['cookies_file'] = os.path.expanduser(value) if value else ''
        if 'max_parallel' in patch:
            try:
                value = int(patch['max_parallel'])
            except (TypeError, ValueError):
                raise ValueError('Parallel downloads must be a number.') from None
            clean['max_parallel'] = max(1, min(5, value))
        with self.lock:
            self.data.update(clean)
            try:
                self.path.write_text(json.dumps(self.data, indent=2), encoding='utf-8')
            except Exception as exc:
                log(f'Could not save settings: {exc}')
            return dict(self.data)

    def output_dir(self) -> Path:
        path = Path(self.snapshot()['output_dir'])
        path.mkdir(parents=True, exist_ok=True)
        return path


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

class Cancelled(Exception):
    pass


class ConversionError(Exception):
    pass


class UserError(Exception):
    """A problem with what was asked for; the message is shown to the user as-is."""


COOKIE_HINT = 'Open Settings (gear icon), pick the browser you’re logged in with under “Use cookies from”, then try again.'

FRIENDLY_ERRORS = [
    (r'not a bot', 'YouTube wants to check you’re not a bot. ' + COOKIE_HINT),
    (r'could not (?:copy|find|open).{0,40}cookie|failed to decrypt|cookies? database|unsupported browser',
     'Couldn’t read your browser’s cookies. Close that browser completely and try again, '
     'or choose Firefox or a cookies.txt file in Settings.'),
    (r'private video|this account is private|private account|is private',
     'This video is private. If it’s yours: ' + COOKIE_HINT),
    (r'confirm your age|age.restricted|inappropriate for some users',
     'This video is age-restricted. ' + COOKIE_HINT),
    (r'login required|log ?in|logged.in|sign in|rate.limit reached|requires? authentication|cookies',
     'This site wants you to be logged in. ' + COOKIE_HINT),
    (r'unsupported url', 'That link isn’t supported — make sure it points to a video or post.'),
    (r'is not a valid url|invalid url|no scheme|failed to parse', 'That doesn’t look like a valid link.'),
    (r'video unavailable|has been removed|no longer available|does not exist|http error 404|not found',
     'This video is unavailable — it may have been deleted, made private or blocked in your country.'),
    (r'http error 403|403: forbidden',
     'The site refused the download (error 403). Try again — if it keeps happening, click '
     '“Update engine” at the bottom of the page.'),
    (r'http error 429|too many requests',
     'The site is limiting requests right now. Wait a few minutes and try again.'),
    (r'getaddrinfo|name or service not known|failed to resolve|network is unreachable|timed out|'
     r'no route to host|connection refused|nodename nor servname|temporary failure in name resolution',
     'Couldn’t reach the site. Check your internet connection and try again.'),
    (r'no video formats found|there is no video|no video in this|requested format is not available|'
     r'no media found|no formats found',
     'No downloadable video was found at that link.'),
    (r'is live|live event|premieres in|this live',
     'This is a live stream or premiere that hasn’t finished yet — try again once it’s over.'),
    (r'no space left|errno 28', 'Your disk is full — free up some space and try again.'),
    (r'permission denied|errno 13|access is denied',
     'RealConvert can’t write to the save folder. Pick a different folder in Settings.'),
    (r'ffmpeg|ffprobe|conversion failed|postprocessing', 'Converting the file failed. See details below.'),
]


def clean_message(msg: str) -> str:
    msg = ANSI_RE.sub('', str(msg or '')).strip()
    msg = re.sub(r'^(ERROR|WARNING):\s*', '', msg)
    msg = re.sub(r';?\s*please report this issue on\s+https?://\S+.*$', '', msg, flags=re.I | re.S)
    msg = re.sub(r'Use --cookies-from-browser or --cookies for the authentication\.?', '', msg)
    msg = re.sub(r'See\s+https://github\.com/yt-dlp/yt-dlp/wiki/\S+.*?(?:\.|$)', '', msg)
    return re.sub(r'\s+', ' ', msg).strip()


def friendly_error(exc: BaseException) -> tuple[str, str]:
    detail = clean_message(str(exc)) or exc.__class__.__name__
    lowered = detail.lower()
    for pattern, message in FRIENDLY_ERRORS:
        if re.search(pattern, lowered):
            return message, detail
    return 'Something went wrong with this download. See details below.', detail


class _YdlLogger:
    """Collects yt-dlp output instead of printing it."""

    def __init__(self, tag: str):
        self.tag = tag
        self.warnings: list[str] = []

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        msg = clean_message(msg)
        if msg and msg not in self.warnings:
            self.warnings.append(msg)
            log(f'{self.tag} warning: {msg}')

    def error(self, msg):
        log(f'{self.tag} error: {clean_message(msg)}')


# --------------------------------------------------------------------------
# yt-dlp options
# --------------------------------------------------------------------------

def base_ydl_opts(settings: dict, tag: str) -> dict:
    opts = {
        'logger': _YdlLogger(tag),
        'quiet': True,
        'noprogress': True,
        'noplaylist': True,
        'windowsfilenames': True,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 3,
        'concurrent_fragment_downloads': 4,
        'socket_timeout': 30,
        'overwrites': True,
    }
    if FFMPEG:
        opts['ffmpeg_location'] = FFMPEG
    if JS_RUNTIMES:
        opts['js_runtimes'] = copy.deepcopy(JS_RUNTIMES)
    if not HAS_EJS:
        opts['remote_components'] = ['ejs:github']
    if settings.get('cookies_file'):
        opts['cookiefile'] = settings['cookies_file']
    elif settings.get('cookies_browser'):
        opts['cookiesfrombrowser'] = (settings['cookies_browser'],)
    return opts


def video_format_sort(target: str, quality) -> list[str]:
    res = f'res:{int(quality)}' if str(quality).isdigit() else 'res'
    if target == 'mkv':
        return [res, 'fps']  # anything goes: keep the very best original streams
    if target == 'webm':
        return [res, 'fps', 'vcodec:vp9', 'acodec:opus']
    # MP4 / MOV: at the same resolution, prefer H.264 + AAC (plays everywhere)
    return [res, 'fps', 'vcodec:h264', 'acodec:aac']


AUDIO_SORT = {
    'm4a': ['acodec:aac'],
    'opus': ['acodec:opus'],
}


# --------------------------------------------------------------------------
# ffmpeg helpers
# --------------------------------------------------------------------------

def probe_media(path: Path) -> dict:
    """Read codecs and duration using ffmpeg (works without ffprobe)."""
    info = {'v': None, 'a': None, 'duration': None, 'width': None, 'height': None}
    if not FFMPEG:
        return info
    proc = subprocess.run([FFMPEG, '-hide_banner', '-nostdin', '-i', str(path)],
                          capture_output=True, text=True, encoding='utf-8', errors='replace',
                          creationflags=NO_WINDOW)
    out = proc.stderr
    m = re.search(r'Duration: (\d+):(\d{2}):(\d{2}(?:\.\d+)?)', out)
    if m:
        info['duration'] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    for m in re.finditer(r'Stream #\d+:\d+[^:\n]*: (Video|Audio): (\w+)([^\n]*)', out):
        kind, codec, rest = m.groups()
        if kind == 'Video' and info['v'] is None and 'attached pic' not in rest:
            info['v'] = codec
            size = re.search(r'\b(\d{2,5})x(\d{2,5})\b', rest)
            if size:
                info['width'], info['height'] = int(size.group(1)), int(size.group(2))
        elif kind == 'Audio' and info['a'] is None:
            info['a'] = codec
    return info


EVEN_SIZE = 'scale=trunc(iw/2)*2:trunc(ih/2)*2'
ENCODE_VIDEO = {
    'mp4': ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-vf', EVEN_SIZE],
    'mov': ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-vf', EVEN_SIZE],
    'webm': ['-c:v', 'libvpx-vp9', '-crf', '31', '-b:v', '0', '-row-mt', '1', '-deadline', 'good',
             '-cpu-used', '4', '-pix_fmt', 'yuv420p', '-vf', EVEN_SIZE],
}
ENCODE_AUDIO = {
    'mp4': ['-c:a', 'aac', '-b:a', '192k'],
    'mov': ['-c:a', 'aac', '-b:a', '192k'],
    'webm': ['-c:a', 'libopus', '-b:a', '160k'],
}
VIDEO_OK = {
    'mp4': {'h264', 'hevc', 'vp9', 'av1', 'mpeg4'},
    'mov': {'h264', 'hevc', 'prores', 'mpeg4'},
    'webm': {'vp8', 'vp9', 'av1'},
}
AUDIO_OK = {
    'mp4': {'aac', 'mp3', 'opus', 'flac', 'alac', 'ac3', 'eac3'},
    'mov': {'aac', 'mp3', 'alac', 'pcm_s16le', 'pcm_s24le', 'ac3'},
    'webm': {'opus', 'vorbis'},
}
COMPAT_VIDEO = {'h264'}
COMPAT_AUDIO = {'aac', 'mp3'}


def plan_conversion(target: str, compat: bool, vcodec: str | None, acodec: str | None):
    """Return (ffmpeg codec args, label or None). Label is set when re-encoding is needed."""
    if target == 'mkv':
        return ['-c', 'copy'], None
    strict = compat and target in ('mp4', 'mov')
    v_ok = COMPAT_VIDEO if strict else VIDEO_OK[target]
    a_ok = COMPAT_AUDIO if strict else AUDIO_OK[target]
    args, label = [], None
    if vcodec:
        if vcodec in v_ok:
            args += ['-c:v', 'copy']
            if vcodec == 'hevc':
                args += ['-tag:v', 'hvc1']  # lets Apple devices play H.265
        else:
            args += ENCODE_VIDEO[target]
            label = 'Converting to VP9' if target == 'webm' else 'Converting to H.264'
    if acodec:
        if acodec in a_ok:
            args += ['-c:a', 'copy']
        else:
            args += ENCODE_AUDIO[target]
            label = label or 'Converting audio'
    return args, label


# --------------------------------------------------------------------------
# Link info (for the preview card)
# --------------------------------------------------------------------------

PLATFORMS = [
    ('youtube', 'YouTube'), ('tiktok', 'TikTok'), ('instagram', 'Instagram'),
    ('twitter', 'X'), ('facebook', 'Facebook'), ('vimeo', 'Vimeo'), ('reddit', 'Reddit'),
    ('soundcloud', 'SoundCloud'), ('twitch', 'Twitch'), ('dailymotion', 'Dailymotion'),
    ('pinterest', 'Pinterest'), ('snapchat', 'Snapchat'), ('threads', 'Threads'),
    ('bilibili', 'Bilibili'), ('linkedin', 'LinkedIn'), ('tumblr', 'Tumblr'),
    ('streamable', 'Streamable'), ('kick', 'Kick'), ('rumble', 'Rumble'),
    ('bandcamp', 'Bandcamp'), ('loom', 'Loom'), ('bluesky', 'Bluesky'), ('vk', 'VK'),
]


def platform_of(info: dict, url: str) -> tuple[str, str]:
    key = (info.get('extractor_key') or info.get('ie_key') or '').lower()
    for prefix, name in PLATFORMS:
        if key.startswith(prefix):
            return prefix, name
    host = urllib.parse.urlparse(info.get('webpage_url') or url).netloc.lower()
    host = re.sub(r'^(www|m|mobile)\.', '', host)
    return 'other', host or 'Link'


def fmt_duration(seconds) -> str | None:
    if not seconds:
        return None
    seconds = int(round(float(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'


QUALITY_RUNGS = (4320, 2160, 1440, 1080, 720, 480, 360, 240, 144)


def quality_tag(side: int) -> str:
    if side >= 4320:
        return '8K'
    if side >= 2160:
        return '4K'
    if side >= 1440:
        return '2K'
    if side >= 1080:
        return 'Full HD'
    if side >= 720:
        return 'HD'
    return ''


def quality_list(formats: list) -> list[dict]:
    buckets: dict[int, int] = {}
    for f in formats or []:
        if f.get('vcodec') == 'none':
            continue
        w, h = f.get('width'), f.get('height')
        side = min(w, h) if (w and h) else h
        if not side or side < 100:
            continue
        label = next((r for r in QUALITY_RUNGS if abs(side - r) / r < 0.08), side)
        buckets[label] = max(buckets.get(label, 0), side)
    return [{'value': buckets[label], 'label': f'{label}p', 'tag': quality_tag(label)}
            for label in sorted(buckets, reverse=True)]


def best_thumbnail(entry: dict) -> str | None:
    if entry.get('thumbnail'):
        return entry['thumbnail']
    thumbs = [t for t in (entry.get('thumbnails') or []) if t.get('url')]
    if not thumbs:
        return None
    thumbs.sort(key=lambda t: (t.get('preference') or 0, (t.get('width') or 0) * (t.get('height') or 0)))
    return thumbs[-1]['url']


class ThumbStore:
    """Serves preview images through the app, so sites that block hotlinking still show them."""

    def __init__(self):
        self.lock = threading.Lock()
        self.urls: OrderedDict[str, str] = OrderedDict()
        self.cache: OrderedDict[str, tuple[bytes, str]] = OrderedDict()

    def register(self, url: str | None) -> str | None:
        if not url or not url.startswith(('http://', 'https://')):
            return None
        key = uuid.uuid5(uuid.NAMESPACE_URL, url).hex[:16]
        with self.lock:
            self.urls[key] = url
            while len(self.urls) > 2000:
                self.urls.popitem(last=False)
        return f'/api/thumb/{key}'

    def fetch(self, key: str) -> tuple[bytes, str] | None:
        with self.lock:
            if key in self.cache:
                return self.cache[key]
            url = self.urls.get(key)
        if not url:
            return None
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/130.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/*,*/*;q=0.8',
        })
        try:
            with urllib.request.urlopen(req, timeout=15, context=ssl_context()) as resp:
                data = resp.read(8 * 1024 * 1024)
                ctype = resp.headers.get('Content-Type', 'image/jpeg').split(';')[0]
        except Exception:
            return None
        if not ctype.startswith('image/'):
            ctype = 'image/jpeg'
        with self.lock:
            self.cache[key] = (data, ctype)
            while len(self.cache) > 150:
                self.cache.popitem(last=False)
        return data, ctype


THUMBS = ThumbStore()


def _approx_size(info: dict) -> int | None:
    parts = info.get('requested_formats') or [info]
    total = 0
    for f in parts:
        size = f.get('filesize') or f.get('filesize_approx')
        if not size:
            return None
        total += size
    return int(total) or None


def _summarize_video(info: dict, url: str) -> dict:
    formats = info.get('formats') or []
    has_video = any(f.get('vcodec') != 'none' for f in formats) if formats else info.get('vcodec') != 'none'
    has_audio = any(f.get('acodec') != 'none' for f in formats) if formats else info.get('acodec') != 'none'
    w, h = info.get('width'), info.get('height')
    orientation = None
    if w and h:
        orientation = 'vertical' if h > w * 1.05 else 'horizontal' if w > h * 1.05 else 'square'
    pkey, pname = platform_of(info, url)
    qualities = quality_list(formats) if has_video else []
    return {
        'kind': 'video',
        'url': info.get('webpage_url') or info.get('original_url') or url,
        'title': info.get('title') or info.get('fulltitle') or 'Untitled',
        'uploader': info.get('uploader') or info.get('channel') or info.get('creator') or info.get('uploader_id'),
        'duration': info.get('duration'),
        'duration_text': fmt_duration(info.get('duration')),
        'platform': pname,
        'platform_key': pkey,
        'thumbnail': THUMBS.register(best_thumbnail(info)),
        'width': w,
        'height': h,
        'orientation': orientation,
        'has_video': bool(has_video),
        'has_audio': bool(has_audio),
        'qualities': qualities,
        'filesize': _approx_size(info),
        'count': 1,
    }


def get_info(url: str, settings: dict) -> dict:
    opts = base_ydl_opts(settings, '[info]')
    opts.update({'skip_download': True, 'extract_flat': 'in_playlist', 'playlistend': 300})
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise ConversionError('No media found at that link.')

    if info.get('_type') == 'playlist':
        entries = [e for e in (info.get('entries') or []) if e]
        if not entries:
            raise ConversionError('No media found at that link (the playlist is empty).')
        flat = all(e.get('_type') in ('url', 'url_transparent') for e in entries)
        if flat:
            pkey, pname = platform_of(info, url)
            items = []
            for e in entries:
                link = e.get('url') or e.get('webpage_url')
                if not link or not str(link).startswith(('http://', 'https://')):
                    link = e.get('webpage_url')
                if not link or not str(link).startswith(('http://', 'https://')):
                    continue
                items.append({
                    'url': link,
                    'title': e.get('title') or link,
                    'duration_text': fmt_duration(e.get('duration')),
                    'thumbnail': THUMBS.register(best_thumbnail(e)),
                })
            if not items:
                raise ConversionError('No downloadable videos were found in that playlist.')
            return {
                'kind': 'playlist',
                'url': url,
                'title': info.get('title') or 'Playlist',
                'uploader': info.get('uploader') or info.get('channel'),
                'platform': pname,
                'platform_key': pkey,
                'thumbnail': THUMBS.register(best_thumbnail(info)) or items[0]['thumbnail'],
                'count': len(items),
                'truncated': len(items) >= 300,
                'entries': items,
            }
        # A post with several videos (e.g. an Instagram carousel): one download grabs them all.
        summary = _summarize_video(entries[0], url)
        summary.update(kind='multi', count=len(entries), url=url,
                       title=info.get('title') or summary['title'],
                       thumbnail=summary['thumbnail'] or THUMBS.register(best_thumbnail(info)),
                       filesize=None)
        return summary

    if info.get('is_live') or info.get('live_status') in ('is_live', 'is_upcoming'):
        raise ConversionError('This is a live stream that hasn’t finished yet — try again once it’s over.')
    return _summarize_video(info, url)


# --------------------------------------------------------------------------
# Download jobs
# --------------------------------------------------------------------------

def _parse_time(value) -> float | None:
    if value in (None, ''):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    seconds = parse_duration(text)
    if seconds is None:
        raise ValueError(f'“{text}” isn’t a valid time. Use something like 1:30 or 90.')
    return float(seconds)


def _clock(seconds: float) -> str:
    """90.5 -> '1m30s' (file-name safe on every OS)."""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f'{h}h{m:02d}m{s:02d}s'
    return f'{m}m{s:02d}s' if m else f'{s}s'


def normalize_options(raw: dict) -> dict:
    fmt = str(raw.get('format') or 'mp4').lower()
    if fmt not in VIDEO_FORMATS + AUDIO_FORMATS:
        raise ValueError('Unknown format.')
    quality = str(raw.get('quality') or 'best')
    if quality != 'best' and not quality.isdigit():
        quality = 'best'
    bitrate = str(raw.get('audio_quality') or '320')
    if bitrate not in AUDIO_BITRATES:
        bitrate = '320'
    start = _parse_time(raw.get('trim_start'))
    end = _parse_time(raw.get('trim_end'))
    if start is not None and end is not None and end <= start:
        raise ValueError('The trim end time has to be after the start time.')
    return {
        'format': fmt,
        'kind': 'audio' if fmt in AUDIO_FORMATS else 'video',
        'quality': quality,
        'audio_quality': bitrate,
        'compat': bool(raw.get('compat', True)),
        'trim_start': start,
        'trim_end': end,
    }


class Job:
    def __init__(self, url: str, options: dict, meta: dict):
        self.id = uuid.uuid4().hex[:12]
        self.url = url
        self.options = options
        self.title = meta.get('title') or url
        self.thumbnail = meta.get('thumbnail')
        self.platform = meta.get('platform')
        self.platform_key = meta.get('platform_key')
        self.status = 'queued'   # queued, preparing, downloading, processing, done, error, cancelled
        self.stage = 'Waiting in line…'
        self.progress: float | None = None
        self.speed: float | None = None
        self.speed_text: str | None = None
        self.eta: float | None = None
        self.downloaded: int | None = None
        self.total: int | None = None
        self.files: list[Path] = []
        self.error: str | None = None
        self.error_detail: str | None = None
        self.warnings: list[str] = []
        self.created = time.time()
        self.finished: float | None = None
        self.cancel_event = threading.Event()
        self.proc: subprocess.Popen | None = None
        # progress bookkeeping
        self._weights: dict = {}
        self._fallback_weights = False
        self._stream_frac: dict = {}
        self._expected_bytes: int | None = None
        self._entry_count = 1

    @property
    def active(self) -> bool:
        return self.status in ('queued', 'preparing', 'downloading', 'processing')

    def to_dict(self) -> dict:
        o = self.options
        files = []
        for i, p in enumerate(self.files):
            try:
                size = p.stat().st_size
            except OSError:
                size = None
            files.append({'index': i, 'name': p.name, 'size': size, 'ext': p.suffix.lstrip('.').lower()})
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'thumbnail': self.thumbnail,
            'platform': self.platform,
            'platform_key': self.platform_key,
            'format': o['format'],
            'kind': o['kind'],
            'quality': o['quality'],
            'audio_quality': o['audio_quality'],
            'trimmed': o['trim_start'] is not None or o['trim_end'] is not None,
            'status': self.status,
            'stage': self.stage,
            'progress': self.progress,
            'speed': self.speed,
            'speed_text': self.speed_text,
            'eta': self.eta,
            'downloaded': self.downloaded,
            'total': self.total,
            'files': files,
            'error': self.error,
            'error_detail': self.error_detail,
            'created': self.created,
            'finished': self.finished,
            'options': {k: o[k] for k in ('format', 'quality', 'audio_quality', 'compat', 'trim_start', 'trim_end')},
        }


class _Slots:
    """Limits how many downloads run at once (the limit can change while running)."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.cond = threading.Condition()
        self.active = 0

    def acquire(self, cancel_event: threading.Event):
        with self.cond:
            while self.active >= int(self.settings.snapshot().get('max_parallel') or 2):
                if cancel_event.is_set():
                    raise Cancelled()
                self.cond.wait(0.5)
            self.active += 1

    def release(self):
        with self.cond:
            self.active -= 1
            self.cond.notify_all()


def unique_path(folder: Path, stem: str, suffix: str) -> Path:
    stem = stem.strip().rstrip('.') or 'download'
    candidate = folder / f'{stem}{suffix}'
    n = 2
    while candidate.exists():
        candidate = folder / f'{stem} ({n}){suffix}'
        n += 1
    return candidate


class JobManager:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.jobs: OrderedDict[str, Job] = OrderedDict()
        self.lock = threading.Lock()
        self.name_lock = threading.Lock()
        self.slots = _Slots(settings)

    # ---- public API -------------------------------------------------------

    def submit(self, url: str, raw_options: dict, meta: dict | None = None) -> Job:
        url = (url or '').strip()
        if not re.match(r'^https?://', url, re.I):
            raise ValueError('That doesn’t look like a link. It should start with http:// or https://')
        job = Job(url, normalize_options(raw_options), meta or {})
        with self.lock:
            self.jobs[job.id] = job
        threading.Thread(target=self._run, args=(job,), daemon=True, name=f'job-{job.id}').start()
        return job

    def list(self) -> list[dict]:
        with self.lock:
            jobs = list(self.jobs.values())
        return [j.to_dict() for j in reversed(jobs)]

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job or not job.active:
            return False
        job.cancel_event.set()
        job.stage = 'Cancelling…'
        proc = job.proc
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass
        return True

    def remove(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job.active:
                return False
            del self.jobs[job_id]
            return True

    def clear_finished(self) -> int:
        with self.lock:
            done = [k for k, j in self.jobs.items() if not j.active]
            for k in done:
                del self.jobs[k]
            return len(done)

    def active_count(self) -> int:
        with self.lock:
            return sum(1 for j in self.jobs.values() if j.active)

    def cleanup_temp(self):
        try:
            temp_root = self.settings.output_dir() / TEMP_DIRNAME
            if temp_root.exists() and not self.active_count():
                shutil.rmtree(temp_root, ignore_errors=True)
        except Exception:
            pass

    # ---- worker -----------------------------------------------------------

    def _run(self, job: Job):
        tag = f'[{job.id}]'
        temp_dir = None
        try:
            self.slots.acquire(job.cancel_event)
        except Cancelled:
            job.status, job.stage, job.finished = 'cancelled', 'Cancelled', time.time()
            return
        try:
            settings = self.settings.snapshot()
            out_dir = self.settings.output_dir()
            temp_dir = out_dir / TEMP_DIRNAME / job.id
            temp_dir.mkdir(parents=True, exist_ok=True)
            log(f'{tag} start {job.options["format"].upper()} {job.url}')
            self._download(job, settings, temp_dir)
            self._deliver(job, temp_dir, out_dir)
            job.status, job.stage, job.progress = 'done', 'Saved', 1.0
            log(f'{tag} done -> {", ".join(p.name for p in job.files)}')
        except Cancelled:
            job.status, job.stage = 'cancelled', 'Cancelled'
            log(f'{tag} cancelled')
        except Exception as exc:
            if job.cancel_event.is_set():
                job.status, job.stage = 'cancelled', 'Cancelled'
                log(f'{tag} cancelled')
            elif isinstance(exc, UserError):
                job.error, job.error_detail = str(exc), None
                job.status, job.stage = 'error', 'Failed'
                log(f'{tag} failed: {exc}')
            else:
                job.error, job.error_detail = friendly_error(exc)
                if job.options['trim_start'] is not None or job.options['trim_end'] is not None:
                    if job.error.startswith(('Converting', 'Something went wrong')):
                        job.error = ('Couldn’t cut that part of the video. Check the trim times are inside the '
                                     'video’s length, or try again without trimming.')
                job.status, job.stage = 'error', 'Failed'
                log(f'{tag} failed: {job.error_detail}')
        finally:
            job.finished = time.time()
            job.proc = None
            job.speed = job.eta = None
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            self.slots.release()

    def _download(self, job: Job, settings: dict, temp_dir: Path):
        o = job.options
        fmt = o['format']
        opts = base_ydl_opts(settings, f'[{job.id}]')
        opts['outtmpl'] = {'default': str(temp_dir / '%(title).110B [%(id)s].%(ext)s')}
        opts['progress_hooks'] = [lambda d: self._on_progress(job, d)]
        opts['postprocessor_hooks'] = [lambda d: self._on_postprocess(job, d)]

        if o['kind'] == 'video':
            opts['format'] = 'bv*+ba/b'
            opts['format_sort'] = video_format_sort(fmt, o['quality'])
            opts['merge_output_format'] = {'mp4': 'mp4/mkv', 'mov': 'mp4/mkv', 'webm': 'webm/mkv'}.get(fmt, 'mkv')
        else:
            opts['format'] = 'ba/b'
            if fmt in AUDIO_SORT:
                opts['format_sort'] = AUDIO_SORT[fmt]
            codec = 'best' if fmt == 'original' else ('vorbis' if fmt == 'ogg' else fmt)
            quality = {'mp3': o['audio_quality'], 'm4a': '256', 'opus': '160'}.get(fmt)
            pp = {'key': 'FFmpegExtractAudio', 'preferredcodec': codec}
            if quality:
                pp['preferredquality'] = quality
            opts['postprocessors'] = [pp]

        start, end = o['trim_start'], o['trim_end']
        if start is not None or end is not None:
            opts['download_ranges'] = download_range_func(None, [(start or 0, end if end is not None else float('inf'))])
            opts['force_keyframes_at_cuts'] = True

        job.status, job.stage = 'preparing', 'Reading link…'
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job.url, download=False)
            if job.cancel_event.is_set():
                raise Cancelled()
            if not info:
                raise ConversionError('No media found at that link.')
            if info.get('is_live') or info.get('live_status') in ('is_live', 'is_upcoming'):
                raise UserError('This is a live stream that hasn’t finished yet — try again once it’s over.')
            self._adopt_meta(job, info)
            duration = info.get('duration')
            if start is not None and duration and start >= duration:
                raise UserError(f'The trim start ({fmt_duration(start) or "0:00"}) is after the end of the '
                                 f'video ({fmt_duration(duration)}).')
            self._plan_progress(job, info, trimmed=('download_ranges' in opts))
            job.stage = 'Starting download…'
            ydl.process_ie_result(info, download=True)
            job.warnings = list(opts['logger'].warnings)
        if job.cancel_event.is_set():
            raise Cancelled()

    def _adopt_meta(self, job: Job, info: dict):
        first = info
        if info.get('_type') == 'playlist':
            entries = [e for e in (info.get('entries') or []) if e]
            first = entries[0] if entries else info
        if not job.title or job.title == job.url:
            job.title = info.get('title') or first.get('title') or job.url
        if not job.thumbnail:
            job.thumbnail = THUMBS.register(best_thumbnail(first) or best_thumbnail(info))
        if not job.platform:
            job.platform_key, job.platform = platform_of(first, job.url)

    # ---- progress ---------------------------------------------------------

    def _plan_progress(self, job: Job, info: dict, trimmed: bool):
        entries = [e for e in (info.get('entries') or []) if e] if info.get('_type') == 'playlist' else [info]
        job._entry_count = max(1, len(entries))
        sizes, keys = {}, []
        for e in entries:
            parts = e.get('requested_formats') or [e]
            for f in parts:
                key = (e.get('id'), f.get('format_id'))
                keys.append((key, f))
                sizes[key] = f.get('filesize') or f.get('filesize_approx')
        if keys and not trimmed and all(sizes.values()):
            total = sum(sizes.values())
            job._weights = {k: s / total for k, s in sizes.items()}
            job._expected_bytes = int(total)
            job._fallback_weights = False
        else:
            share = 1 / job._entry_count
            weights = {}
            for e in entries:
                parts = e.get('requested_formats') or [e]
                videos = [f for f in parts if f.get('vcodec') != 'none']
                for f in parts:
                    if len(parts) == 1:
                        w = 1.0
                    elif f.get('vcodec') == 'none':
                        w = 0.15
                    else:
                        w = 0.85 / max(1, len(videos))
                    weights[(e.get('id'), f.get('format_id'))] = share * w
            job._weights = weights if not trimmed else {}
            job._expected_bytes = None
            job._fallback_weights = True

    def _on_progress(self, job: Job, d: dict):
        if job.cancel_event.is_set():
            raise Cancelled()
        status = d.get('status')
        info = d.get('info_dict') or {}
        key = (info.get('id'), info.get('format_id'))
        if status == 'downloading':
            job.status = 'downloading'
            done = d.get('downloaded_bytes') or 0
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            frac = (done / total) if total else None
            if frac is None and d.get('fragment_count'):
                frac = (d.get('fragment_index') or 0) / d['fragment_count']
            if frac is not None:
                frac = max(0.0, min(1.0, frac))
                job._stream_frac[key] = frac
            if key in job._weights:
                job.progress = min(0.999, sum(w * job._stream_frac.get(k, 0) for k, w in job._weights.items()))
            else:
                job.progress = frac
            job.speed = d.get('speed')
            job.speed_text = None
            if job._expected_bytes and job.speed and job.progress is not None:
                job.eta = max(0, job._expected_bytes * (1 - job.progress) / job.speed)
                job.downloaded = int(job._expected_bytes * job.progress)
                job.total = job._expected_bytes
            else:
                job.eta = d.get('eta')
                job.downloaded = done
                job.total = int(total) if total else None
            vcodec, acodec = info.get('vcodec'), info.get('acodec')
            what = 'audio' if vcodec == 'none' else 'video' if acodec == 'none' else ''
            stage = f'Downloading {what}'.strip()
            if job._entry_count > 1 and info.get('playlist_index'):
                stage += f' ({info["playlist_index"]} of {job._entry_count})'
            job.stage = stage
        elif status == 'finished':
            job._stream_frac[key] = 1.0
            if key in job._weights:
                job.progress = min(0.999, sum(w * job._stream_frac.get(k, 0) for k, w in job._weights.items()))

    def _on_postprocess(self, job: Job, d: dict):
        if job.cancel_event.is_set():
            raise Cancelled()
        if d.get('status') != 'started':
            return
        name = d.get('postprocessor') or ''
        fmt = job.options['format']
        labels = {
            'Merger': 'Merging video and audio…',
            'ExtractAudio': 'Saving audio…' if fmt == 'original' else f'Converting to {fmt.upper()}…',
            'FixupM3u8': 'Finishing up…',
            'FixupStretched': 'Finishing up…',
            'FixupDuplicateMoov': 'Finishing up…',
            'FixupTimestamp': 'Finishing up…',
            'FixupDuration': 'Finishing up…',
            'ModifyChapters': 'Trimming…',
        }
        if name in labels:
            job.status, job.stage = 'processing', labels[name]
            job.progress = job.speed = job.eta = job.downloaded = job.total = None

    # ---- convert + move into the output folder -----------------------------

    def _media_files(self, temp_dir: Path) -> list[Path]:
        files = []
        for p in temp_dir.rglob('*'):
            if not p.is_file():
                continue
            name = p.name.lower()
            if p.suffix.lower() in MEDIA_JUNK_SUFFIXES or '.part' in name or name.endswith('.ytdl'):
                continue
            if re.search(r'\.f[\w-]+\.\w+$', name):  # leftover unmerged stream
                continue
            files.append(p)
        files.sort(key=lambda p: p.stat().st_mtime)
        return files

    def _run_ffmpeg(self, job: Job, args: list[str], duration: float | None):
        cmd = [FFMPEG, '-hide_banner', '-nostdin', '-y', *args]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                encoding='utf-8', errors='replace', creationflags=NO_WINDOW)
        job.proc = proc
        tail: list[str] = []
        try:
            for line in proc.stdout:
                line = line.strip()
                if job.cancel_event.is_set():
                    proc.kill()
                    break
                m = re.match(r'^([a-z_]+)=(.*)$', line)
                if not m:
                    if line:
                        tail = (tail + [line])[-15:]
                    continue
                k, v = m.groups()
                if k in ('out_time_us', 'out_time_ms') and v.strip().isdigit() and duration:
                    job.progress = max(0.0, min(0.999, int(v) / 1e6 / duration))
                elif k == 'speed' and v not in ('N/A', ''):
                    job.speed_text = v.strip()
        finally:
            rc = proc.wait()
            job.proc = None
        if job.cancel_event.is_set():
            raise Cancelled()
        if rc != 0:
            raise ConversionError('ffmpeg: ' + (' | '.join(tail) or f'exited with code {rc}'))

    def _convert_video(self, job: Job, src: Path, target: str, compat: bool) -> Path:
        probe = probe_media(src)
        args, label = plan_conversion(target, compat, probe['v'], probe['a'])
        if label is None and src.suffix.lower() == f'.{target}':
            return src
        if not FFMPEG:
            raise ConversionError('ffmpeg is missing, so the file can’t be converted.')
        out = src.with_name(f'{src.stem}.rc-out.{target}')
        cmd = ['-i', str(src), '-map', '0:v:0?', '-map', '0:a:0?', *args, '-map_metadata', '0']
        if target in ('mp4', 'mov'):
            cmd += ['-movflags', '+faststart']
        cmd += ['-progress', 'pipe:1', '-nostats', '-loglevel', 'error', str(out)]
        job.status = 'processing'
        job.stage = f'{label}…' if label else f'Saving as {target.upper()}…'
        job.progress = 0.0 if label else None
        job.speed = job.eta = job.downloaded = job.total = None
        job.speed_text = None
        self._run_ffmpeg(job, cmd, probe['duration'] if label else None)
        final = src.with_name(f'{src.stem}.{target}')
        src.unlink(missing_ok=True)
        out.replace(final)
        return final

    def _deliver(self, job: Job, temp_dir: Path, out_dir: Path):
        o = job.options
        files = self._media_files(temp_dir)
        if not files:
            raise ConversionError('The download finished but no file was produced.')
        suffix = ''
        if o['trim_start'] is not None or o['trim_end'] is not None:
            start = _clock(o['trim_start'] or 0)
            end = _clock(o['trim_end']) if o['trim_end'] is not None else 'end'
            suffix = f' (clip {start}-{end})'
        total = len(files)
        for i, src in enumerate(files, 1):
            if job.cancel_event.is_set():
                raise Cancelled()
            if o['kind'] == 'video':
                src = self._convert_video(job, src, o['format'], o['compat'])
                if total > 1 and job.stage:
                    job.stage = f'{job.stage.rstrip("…")} ({i} of {total})…'
            stem = re.sub(r'\s*\[[^\[\]]*\]$', '', src.stem) or 'download'
            with self.name_lock:
                dest = unique_path(out_dir, stem + suffix, src.suffix.lower())
                shutil.move(str(src), str(dest))
            job.files.append(dest)


def open_in_file_manager(path: Path, select: bool = True):
    """Show a file in Explorer / Finder / the Linux file manager, or open it."""
    path = Path(path)
    if sys.platform.startswith('win'):
        if select and path.is_file():
            subprocess.Popen(f'explorer /select,"{path}"')
        else:
            os.startfile(str(path))  # noqa: S606 - opening the user's own file
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', '-R', str(path)] if select and path.is_file() else ['open', str(path)])
    else:
        target = path.parent if (select and path.is_file()) else path
        subprocess.Popen(['xdg-open', str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
