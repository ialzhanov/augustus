#!/bin/bash
# Downloads the CC0 photo textures (ambientCG, 1K JPG) that blender/c3.py and the sprite scripts use, into tex/.
cd "$(dirname "$0")"; mkdir -p tex
for id in Fabric061 Ground108 Ground054 Ground037 Grass004 Grass001 Planks037A RoofingTiles006 Plaster007 Rock064 Gravel023; do
  [ -d tex/$id ] && continue
  mkdir -p tex/$id
  curl -sfL -o tex/$id.zip "https://ambientcg.com/get?file=${id}_1K-JPG.zip" && unzip -oq tex/$id.zip -d tex/$id && rm tex/$id.zip
  echo "$id"
done
