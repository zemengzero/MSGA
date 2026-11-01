"""Capture an owned Win32 window via PrintWindow; never capture the desktop."""

import ctypes
import os
from ctypes import wintypes as W

from PIL import Image


def capture_owned_window(root, target):
    u = ctypes.windll.user32
    g = ctypes.windll.gdi32
    u.GetAncestor.argtypes = [W.HWND, W.UINT]
    u.GetAncestor.restype = W.HWND
    u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
    u.GetWindowRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
    u.GetWindowDC.argtypes = [W.HWND]
    u.GetWindowDC.restype = W.HDC
    u.ReleaseDC.argtypes = [W.HWND, W.HDC]
    u.PrintWindow.argtypes = [W.HWND, W.HDC, W.UINT]
    u.PrintWindow.restype = W.BOOL
    g.CreateCompatibleDC.argtypes = [W.HDC]
    g.CreateCompatibleDC.restype = W.HDC
    g.CreateCompatibleBitmap.argtypes = [W.HDC, ctypes.c_int, ctypes.c_int]
    g.CreateCompatibleBitmap.restype = W.HBITMAP
    g.SelectObject.argtypes = [W.HDC, W.HGDIOBJ]
    g.SelectObject.restype = W.HGDIOBJ
    g.DeleteObject.argtypes = [W.HGDIOBJ]
    g.DeleteDC.argtypes = [W.HDC]

    class Header(ctypes.Structure):
        _fields_ = [
            ("size", W.DWORD),
            ("width", W.LONG),
            ("height", W.LONG),
            ("planes", W.WORD),
            ("bits", W.WORD),
            ("compression", W.DWORD),
            ("image_size", W.DWORD),
            ("xppm", W.LONG),
            ("yppm", W.LONG),
            ("used", W.DWORD),
            ("important", W.DWORD),
        ]

    class Info(ctypes.Structure):
        _fields_ = [("header", Header), ("colors", W.DWORD * 3)]

    g.GetDIBits.argtypes = [
        W.HDC,
        W.HBITMAP,
        W.UINT,
        W.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(Info),
        W.UINT,
    ]
    hwnd = u.GetAncestor(root.winfo_id(), 2)
    pid = W.DWORD()
    u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value != os.getpid():
        raise RuntimeError("拒绝读取其他进程窗口")
    rect = W.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    dc = u.GetWindowDC(hwnd)
    memory = g.CreateCompatibleDC(dc)
    bitmap = g.CreateCompatibleBitmap(dc, width, height)
    prior = g.SelectObject(memory, bitmap)
    try:
        if not u.PrintWindow(hwnd, memory, 2):
            raise RuntimeError("PrintWindow未成功；不使用桌面截图替代")
        info = Info()
        info.header = Header(
            ctypes.sizeof(Header), width, -height, 1, 32, 0, 0, 0, 0, 0, 0
        )
        raw = ctypes.create_string_buffer(width * height * 4)
        if not g.GetDIBits(memory, bitmap, 0, height, raw, ctypes.byref(info), 0):
            raise RuntimeError("读取本窗口像素失败")
        Image.frombytes("RGB", (width, height), raw.raw, "raw", "BGRX").save(target)
    finally:
        g.SelectObject(memory, prior)
        g.DeleteObject(bitmap)
        g.DeleteDC(memory)
        u.ReleaseDC(hwnd, dc)
