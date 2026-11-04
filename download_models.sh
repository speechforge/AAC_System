#!/bin/bash
set -e
cd indic-generative-aac/indictts/inference/checkpoints
rm -f *.zip
for lang in hi en+hi; do
    echo "Downloading $lang..."
    wget -c "https://github.com/AI4Bharat/Indic-TTS/releases/download/v1-checkpoints-release/${lang}.zip" -O "${lang}.zip"
    echo "Unzipping $lang..."
    unzip -q -o "${lang}.zip"
    rm "${lang}.zip"
done
echo "Done!"
