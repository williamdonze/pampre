import json, math
LON0, LAT0, K = 2.5, 46.5, 100.0
C = math.cos(math.radians(46.5))
def P(lon, lat): return (round((lon-LON0)*C*K,1), round((LAT0-lat)*K,1))
def ring(r):
    pts=[]; 
    for lon,lat in r:
        p=P(lon,lat)
        if not pts or p!=pts[-1]: pts.append(p)
    if len(pts)<3: return ''
    s='M'+' '.join(f'{x:g},{y:g}' for x,y in pts)+'Z'
    return s
def geom(g):
    polys = [g['coordinates']] if g['type']=='Polygon' else g['coordinates']
    return ''.join(ring(r) for poly in polys for r in poly)
d=json.load(open('sources/departements-version-simplifiee.geojson'))
deps={f['properties']['code']:{'n':f['properties']['nom'],'d':geom(f['geometry'])} for f in d['features']}
m=json.load(open('sources/metropole-version-simplifiee.geojson'))
g=m['features'][0]['geometry'] if 'features' in m else m['geometry'] if 'geometry' in m else m
outline=geom(g)
out={'source':'Contours : france-geojson (G. David), données IGN / Etalab, Licence Ouverte','proj':{'lon0':LON0,'lat0':LAT0,'k':K,'cos':C},'deps':deps,'outline':outline}
json.dump(out,open('content/carte-france.json','w'),ensure_ascii=False,separators=(',',':'))
