#!/bin/bash
#
# author: the ACLEW team
#
# This script converts all the mp3's downloaded from databrary
# into wav and rename them id.wav (by extracting the id from the name
# exported by databrary).
# it also reads the .eaf file and extracts small wav files containing 
# only the transcribed parts, along with their transcription in .rttm format


# function to convert all the mp3's into wav, and rename them with the id
convert2wav() {
# convert all the .mp3 files in $1 to .wav files that have
# only the id as name
for fin in `ls $1/*.mp3`; do
    # retrieve ID within the name exported by databrary
    base=$(basename $fin .mp3)
    # this works if the name has "audio" or not at the end
    id=`echo $base | cut -d '_' -f 1 | cut -d '-' -f 15`
    # call sox to convert
    sox $fin $1/${id}.wav
done
}

# read the corpus path
corpus=$(readlink -f $1)

# convert the mp3s into wav
convert2wav $corpus

# extract the transcribed parts
for wav in `ls $corpus/*.wav`; do
    base=$(basename $wav .wav)
    eaf=$corpus/raw_$corpus/${base}.eaf
    python adjust_timestamps.py $eaf $wav
done
