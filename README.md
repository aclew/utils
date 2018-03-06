# varia
Various intermediate scripts useful to the ACLEW project

# Required

* [pympi](https://github.com/dopefishh/pympi) 
* [tgt](https://github.com/hbuschme/TextGridTools/)

# RTTM

RTTM is an annotaion format for audio files well designed for diarization. Explanations about how to write and read .rttm files can be found [here](https://catalog.ldc.upenn.edu/docs/LDC2004T12/RTTM-format-v13.pdf)

We provide code to translate annotations from other formats into RTTM:

**ELAN .eaf fromat**

WARNING: the current version does not handle subtypes when parsing annotations e.g. TIER\_ID 'CHI' would be written in the RTTM output file but 'vmc@CHI' would not. This is due to the time references being based on other TIER\_ID's annotations for subtypes. 

You should run the script as follows:

```
python elan2rttm.py -i my_file.eaf -o my_output_folder
```

**Praat TextGrid format**

You should run the script as follows:

```
python textgrid2rttm.py my_input_folder
```
