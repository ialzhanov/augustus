#!/bin/zsh
# Usage: S=<work dir with dumper2/ and scripts/> GAME=<Caesar 3 data dir> ./run3.sh
S=${S:?set S}; GAME=${GAME:?set GAME}; C=$GAME/campaigns; O=$S/dumper2/out3; cd $S/dumper2; rm -rf $O; mkdir -p $O; args=()
for f in "$C/Reconquered Campaign/scenario/"*.mapx "$C/Reconquered Campaign/scenario/"*.svx "$C/Conquering Numidia/scenario/"*.mapx "$C/All Roads Lead to Rome/scenario/"*.mapx; do b=$(basename "$f" .mapx); b=${b%.svx}; k=$(echo "$b" | tr -c 'A-Za-z0-9\n' '_'); mkdir -p "$O/$k"; args+=("$f" "$O/$k"); done
./dumper3 $GAME "${args[@]}" > $O/all.txt 2>$O/err.txt
cd $O
python3 - <<'PY'
import re,os
txt=open('all.txt').read()
for blk in txt.split('##### ')[1:]:
    path=blk.split('\n',1)[0]
    b=os.path.basename(path); b=re.sub(r'\.(mapx|svx)$','',b); k=re.sub(r'[^A-Za-z0-9\n]','_',b)
    open(f'{k}/dump.txt','w').write('##### '+blk)
PY
for d in */; do python3 $S/scripts/compact.py $d > $d/compact.txt 2>$d/compact.err || echo "fail $d"; done
