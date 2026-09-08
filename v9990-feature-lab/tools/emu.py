"""Send a Tcl command to the workspace's running development emulator."""
import sys,urllib.request
req=urllib.request.Request('http://127.0.0.1:18890',data=' '.join(sys.argv[1:]).encode(),method='POST')
try:print(urllib.request.urlopen(req,timeout=25).read().decode())
except urllib.error.HTTPError as e:print(e.read().decode());sys.exit(1)
