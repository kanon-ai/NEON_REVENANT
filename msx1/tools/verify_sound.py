"""Exercise the PSG driver on a host C compiler; no MSX hardware is simulated.

Run from either port: python tools/verify_sound.py. Use a C compiler shell
(gcc, clang, or Visual Studio Developer Command Prompt); CC overrides it.
Native PSG execution is checked separately by the openMSX integration test.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1]
build=ROOT/'work/sound-test';build.mkdir(parents=True,exist_ok=True)
cc=os.environ.get('CC') or next((shutil.which(x) for x in ['clang','gcc','cl'] if shutil.which(x)),None)
if not cc:raise SystemExit('A host C compiler is required. Run in a gcc/clang or Visual Studio Developer Command Prompt, or set CC.')
compiler_env=dict(os.environ)
compiler_env['PATH']=str(Path(cc).resolve().parent)+os.pathsep+compiler_env.get('PATH','')
exe=build/('sound-test.exe' if os.name=='nt' else 'sound-test')
sources=[ROOT/'src/sound.c',ROOT/'tools/test_sound.c']
if Path(cc).stem.lower()=='cl':
    args=[cc,'/nologo','/W4','/DSOUND_HOST_TEST','/I'+str(ROOT/'src'),'/Fe:'+str(exe),'/Fo:'+str(build)+os.sep,*map(str,sources)]
else:
    args=[cc,'-Wall','-Wextra','-DSOUND_HOST_TEST','-I',str(ROOT/'src'),'-o',str(exe),*map(str,sources)]
subprocess.run(args,cwd=build,env=compiler_env,check=True)
result=subprocess.run([str(exe)],env=compiler_env,text=True,capture_output=True,check=True)
report=json.loads(result.stdout)
assert report['passed'] and not report['failures']
report.update({'kind':'host PSG register protocol and music/effect regression test','physical_hardware_tested':False,'source_sha256':hashlib.sha256(sources[0].read_bytes()).hexdigest()})
# When the preserved v1.1 source archive is present, compile its driver with
# the same register trace harness and compare all three original arrangements.
archive=ROOT.parent/'outputs/msx1/v1.1/NEON_REVENANT-MSX1-v1.1-complete.zip'
if archive.is_file():
    legacy=build/'legacy';legacy.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for name in ('sound.c','sound.h'):
            matches=[n for n in z.namelist() if n.endswith('/msx1/src/'+name)]
            assert len(matches)==1
            (legacy/name).write_bytes(z.read(matches[0]))
    old_exe=legacy/('sound-test.exe' if os.name=='nt' else 'sound-test')
    if Path(cc).stem.lower()=='cl':
        old_args=[cc,'/nologo','/W4','/DSOUND_HOST_TEST','/DSOUND_TEST_STAGE_COUNT=3','/I'+str(legacy),'/Fe:'+str(old_exe),'/Fo:'+str(legacy)+os.sep,str(legacy/'sound.c'),str(sources[1])]
    else:
        old_args=[cc,'-Wall','-Wextra','-DSOUND_HOST_TEST','-DSOUND_TEST_STAGE_COUNT=3','-I',str(legacy),'-o',str(old_exe),str(legacy/'sound.c'),str(sources[1])]
    subprocess.run(old_args,cwd=legacy,env=compiler_env,check=True)
    old=json.loads(subprocess.run([str(old_exe)],env=compiler_env,text=True,capture_output=True,check=True).stdout)
    equal=all(new[:3]==prior for new,prior in zip(report['stage_hashes'],old['stage_hashes']))
    assert equal,'Original v1.1 music register traces changed'
    report['original_three_arrangements_match_v1_1']={'passed':equal,'direction_variants':4,'ticks_per_arrangement':384,'baseline_source_sha256':hashlib.sha256((legacy/'sound.c').read_bytes()).hexdigest()}
out=ROOT.parent/'outputs'/ROOT.name/'v1.3';out.mkdir(parents=True,exist_ok=True)
(out/'sound-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
