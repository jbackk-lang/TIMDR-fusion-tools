import sys,pickle,numpy as np,pandas as pd
sys.path.insert(0,"/mnt/user-data/uploads/Downloads/a/TIMDR-fusion-tools")
from model_j.model_j_detector import _decay_window_bounds
data=pickle.load(open('data.pkl','rb')); res=pd.read_csv('/mnt/user-data/outputs/mast_validation/results.csv')
# 1. odpornosc reguly znaku: ta sama regula tylko na x[40:]
flip_all=set(res.shot[res.flipped]); flip_late=set()
art=0
for s,(t,ip) in data.items():
    x=np.asarray(ip,float)
    if abs(np.nanmin(x[40:]))>abs(np.nanmax(x[40:])): flip_late.add(s)
    if abs(x[:40]).max()>0.5*abs(x[40:]).max(): art+=1
print('flip rule differs (all vs x[40:]):',sorted(flip_all^flip_late),'| shots with startup |ip|>50% of peak in first 8ms:',art)
# 2. cechy strukturalne
rows=[]
for s,(t,ip) in data.items():
    x=np.asarray(ip,float); x=-x if s in flip_all else x
    b=_decay_window_bounds(x,exclude_start=40,smooth_window=1)
    ih,il=b
    pk=int(np.argmax(x[40:]))+40
    rows.append(dict(shot=s,t_end=t[-1],t_peak=t[pk],t_hi=t[ih],t_lo=t[il],ipk=x[pk],ip_end_frac=x[-1]/x[pk],
                     t_after_lo=t[-1]-t[il], flat_before=(t[ih]-t[pk])))
f=pd.DataFrame(rows).merge(res[['shot','quench_duration_s','is_fast','n_bridge','flipped']],on='shot')
f['d_ms']=f.quench_duration_s*1e3; f['logd']=np.log10(f.d_ms)
# 3. mieszanina 1 vs 2 vs 3 skladniki w log10(d)
from sklearn.mixture import GaussianMixture
X=f.logd.values.reshape(-1,1)
for k in (1,2,3):
    g=GaussianMixture(k,n_init=10,random_state=0).fit(X)
    print(f'GMM k={k}: BIC={g.bic(X):.1f} means(ms)={np.sort(10**g.means_.ravel()).round(2)} weights={np.round(g.weights_[np.argsort(g.means_.ravel())],2)}')
g=GaussianMixture(2,n_init=10,random_state=0).fit(X); lo,hi=np.sort(g.means_.ravel())
grid=np.linspace(lo,hi,2000); post=g.predict_proba(grid.reshape(-1,1)); c=np.argmin(np.abs(post[:,0]-post[:,1])); 
print('granica 50/50 miedzy skladnikami [ms]:',round(10**grid[c],2))
# 4. gestosc wokol progu, drobne przedzialy
bins=[0,1,2,3,4,5,6,8,10,12,15,20,25,30,40,60,100,200,5000]
print(pd.cut(f.d_ms,bins).value_counts().sort_index().to_string())
# 5. udzial szybkich wg numeru strzalu
f['bin']=pd.cut(f.shot,[11000,14000,17000,20000,23000,26000,31000])
print(f.groupby('bin',observed=True).agg(n=('shot','size'),fast=('is_fast','mean'),med_d=('d_ms','median'),ipk_med=('ipk','median'),t_end_med=('t_end','median')).round(3).to_string())
# 6. gdzie w zapisie wystepuje zanik
f['lo_rel_end']=f.t_after_lo*1e3
print('t od konca zaniku do konca zapisu [ms]: szybkie',f[f.is_fast==True].lo_rel_end.describe().round(1).to_dict()); print('wolne',f[f.is_fast==False].lo_rel_end.describe().round(1).to_dict())
print('szczyt Ip [MA]: szybkie',round(f[f.is_fast==True].ipk.median()/1e6,3),'wolne',round(f[f.is_fast==False].ipk.median()/1e6,3))
print('t_peak->poczatek zaniku [ms] mediana: szybkie',round(f[f.is_fast==True].flat_before.median()*1e3,1),'wolne',round(f[f.is_fast==False].flat_before.median()*1e3,1))
print('wykrycia bridge / strzal: szybkie',f[f.is_fast==True].n_bridge.mean().round(2),'wolne',f[f.is_fast==False].n_bridge.mean().round(2))
f.to_csv('/tmp/w/explore_features.csv',index=False)
