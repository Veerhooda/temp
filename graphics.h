#ifndef GRAPHICS_H
#define GRAPHICS_H

#include <windows.h>
#include <conio.h>
#include <iostream>
#include <cmath>

#define DETECT 0
#define WHITE RGB(255, 255, 255)
#define BLACK RGB(0, 0, 0)
#define RED RGB(255, 0, 0)
#define GREEN RGB(0, 255, 0)
#define BLUE RGB(0, 0, 255)
#define YELLOW RGB(255, 255, 0)
#define CYAN RGB(0, 255, 255)
#define MAGENTA RGB(255, 0, 255)
#define BROWN RGB(139, 69, 19)
#define DARKGRAY RGB(128, 128, 128)
#define LIGHTGRAY RGB(192, 192, 192)
#define LIGHTBLUE RGB(173, 216, 230)
#define LIGHTGREEN RGB(144, 238, 144)
#define LIGHTCYAN RGB(224, 255, 255)
#define LIGHTRED RGB(255, 102, 102)
#define LIGHTMAGENTA RGB(255, 153, 255)

static HWND g_hWnd = NULL;
static HDC g_hDC = NULL;
static HDC g_hMemDC = NULL;
static HBITMAP g_hBitmap = NULL;
static HBITMAP g_hOldBitmap = NULL;
static int g_width = 640;
static int g_height = 480;
static COLORREF g_currentColor = RGB(255, 255, 255);
static bool g_mouseClicked = false;
static int g_mouseX = 0;
static int g_mouseY = 0;

inline void bgi_flush_events() {
    MSG msg;
    while (PeekMessage(&msg, NULL, 0, 0, PM_REMOVE)) {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }
}

inline LRESULT CALLBACK BgiWndProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
        case WM_LBUTTONDOWN:
            g_mouseClicked = true;
            g_mouseX = LOWORD(lParam);
            g_mouseY = HIWORD(lParam);
            return 0;
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);
            if (g_hMemDC) {
                BitBlt(hdc, 0, 0, g_width, g_height, g_hMemDC, 0, 0, SRCCOPY);
            }
            EndPaint(hwnd, &ps);
            return 0;
        }
    }
    return DefWindowProc(hwnd, uMsg, wParam, lParam);
}

inline void initgraph(int *gd, int *gm, const char *pathtodriver = "") {
    WNDCLASS wc = {0};
    wc.lpfnWndProc = BgiWndProc;
    wc.hInstance = GetModuleHandle(NULL);
    wc.lpszClassName = "BGI_Win32_Class";
    wc.hbrBackground = (HBRUSH)GetStockObject(BLACK_BRUSH);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    RegisterClass(&wc);

    g_width = 640;
    g_height = 480;

    RECT rc = {0, 0, g_width, g_height};
    AdjustWindowRect(&rc, WS_OVERLAPPEDWINDOW, FALSE);

    g_hWnd = CreateWindow("BGI_Win32_Class", "Computer Graphics Lab Window",
                          WS_OVERLAPPEDWINDOW | WS_VISIBLE,
                          CW_USEDEFAULT, CW_USEDEFAULT,
                          rc.right - rc.left, rc.bottom - rc.top,
                          NULL, NULL, GetModuleHandle(NULL), NULL);

    g_hDC = GetDC(g_hWnd);

    // Offscreen memory bitmap buffer for persistent painting
    g_hMemDC = CreateCompatibleDC(g_hDC);
    g_hBitmap = CreateCompatibleBitmap(g_hDC, g_width, g_height);
    g_hOldBitmap = (HBITMAP)SelectObject(g_hMemDC, g_hBitmap);

    // Fill background with black
    HBRUSH hBrush = CreateSolidBrush(RGB(0, 0, 0));
    RECT fullRc = {0, 0, g_width, g_height};
    FillRect(g_hMemDC, &fullRc, hBrush);
    DeleteObject(hBrush);

    UpdateWindow(g_hWnd);
    SetForegroundWindow(g_hWnd);
    bgi_flush_events();
}

inline void cleardevice() {
    if (g_hDC && g_hMemDC) {
        HBRUSH hBrush = CreateSolidBrush(RGB(0, 0, 0));
        RECT fullRc = {0, 0, g_width, g_height};
        FillRect(g_hMemDC, &fullRc, hBrush);
        FillRect(g_hDC, &fullRc, hBrush);
        DeleteObject(hBrush);
        bgi_flush_events();
    }
}

