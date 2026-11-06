"""Native floating window and read-only macOS desktop wallpaper support."""
from pathlib import Path
import sys


def wallpaper_image():
    """Return encoded PNG in memory, never expose arbitrary local file paths."""
    if sys.platform != 'darwin':
        raise ValueError('Tự đọc hình nền hiện hỗ trợ macOS.')
    from AppKit import NSWorkspace, NSScreen, NSImage, NSBitmapImageRep, NSPNGFileType
    screen = NSScreen.mainScreen()
    url = NSWorkspace.sharedWorkspace().desktopImageURLForScreen_(screen)
    if url is None or not Path(str(url.path())).is_file():
        raise ValueError('Không lấy được ảnh tĩnh của hình nền desktop hiện tại.')
    image = NSImage.alloc().initWithContentsOfURL_(url)
    if image is None:
        raise ValueError('Hình nền không có ảnh xem trước khả dụng.')
    bitmap = NSBitmapImageRep.imageRepWithData_(image.TIFFRepresentation())
    if bitmap is None:
        raise ValueError('Không giải mã được hình nền.')
    return bytes(bitmap.representationUsingType_properties_(NSPNGFileType, {}))


class WindowAPI:
    def __init__(self):
        self._window = None
        self._size = (1220, 860)
        self._compact = False

    def compact(self, enabled):
        if not isinstance(enabled, bool):
            raise ValueError('Trạng thái không hợp lệ.')
        w = self._window
        if enabled and not self._compact:
            self._size = (w.width, w.height)
        w.on_top = enabled
        w.resize(420, 540) if enabled else w.resize(*self._size)
        self._compact = enabled
        return {'compact': enabled, 'on_top': enabled}

    def minimize(self):
        self._window.minimize()


def launch(url):
    if sys.platform == 'darwin':
        return launch_macos(url)
    import webview
    api = WindowAPI()
    api._window = webview.create_window('Iris Studio · Eye HCI', url, js_api=api,
        width=1220, height=860, min_size=(380, 420), background_color='#07151f')
    # Native title bar provides reliable dragging, resizing and Dock restore.
    webview.start(private_mode=False)


def launch_macos(url):
    """Build a small native AppKit/WKWebView shell using installed Xcode tools."""
    import plistlib
    import subprocess
    root = Path(__file__).resolve().parent.parent
    source = root / 'native' / 'IrisStudio.m'
    bundle = root / 'build' / 'Iris Studio.app'
    contents = bundle / 'Contents'
    executable = contents / 'MacOS' / 'IrisStudio'
    executable.parent.mkdir(parents=True, exist_ok=True)
    (contents / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': 'IrisStudio', 'CFBundleIdentifier': 'local.eye-hci.iris-studio',
        'CFBundleName': 'Iris Studio', 'CFBundlePackageType': 'APPL',
        'NSHighResolutionCapable': True,
    }))
    if not executable.exists() or executable.stat().st_mtime < source.stat().st_mtime:
        subprocess.run(['xcrun', 'clang', '-fobjc-arc', str(source), '-o', str(executable),
                        '-framework', 'Cocoa', '-framework', 'WebKit'], check=True)
    process = subprocess.Popen(['open', '-W', '-n', str(bundle), '--args', url])
    try:
        process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
