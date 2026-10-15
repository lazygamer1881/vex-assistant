import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _fatal(e):
    """Startup failed: write a local crash report and tell the user where it is (nothing is sent anywhere)."""
    path = ""
    try:
        from vex import crashreport
        path = crashreport.write("startup failed", type(e), e, e.__traceback__)
    except Exception:
        pass
    if "--child" in sys.argv or "--selftest" in sys.argv:
        return   # the watchdog restarts the app; avoid a pile of message boxes
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, "Vex couldn't start.\n\n%s: %s\n\nA crash report was saved here (nothing was sent):\n%s\n\n"
                                         "Try again, or share that file with whoever gave you Vex." % (type(e).__name__, str(e)[:300], path),
                                         "Vex Assistant", 0x10)
    except Exception:
        pass


try:
    from vex import crashreport
    crashreport.install()
except Exception:
    pass
try:
    from vex import voicepack
    voicepack.activate()
except Exception:
    pass
try:
    from vex.main import main
    main()
except SystemExit:
    raise
except BaseException as e:
    _fatal(e)
    sys.exit(1)