inline int getmaxx() { return g_width; }
inline int getmaxy() { return g_height; }

inline void setcolor(int color) {
    g_currentColor = color;
}

inline void putpixel(int x, int y, COLORREF color = WHITE) {
    if (g_hDC && g_hMemDC) {
        SetPixel(g_hMemDC, x, y, color);
        SetPixel(g_hDC, x, y, color);
        bgi_flush_events();
    }
}

inline COLORREF getpixel(int x, int y) {
    if (g_hMemDC) {
        return GetPixel(g_hMemDC, x, y);
    }
    return 0;
}

inline void outtextxy(int x, int y, const char *text) {
    if (g_hDC && g_hMemDC) {
        SetTextColor(g_hMemDC, g_currentColor);
        SetBkMode(g_hMemDC, TRANSPARENT);
        TextOutA(g_hMemDC, x, y, text, (int)strlen(text));

        SetTextColor(g_hDC, g_currentColor);
        SetBkMode(g_hDC, TRANSPARENT);
        TextOutA(g_hDC, x, y, text, (int)strlen(text));

        bgi_flush_events();
    }
}

inline void line(int x1, int y1, int x2, int y2) {
    if (g_hDC && g_hMemDC) {
        HPEN hPen = CreatePen(PS_SOLID, 1, g_currentColor);
        HPEN hOldPen1 = (HPEN)SelectObject(g_hMemDC, hPen);
        HPEN hOldPen2 = (HPEN)SelectObject(g_hDC, hPen);

        MoveToEx(g_hMemDC, x1, y1, NULL);
        LineTo(g_hMemDC, x2, y2);

        MoveToEx(g_hDC, x1, y1, NULL);
        LineTo(g_hDC, x2, y2);

        SelectObject(g_hMemDC, hOldPen1);
        SelectObject(g_hDC, hOldPen2);
        DeleteObject(hPen);
        bgi_flush_events();
    }
}

inline void rectangle(int left, int top, int right, int bottom) {
    line(left, top, right, top);
    line(right, top, right, bottom);
    line(right, bottom, left, bottom);
    line(left, bottom, left, top);
}

inline void circle(int x, int y, int radius) {
    if (g_hDC && g_hMemDC) {
        HPEN hPen = CreatePen(PS_SOLID, 1, g_currentColor);
        HBRUSH hNullBrush = (HBRUSH)GetStockObject(NULL_BRUSH);

        HPEN hOldPen1 = (HPEN)SelectObject(g_hMemDC, hPen);
        HBRUSH hOldBrush1 = (HBRUSH)SelectObject(g_hMemDC, hNullBrush);

        HPEN hOldPen2 = (HPEN)SelectObject(g_hDC, hPen);
        HBRUSH hOldBrush2 = (HBRUSH)SelectObject(g_hDC, hNullBrush);

        Ellipse(g_hMemDC, x - radius, y - radius, x + radius + 1, y + radius + 1);
        Ellipse(g_hDC, x - radius, y - radius, x + radius + 1, y + radius + 1);

        SelectObject(g_hMemDC, hOldPen1);
        SelectObject(g_hMemDC, hOldBrush1);
        SelectObject(g_hDC, hOldPen2);
        SelectObject(g_hDC, hOldBrush2);

        DeleteObject(hPen);
        bgi_flush_events();
    }
}

inline bool ismouseclick(int kind) {
    bgi_flush_events();
    return g_mouseClicked;
}

inline void getmouseclick(int kind, int &x, int &y) {
    bgi_flush_events();
    x = g_mouseX;
    y = g_mouseY;
}

inline void clearmouseclick(int kind) {
    g_mouseClicked = false;
}

inline void delay(int ms) {
    DWORD start = GetTickCount();
    while (GetTickCount() - start < (DWORD)ms) {
        bgi_flush_events();
        Sleep(1);
    }
}

inline void closegraph() {
    if (g_hWnd) {
        if (g_hMemDC) {
            SelectObject(g_hMemDC, g_hOldBitmap);
            DeleteObject(g_hBitmap);
            DeleteDC(g_hMemDC);
            g_hMemDC = NULL;
        }
        ReleaseDC(g_hWnd, g_hDC);
        DestroyWindow(g_hWnd);
        g_hWnd = NULL;
        g_hDC = NULL;
    }
}

#endif
