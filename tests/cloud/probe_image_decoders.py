"""Independent bounded decoder verification for generated TIFF/PSD fixtures."""
import hashlib,json,os,resource,subprocess,sys,time
from pathlib import Path

def child(engine,path,preview):
    resource.setrlimit(resource.RLIMIT_AS,(768*1024**2,768*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(15,15))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    started=time.monotonic();frames=[]
    try:
        if engine=='pillow':
            from PIL import Image
            with Image.open(path) as image:
                # PSD n_frames counts layers; a flattened composite can have zero layers.
                count=1 if image.format=='PSD' else max(1,getattr(image,'n_frames',1))
                for index in range(count):
                    if index:image.seek(index)
                    image.load()
                    frames.append({'width':image.width,'height':image.height,'mode':image.mode,'pixel_sha256':hashlib.sha256(image.tobytes()).hexdigest()})
                    if index==0:
                        thumb=image.convert('RGB');thumb.thumbnail((256,256));thumb.save(preview,format='PNG')
        else:
            import pyvips
            pyvips.cache_set_max(0);pyvips.cache_set_max_mem(32*1024**2)
            initial=pyvips.Image.new_from_file(str(path),access='sequential')
            pages=initial.get('n-pages') if initial.get_typeof('n-pages') else 1
            for index in range(pages):
                image=pyvips.Image.new_from_file(str(path),page=index,access='sequential') if str(path).endswith('.tif') else initial
                mode={('uchar',3):'RGB',('uchar',1):'L',('ushort',1):'I;16'}.get((image.format,image.bands),image.format+':'+str(image.bands))
                frames.append({'width':image.width,'height':image.height,'mode':mode,'pixel_sha256':hashlib.sha256(image.write_to_memory()).hexdigest()})
            pyvips.Image.thumbnail(str(path),256).write_to_file(str(preview))
        result={'decoded':True,'frames':frames,'preview_bytes':preview.stat().st_size}
    except Exception as error:
        message=str(error)[:500]
        unsupported=engine=='vips' and ('not a known file format' in message or 'no loader' in message)
        result={'decoded':False,'error_class':type(error).__name__,'error':message,'unsupported':unsupported}
    result.update(elapsed_s=time.monotonic()-started,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    print(json.dumps(result))

def run(directory,output=None):
    assert not directory.is_symlink()
    directory=directory.resolve();assert not (directory/'manifest.json').is_symlink()
    manifest=json.loads((directory/'manifest.json').read_text())
    output=output or directory.parent/'image-probe-results'
    assert output.resolve().parent==directory.parent
    output.mkdir(exist_ok=False)
    os.nice(15)
    env=os.environ.copy();env.update(VIPS_CONCURRENCY='2',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
    rows=[];hard_failures=[]
    for case in manifest['cases']:
        name=case['file'];assert Path(name).name==name
        path=directory/name;assert path.is_file() and not path.is_symlink()
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        for engine in ['pillow','vips']:
            preview=output/(engine+'-'+name+'.png')
            started=time.monotonic()
            try:
                p=subprocess.run([sys.executable,__file__,'--child',engine,str(path),str(preview)],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=25)
                result=json.loads(p.stdout) if p.returncode==0 else {'decoded':False,'process_failed':True,'exit_code':p.returncode,'stderr':p.stderr[-500:]}
            except subprocess.TimeoutExpired:
                result={'decoded':False,'timed_out':True}
            if case['expected_error']:
                parse_error=result.get('error_class') in {'UnidentifiedImageError','OSError','SyntaxError','ValueError','Error'}
                allocation_error=any(word in result.get('error','').lower() for word in ['out of memory','cannot allocate','allocation failed'])
                passed=not result['decoded'] and parse_error and not allocation_error and not result.get('process_failed') and not result.get('timed_out')
            else:
                passed=result['decoded'] and result['frames']==case['frames'] and result['preview_bytes']>0
                if passed:
                    from PIL import Image
                    with Image.open(preview) as thumb:
                        thumb.load();assert 0<thumb.width<=256 and 0<thumb.height<=256
            compatibility_gap=engine=='vips' and case['format']=='PSD' and result.get('unsupported',False) and not case['expected_error']
            if not passed and not compatibility_gap:hard_failures.append(engine+':'+name)
            rows.append(dict(engine=engine,file=name,expected_error=case['expected_error'],passed=passed,compatibility_gap=compatibility_gap,whole_child_wall_s=time.monotonic()-started,**result))
        assert hashlib.sha256(path.read_bytes()).hexdigest()==before,'Input changed'
    from PIL import __version__ as pillow_version
    import pyvips
    summary={'hard_failures':hard_failures,'core_checks_passed':not hard_failures,'input_files_unchanged':True,'synthetic_only':True,'case_count':len(manifest['cases']),'pillow_version':pillow_version,'libvips_version':'.'.join(str(pyvips.version(n)) for n in range(3)),'limits':{'child_address_space_mib':768,'child_cpu_seconds':15,'child_wall_seconds':25,'vips_threads':2},'rows':rows,'all_decoder_cases_passed':all(x['passed'] for x in rows)}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))
    return 0 if summary['all_decoder_cases_passed'] else (2 if summary['core_checks_passed'] else 1)

if __name__=='__main__':
    if len(sys.argv)==5 and sys.argv[1]=='--child':child(sys.argv[2],Path(sys.argv[3]),Path(sys.argv[4]))
    elif len(sys.argv)==2:raise SystemExit(run(Path(sys.argv[1])))
    elif len(sys.argv)==3:raise SystemExit(run(Path(sys.argv[1]),Path(sys.argv[2])))
    else:raise SystemExit('Usage: probe_image_decoders.py FIXTURE_DIRECTORY [OUTPUT_DIRECTORY]')
