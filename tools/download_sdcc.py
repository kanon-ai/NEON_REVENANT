import concurrent.futures, hashlib, json, pathlib, urllib.request
PROJECT = pathlib.Path(__file__).resolve().parents[1]
root = PROJECT / 'work/toolchain/sdcc'
commit = 'ab4b26feda36189e677aa23b56acfdc3218f7953'
tree_file=PROJECT / 'work/msxgl-tree.json'
if tree_file.exists():
    tree = json.loads(tree_file.read_text())
else:
    tree=json.loads(urllib.request.urlopen(f'https://api.github.com/repos/aoineko-fr/MSXgl/git/trees/{commit}?recursive=1').read())
assert tree['sha']==commit
prefix = 'tools/sdcc/'
files = [x for x in tree['tree'] if x['type'] == 'blob' and x['path'].startswith(prefix) and (x['path'].endswith('.exe') or x['path']==prefix+'bin/cc1' or x['path'].startswith(prefix+'include/') or x['path'].startswith(prefix+'lib/z80/') or x['path'].endswith('COPYING.txt') or x['path'].endswith('COPYING3.txt'))]
def fetch(x):
    rel = x['path'][len(prefix):]
    url = f"https://raw.githubusercontent.com/aoineko-fr/MSXgl/{tree['sha']}/{x['path']}"
    dest=root/rel
    data = dest.read_bytes() if dest.exists() else urllib.request.urlopen(url,timeout=60).read()
    assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==x['sha'],rel
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes(data)
    return {'path': rel,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source':url}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    manifest=list(pool.map(fetch,files))
(root/'bin/cc1.exe').write_bytes((root/'bin/cc1').read_bytes())
(root/'PROVENANCE.json').write_text(json.dumps({'repository':'https://github.com/aoineko-fr/MSXgl','commit':tree['sha'],'local_adjustment':'bin/cc1 copied byte-for-byte to bin/cc1.exe so the Windows C preprocessor can execute it','files':manifest},indent=2))
print(f'Downloaded and verified {len(manifest)} official repository files: {sum(x["bytes"] for x in manifest):,} bytes')
