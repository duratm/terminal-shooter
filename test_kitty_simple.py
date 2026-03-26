import sys
import base64
from io import BytesIO
from PIL import Image, ImageDraw

def serialize_gr_command(cmd, payload=None):
    cmd = {'a': 'T', 'f': 100, **cmd}
    vals = ','.join(f'{k}={v}' for k, v in cmd.items())
    res = list()
    res.append(f'\033_G{vals}')
    if payload:
        res.append(';')
        res.append(payload)
    res.append('\033\\')
    return ''.join(res)

def write_chunked(cmd, data):
    data = base64.standard_b64encode(data).decode('ascii')
    while data:
        chunk, data = data[:4096], data[4096:]
        m = 1 if data else 0
        sys.stdout.write(serialize_gr_command({**cmd, 'm': m}, chunk))
        sys.stdout.flush()
        cmd.clear()

def test_kitty():
    # Create a simple image
    img = Image.new('RGB', (200, 100), color = (73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Hello Kitty Graphics!", fill=(255,255,0))
    d.rectangle([50, 50, 150, 80], fill=(255, 0, 0))
    
    # Serialize
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    data = buffer.getvalue()
    
    print("Attempting to display image...")
    # a=T (transmit and display), f=100 (PNG)
    write_chunked({'a': 'T', 'f': 100}, data)
    print("\nImage sent.")

if __name__ == "__main__":
    test_kitty()
