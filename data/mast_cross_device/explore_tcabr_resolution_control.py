import sys, json, glob, numpy as np, pandas as pd
sys.path.insert(0,"/mnt/user-data/uploads/Downloads/a/TIMDR-fusion-tools")
from model_j.model_j_detector import quench_duration, is_fast_quench
man=json.load(open('tcabr_new_20_5_normal_15_disruptive/MANIFEST.json'))
lab={s['shot_id']:s['shot_type'] for s in man['samples']}
rows=[]
for f in sorted(glob.glob('tcabr_new_20_5_normal_15_disruptive/*.npz')):
    try: z=np.load(f); z["shot_id"]
    except Exception: print("POMINIETY (uszkodzony plik):",f[-28:]); continue
    sh=int(str(z['shot_id'])); t=z['IPlasma_time_us'].astype(float)*1e-6; x=z['IPlasma'].astype(float)
    pass  # bez korekty znaku: TCABR ma dodatni prad, a start zapisu zawiera artefakt digitizera ±152
    dt=float(np.median(np.diff(t)))
    r=dict(shot=sh,label=lab[sh],dt_us=dt*1e6)
    # A: native TCABR params (as in repo tests)
    r['d_native_ms']=(quench_duration(x,dt=dt,exclude_start=2000) or np.nan)*1e3
    # B: decimated to 200 us, MAST-frozen params
    for name,y in (('dec',x[::50]),('blk',x[:len(x)//50*50].reshape(-1,50).mean(1))):
        d=quench_duration(y,dt=200e-6,fraction_high=.7,fraction_low=.1,smooth_window=1,exclude_start=40)
        r[f'd_{name}_ms']=(d if d is not None else np.nan)*1e3
    rows.append(r)
df=pd.DataFrame(rows)
for c in ['d_native_ms','d_dec_ms','d_blk_ms']:
    df[c.replace('d_','fast_').replace('_ms','')]=df[c]<15
pd.set_option('display.width',200); print(df.round(2).to_string(index=False))
for c in ['native','dec','blk']:
    p=df['fast_'+c]; y=df.label=='Disruptive'
    print(c,'TP',int((p&y).sum()),'FN',int((~p&y).sum()),'FP',int((p&~y).sum()),'TN',int((~p&~y).sum()))
df.to_csv('tcabr_control.csv',index=False)
