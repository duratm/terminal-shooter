import select
import threading
import time
import sys
import os

try:
    import evdev
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False

class EvdevController:
    def __init__(self, debug=False):
        self.device = None
        self.active_keys = set()
        self.running = False
        self.thread = None
        self.found_device = False
        self.error = None
        self.debug = debug
        
        if not EVDEV_AVAILABLE:
            self.error = "evdev module not installed"
            return

        # Map evdev key codes to our game keys
        self.key_map = {
            evdev.ecodes.KEY_W: 'w',
            evdev.ecodes.KEY_S: 's',
            evdev.ecodes.KEY_A: 'a',
            evdev.ecodes.KEY_D: 'd',
            evdev.ecodes.KEY_LEFT: 'left',
            evdev.ecodes.KEY_RIGHT: 'right',
            evdev.ecodes.KEY_SPACE: 'space',
            evdev.ecodes.KEY_R: 'r',
            evdev.ecodes.KEY_Q: 'q',
            evdev.ecodes.KEY_ESC: 'esc',
            evdev.ecodes.KEY_LEFTSHIFT: 'shift',
            evdev.ecodes.KEY_RIGHTSHIFT: 'shift'
        }
        
        try:
            self._find_keyboard()
        except PermissionError:
            self.error = "Permission denied. Try running with sudo or add user to 'input' group."
        except Exception as e:
            self.error = str(e)

    def _find_keyboard(self):
        """Find the best candidate for a keyboard."""
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        except Exception as e:
            self.error = f"Error listing devices: {e}"
            return

        best_candidate = None
        
        for device in devices:
            try:
                # Check capabilities
                caps = device.capabilities()
                if evdev.ecodes.EV_KEY in caps:
                    keys = caps[evdev.ecodes.EV_KEY]
                    # Check for WASD keys being present in the device capabilities
                    # We check if these KEY codes exist in the list of keys this device supports
                    if (evdev.ecodes.KEY_W in keys and 
                        evdev.ecodes.KEY_A in keys and 
                        evdev.ecodes.KEY_S in keys and 
                        evdev.ecodes.KEY_D in keys):
                        
                        # print(f"Found compatible keyboard: {device.name} at {device.path}")
                        best_candidate = device
                        # Prefer devices with 'keyboard' in the name
                        if 'keyboard' in device.name.lower():
                            break
            except Exception:
                continue
        
        if best_candidate:
            self.device = best_candidate
            self.found_device = True
        else:
            self.error = "No compatible keyboard found (must support WASD)."

    def start(self):
        if not self.device:
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.1)

    def _loop(self):
        try:
            # We use select here to allow checking self.running periodically
            while self.running:
                # Check if device is ready for reading
                r, w, x = select.select([self.device.fd], [], [], 0.1)
                if r:
                    for event in self.device.read():
                        if event.type == evdev.ecodes.EV_KEY:
                            if event.code in self.key_map:
                                key_name = self.key_map[event.code]
                                if event.value == 1: # Key down
                                    self.active_keys.add(key_name)
                                    if self.debug:
                                        try:
                                            with open("/tmp/evdev_debug.log", "a") as f:
                                                f.write(f"KEY DOWN: {key_name} (code={event.code}) active_keys={self.active_keys}\n")
                                        except:
                                            pass
                                elif event.value == 0: # Key up
                                    self.active_keys.discard(key_name)
                                    if self.debug:
                                        try:
                                            with open("/tmp/evdev_debug.log", "a") as f:
                                                f.write(f"KEY UP: {key_name} (code={event.code}) active_keys={self.active_keys}\n")
                                        except:
                                            pass
                                # event.value == 2 is repeat, we ignore it for now as we track held state manually
                            elif self.debug:
                                # Log unknown keys in debug mode
                                try:
                                    with open("/tmp/evdev_debug.log", "a") as f:
                                        f.write(f"UNKNOWN KEY: code={event.code} value={event.value}\n")
                                except:
                                    pass
        except Exception as e:
            # If device is closed or permissions lost
            if self.running:
                # Always log errors
                try:
                    with open("/tmp/evdev_debug.log", "a") as f:
                        import traceback
                        f.write(f"LOOP ERROR: {e}\n")
                        traceback.print_exc(file=f)
                except:
                    pass
                self.error = str(e)
        finally:
            self.running = False

    def get_key_state(self, key):
        return key in self.active_keys
