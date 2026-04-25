using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;

// HotkeyHelper
// - installs WH_KEYBOARD_LL
// - consumes matching hotkey keystrokes
// - fires on key-up by sending JSON line over localhost TCP

internal static class Program
{
    private static int Main(string[] args)
    {
        return new HotkeyApp().Run(args);
    }
}

internal sealed class HotkeyApp
{
    private record Binding(int Mods, int Vk, string Id);

    public int Run(string[] args)
    {
        string? host = null;
        int port = 0;
        string? configPath = null;
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--host" && i + 1 < args.Length) host = args[++i];
            else if (args[i] == "--port" && i + 1 < args.Length) port = int.TryParse(args[++i], out var p) ? p : 0;
            else if (args[i] == "--config" && i + 1 < args.Length) configPath = args[++i];
        }

        if (string.IsNullOrWhiteSpace(host) || port <= 0 || string.IsNullOrWhiteSpace(configPath) || !File.Exists(configPath))
        {
            Usage();
            return 2;
        }

        var bindings = LoadBindings(configPath);
        if (bindings.Count == 0)
        {
            // Still connect so NovaPad can distinguish "no bindings" vs "hook failed".
        }

        using var client = new TcpClient();
        client.Connect(host!, port);
        using var stream = client.GetStream();
        using var writer = new StreamWriter(stream, new UTF8Encoding(false)) { AutoFlush = true };

        string? activeId = null;
        int activeVk = 0;

        nint hook = 0;

        Win32.LowLevelKeyboardProc proc = (nCode, wParam, lParam) =>
        {
            if (nCode < 0) return Win32.CallNextHookEx(hook, nCode, wParam, lParam);

            int msg = (int)wParam;
            bool isDown = msg == Win32.WM_KEYDOWN || msg == Win32.WM_SYSKEYDOWN;
            bool isUp = msg == Win32.WM_KEYUP || msg == Win32.WM_SYSKEYUP;
            var kb = Marshal.PtrToStructure<Win32.KBDLLHOOKSTRUCT>(lParam);
            int vk = (int)kb.vkCode;

            if (isDown)
            {
                int mods = ModsNow();
                foreach (var b in bindings)
                {
                    if (vk != b.Vk) continue;
                    if ((mods & b.Mods) != b.Mods) continue;
                    activeId = b.Id;
                    activeVk = vk;
                    return 1; // eat
                }
            }

            if (isUp && activeId != null && vk == activeVk)
            {
                writer.WriteLine(JsonSerializer.Serialize(new { type = "hotkey", id = activeId }));
                activeId = null;
                activeVk = 0;
                return 1; // eat key up
            }

            return Win32.CallNextHookEx(hook, nCode, wParam, lParam);
        };

        nint hMod = Win32.GetModuleHandleW(null);
        hook = Win32.SetWindowsHookExW(Win32.WH_KEYBOARD_LL, proc, hMod, 0);
        if (hook == 0)
        {
            int err = Marshal.GetLastWin32Error();
            writer.WriteLine(JsonSerializer.Serialize(new { type = "error", err }));
            return 3;
        }

        try
        {
            while (true)
            {
                int gm = Win32.GetMessageW(out var msg, 0, 0, 0);
                if (gm == 0) break; // WM_QUIT
                if (gm == -1) break; // error
                Win32.TranslateMessage(ref msg);
                Win32.DispatchMessageW(ref msg);
            }
        }
        finally
        {
            Win32.UnhookWindowsHookEx(hook);
        }

        return 0;
    }

    private static List<Binding> LoadBindings(string configPath)
    {
        var bindings = new List<Binding>();
        try
        {
            using var fs = File.OpenRead(configPath);
            var doc = JsonDocument.Parse(fs);
            foreach (var el in doc.RootElement.EnumerateArray())
            {
                var id = el.GetProperty("id").GetString() ?? "";
                var mods = el.GetProperty("mods").GetInt32();
                var key = el.GetProperty("key").GetString() ?? "";
                var vk = VkFromKey(key);
                if (vk != 0 && mods != 0 && id.Length > 0)
                    bindings.Add(new Binding(mods, vk, id));
            }
        }
        catch
        {
            // ignore
        }
        return bindings;
    }

    private static int VkFromKey(string key)
    {
        key = (key ?? "").Trim().ToUpperInvariant();
        if (key.Length == 1)
        {
            char c = key[0];
            if (c >= 'A' && c <= 'Z') return c;
            if (c >= '0' && c <= '9') return c;
        }
        if (key.StartsWith("F") && int.TryParse(key.Substring(1), out int n) && n >= 1 && n <= 24)
            return 0x70 + (n - 1);
        return 0;
    }

    private static int ModsNow()
    {
        int m = 0;
        if ((Win32.GetAsyncKeyState(Win32.VK_SHIFT) & 0x8000) != 0) m |= 1;
        if ((Win32.GetAsyncKeyState(Win32.VK_CONTROL) & 0x8000) != 0) m |= 2;
        if ((Win32.GetAsyncKeyState(Win32.VK_MENU) & 0x8000) != 0) m |= 4;
        return m;
    }

    private static void Usage()
    {
        Console.Error.WriteLine("Usage: HotkeyHelper --host <127.0.0.1> --port <port> --config <path>");
    }
}

internal static class Win32
{
    public const int WH_KEYBOARD_LL = 13;
    public const int WM_KEYDOWN = 0x0100;
    public const int WM_KEYUP = 0x0101;
    public const int WM_SYSKEYDOWN = 0x0104;
    public const int WM_SYSKEYUP = 0x0105;

    public const int VK_SHIFT = 0x10;
    public const int VK_CONTROL = 0x11;
    public const int VK_MENU = 0x12; // Alt

    public delegate nint LowLevelKeyboardProc(int nCode, nint wParam, nint lParam);

    [StructLayout(LayoutKind.Sequential)]
    public struct KBDLLHOOKSTRUCT
    {
        public uint vkCode;
        public uint scanCode;
        public uint flags;
        public uint time;
        public nuint dwExtraInfo;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int x; public int y; }

    [StructLayout(LayoutKind.Sequential)]
    public struct MSG
    {
        public nint hwnd;
        public uint message;
        public nuint wParam;
        public nint lParam;
        public uint time;
        public POINT pt;
    }

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern nint SetWindowsHookExW(int idHook, LowLevelKeyboardProc lpfn, nint hMod, uint dwThreadId);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool UnhookWindowsHookEx(nint hhk);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern nint CallNextHookEx(nint hhk, int nCode, nint wParam, nint lParam);

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern nint GetModuleHandleW(string? lpModuleName);

    [DllImport("user32.dll")]
    public static extern short GetAsyncKeyState(int vKey);

    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern int GetMessageW(out MSG lpMsg, nint hWnd, uint wMsgFilterMin, uint wMsgFilterMax);

    [DllImport("user32.dll")]
    public static extern bool TranslateMessage(ref MSG lpMsg);

    [DllImport("user32.dll")]
    public static extern nint DispatchMessageW(ref MSG lpMsg);
}
