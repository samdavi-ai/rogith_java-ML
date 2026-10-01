"""Read-only source dataset audit; does not alter the source or prepared splits."""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.scripts.prepare_dataset import dhash

EXTS={'.jpg','.jpeg','.png'}
def family(stem: str) -> str: return re.sub(r'\.rf\.[0-9a-f]+$','',stem,flags=re.I)
def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument('--data-root',type=Path,required=True); p.add_argument('--report',type=Path,default=Path('ml/reports/dataset_validation.json')); a=p.parse_args()
    report={'source':str(a.data_root),'images':0,'bySplit':{},'corrupt':[],'unsupportedFiles':[],'exactDuplicateGroups':[],'crossSplitFamilies':[],'missingLabels':[],'dimensions':{},'emptyOrSmallImages':[]}
    hashes=defaultdict(list); family_splits=defaultdict(set); counts=Counter(); dimensions=Counter(); records=[]
    for split in ('train','valid','test'):
      image_dir=a.data_root/split/'images'
      for path in sorted(image_dir.iterdir() if image_dir.is_dir() else []):
        if not path.is_file(): continue
        if path.suffix.lower() not in EXTS:
         report['unsupportedFiles'].append(str(path)); continue
        report['images']+=1; counts[split]+=1; family_splits[family(path.stem)].add(split)
        if not (a.data_root/split/'labels'/f'{path.stem}.txt').is_file(): report['missingLabels'].append(str(path))
        try:
         with Image.open(path) as im:
          im.verify()
         with Image.open(path) as im:
          dims=im.size; dimensions[f'{dims[0]}x{dims[1]}']+=1
          if min(dims)<32: report['emptyOrSmallImages'].append({'path':str(path),'size':dims})
         hashes[hashlib.sha256(path.read_bytes()).hexdigest()].append(str(path))
         records.append((split,path,family(path.stem),dhash(path)))
        except Exception as exc: report['corrupt'].append({'path':str(path),'error':type(exc).__name__})
    report['bySplit']=dict(counts); report['dimensions']=dict(dimensions)
    report['exactDuplicateGroups']=[paths for paths in hashes.values() if len(paths)>1]
    report['crossSplitFamilies']=[{'family':k,'splits':sorted(v)} for k,v in family_splits.items() if len(v)>1]
    candidates=[{'distance':(left[3]^right[3]).bit_count(),'left':str(left[1]),'right':str(right[1])} for i,left in enumerate(records) for right in records[i+1:] if left[0]!=right[0] and (left[3]^right[3]).bit_count()<=3]
    report['nearDuplicateCandidatePairsAcrossSourceSplits']=len(candidates)
    report['nearDuplicateCandidateExamples']=candidates[:20]
    report['status']='PASS' if report['images'] and not report['corrupt'] and not report['crossSplitFamilies'] and not report['exactDuplicateGroups'] and not report['missingLabels'] and not report['unsupportedFiles'] and not report['emptyOrSmallImages'] else 'FAIL'
    a.report.parent.mkdir(parents=True,exist_ok=True); a.report.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps({k:report[k] for k in ('status','images','bySplit','corrupt','exactDuplicateGroups','crossSplitFamilies')},indent=2))
    if report['status']!='PASS': raise SystemExit(1)
if __name__=='__main__': main()
