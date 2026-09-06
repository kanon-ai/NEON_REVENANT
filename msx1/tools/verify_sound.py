"""Exercise the PSG driver on a host C compiler; no MSX hardware is simulated.

Run from either port: python tools/verify_sound.py. Use a C compiler shell
(gcc, clang, or Visual Studio Developer Command Prompt); CC overrides it.
Native PSG execution is checked separately by the openMSX integration test.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
build=ROOT/'work/sound-test';build.mkdir(parents=True,exist_ok=True)
cc=os.environ.get('CC') or next((shutil.which(x) for x in ['clang','gcc','cl'] if shutil.which(x)),None)
if not cc:raise SystemExit('A host C compiler is required. Run in a gcc/clang or Visual Studio Developer Command Prompt, or set CC.')
exe=build/('sound-test.exe' if os.name=='nt' else 'sound-test')
sources=[ROOT/'src/sound.c',ROOT/'tools/test_sound.c']
if Path(cc).stem.lower()=='cl':
    args=[cc,'/nologo','/W4','/DSOUND_HOST_TEST','/I'+str(ROOT/'src'),'/Fe:'+str(exe),'/Fo:'+str(build)+os.sep,*map(str,sources)]
else:
    args=[cc,'-Wall','-Wextra','-DSOUND_HOST_TEST','-I',str(ROOT/'src'),'-o',str(exe),*map(str,sources)]
subprocess.run(args,cwd=build,check=True)
result=subprocess.run([str(exe)],text=True,capture_output=True,check=True)
report=json.loads(result.stdout)
assert report['passed'] and not report['failures']
report.update({'kind':'host PSG register protocol and music/effect regression test','physical_hardware_tested':False,'source_sha256':hashlib.sha256(sources[0].read_bytes()).hexdigest()})
out=ROOT.parent/'outputs'/ROOT.name/'v1.1';out.mkdir(parents=True,exist_ok=True)
(out/'sound-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
