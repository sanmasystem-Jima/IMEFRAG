import tkinter as tk
from PIL import Image, ImageTk
import ctypes
import os
import sys
import threading
import pystray

# ==========================================
# 1. 重複起動防止 (Mutex)
# ==========================================
app_id = "IMEFRAG_SINGLE_INSTANCE_MUTEX_JIMA"
mutex = ctypes.windll.kernel32.CreateMutexW(None, False, app_id)
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit()

# ==========================================
# 2. Windows API 型定義
# ==========================================
class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

user32 = ctypes.windll.user32
imm32 = ctypes.windll.imm32
user32.SendMessageW.restype = ctypes.c_longlong

# ==========================================
# 3. 準備
# ==========================================
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

root = tk.Tk()
root.withdraw()

try:
    path_jp  = os.path.join(base_path, "jp.png")
    path_eg  = os.path.join(base_path, "eg.png")
    path_off = os.path.join(base_path, "off.png")
    img_jp   = Image.open(path_jp)
    img_eg   = Image.open(path_eg)
    img_off  = Image.open(path_off)
    photo_jp  = ImageTk.PhotoImage(img_jp.resize((20, 20)))
    photo_eg  = ImageTk.PhotoImage(img_eg.resize((20, 20)))
    photo_off = ImageTk.PhotoImage(img_off.resize((40, 20)))   # 「半角」は横長なので40x20
    tray_img  = img_jp.resize((64, 64))
except Exception as e:
    sys.exit()

# 旗オーバーレイ
overlay = tk.Toplevel(root)
overlay.overrideredirect(True)
overlay.attributes("-topmost", True, "-transparentcolor", "white")
overlay.withdraw()
label = tk.Label(overlay, bg="white")
label.pack()

# ==========================================
# 4. IMEロジック
# ==========================================
def get_ime_status():
    try:
        f_hwnd = user32.GetForegroundWindow()
        u_hwnd = imm32.ImmGetDefaultIMEWnd(f_hwnd)
        is_open = user32.SendMessageW(u_hwnd, 0x0283, 0x0005, 0)
        if not is_open:
            return 0          # IMEオフ → 半角
        conv_mode = user32.SendMessageW(u_hwnd, 0x0283, 0x0001, 0)
        return 1 if (conv_mode & 0x0001) else 2
    except:
        return 0

def update_overlay():
    status = get_ime_status()
    if status == 0:
        # IMEオフ → 「半角」画像をマウスポインタ付近に表示
        label.config(image=photo_off)
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        overlay.geometry(f"40x20+{pt.x - 20}+{pt.y - 50}")
        if not overlay.winfo_viewable():
            overlay.deiconify()
    else:
        label.config(image=photo_jp if status == 1 else photo_eg)
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        overlay.geometry(f"20x20+{pt.x - 10}+{pt.y - 50}")
        if not overlay.winfo_viewable():
            overlay.deiconify()
    root.after(60, update_overlay)

# ==========================================
# 5. タスクトレイ
# ==========================================
def quit_app():
    """トレイアイコンを確実に消してから終了する"""
    try:
        tray_icon.stop()
    except Exception:
        pass
    root.destroy()

def on_quit(icon, item):
    # pystray のコールバックは別スレッドなので root.after で安全にキュー
    root.after(0, quit_app)

tray_icon = pystray.Icon(
    "IMEFRAG",
    tray_img,
    "IMEFRAG",
    menu=pystray.Menu(
        pystray.MenuItem("終了", on_quit)
    )
)

tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
tray_thread.start()

# ==========================================
# 6. 起動
# ==========================================
update_overlay()
root.mainloop()

# mainloop を抜けたときも念のためアイコンを消す
try:
    tray_icon.stop()
except Exception:
    pass
