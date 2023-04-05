ffmpeg -y -i $1 -ar 16000 -ac 1 -c:a pcm_s16le $1.wav
../main $1.wav -otxt -m ../models/ggml-base.bin
