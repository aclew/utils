#!/usr/bin/env python
#
#
import pympi as pmp
import shutil
import os
import argparse
import subprocess
import ipdb
from collections import defaultdict
from operator import itemgetter


def eaf2rttm(path_to_eaf):
    """
    function to write a new .rttm file which is a transcription of the .eaf
    given as input

    """

    # in EAF, timestamps are in milliseconds, convert them to seconds
    # TODO read scale from header of EAF
    sampling_freq = 1000.0

    print('\n')
    # read eaf file
    EAF = pmp.Elan.Eaf(path_to_eaf)

    participants = []

    # gather all the talker's names
    for k in EAF.tiers.keys():

        if 'PARTICIPANT' in EAF.tiers[k][2].keys():

            if EAF.tiers[k][2]['PARTICIPANT'] not in participants:

                participants.append(EAF.tiers[k][2]['PARTICIPANT'])

    print('participants: {}'.format(participants))

    base = os.path.basename(path_to_eaf)
    name = os.path.splitext(base)[0]

    print('parsing file: {}'.format(name))

    # extract all the speech segments
    rttm = []
    for participant in participants:

        for _, val in EAF.tiers[participant][0].items():

            start = val[0]
            end = val[1]

            t0 = EAF.timeslots[start] / sampling_freq
            length = EAF.timeslots[end] / sampling_freq - t0

            rttm.append((name, t0, length, participant))
    return rttm

def write_rttm(rttm_path, annotations):
    """ write annotations to rttm_path"""

    # write the annotations in rttm formats
    with open(rttm_path, 'w') as fout:
        for name, t0, length, participant in annotations:
            fout.write(u"SPEAKER\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format
                       (name, 1, "%.3f" %t0, "%.3f" %length,
                        "<NA>", "<NA>", participant, 1 ))

def get_all_on_offs(eaf):
    """ 
        Return all the annotated intervals from the current file
    """
    EAF = pmp.Elan.Eaf(eaf)

    all_intervals = EAF.tiers['on_off'][0]

    # get the segments delimited for "on_off" tier,
    # as those give the timestamps between which are the annotations
    # TODO check if convention ??? (not found in ACLEW DAS)
    on_offs = []
    for key in all_intervals:
        interv = all_intervals[key]
        beg_end = interv[2]
        beg, end = [float(time) for time in beg_end.split('_')]
        # store in seconds, not milliseconds
        on_offs.append((beg/1000.0, end/1000.0))

    return on_offs

def cut_audio(on_offs, input_audio):
    """
        Extract from the daylong recordings the small parts that have
        been annotated
    """

    # for each annotated segment, call sox to extract the part from the
    # wav file
    for on, off in on_offs:
        audio_base = os.path.splitext(input_audio)[0]
        output_audio = '_'.join([audio_base, str(int(on)), str(int(off))]) + '.wav'
        cmd = ['sox', input_audio, output_audio,
               'trim', str(on), str(off - on)]
        #print " ".join(cmd)
        subprocess.call(cmd)

def extract_from_rttm(on_offs, rttm):
    """
        For each minute of annotation, extract the annotation of that minute
        from the transcription and write a distinct .rttm file with all the
        timestamps with reference to the begining of that segment.
    """
    sorted_rttm = sorted(rttm, key=itemgetter(1))

    # create dict { (annotated segments) -> [annotation] }
    extract_rttm = defaultdict(list)
    for on, off in on_offs:
        for name, t0, length, participant in sorted_rttm:
            end = t0 + length
            if (on <= t0 < off) or (on <= end < off):
                # if the current annotation is (at least partially)
                # contained in the current segment, append it.
                # Adjust the segment to strictly fit in on-off
                t0 = max(t0, on)
                end = min(end, off)
                length = end - t0
                extract_rttm[(on, off)].append((name, t0 - on,
                                                length, participant))
            elif (on > t0) and (end >= off):
                # if the current annotation completely contains the annotated
                # segment, add it also. This shouldn't happen, so print a 
                # warning also.
                print('Warning: speaker speaks longer than annotated segment.\n'
                      'Please check annotation from speaker {},'
                      'between {} {}, segment {} {}.\n'.format(name, t0,
                                                               end, on, off))
                extract_rttm[(on, off)].append((name, 0, off - on, participant))
            elif (end < on):
                # wait until reach segment
                continue
            elif (t0 >= off):
                # no point in continuing further since the rttm is sorted.
                break

    return extract_rttm

def main():
    """
        Take as input one eaf and wav file, and extract the segments from the
        wav that have been annotated.
    """
    # read argument
    parser = argparse.ArgumentParser(description="extract annotated segments\n"
                                                 "usage:\n"
                                                 "python adjust_timestamps.py eaf wav\n"
                                                 "where eaf is transcription, "
                                                 "and wav is the audio")
    parser.add_argument('eaf', type=str)
    parser.add_argument('wav', type=str)
    args = parser.parse_args()

    # read transcriptions
    complete_rttm = eaf2rttm(args.eaf)

    # extract annotated segments
    on_offs = get_all_on_offs(args.eaf)

    # cut audio file
    cut_audio(on_offs, args.wav)

    # cut transcription in small rttm file
    extract_rttm = extract_from_rttm(on_offs, complete_rttm)
    for key in extract_rttm:
        base = os.path.basename(args.wav)
        name = os.path.splitext(base)[0]

        rttm_path = '_'.join([name, str(int(key[0])), str(int(key[1])) ]) + '.rttm'
        write_rttm(rttm_path, extract_rttm[key])






if __name__ == '__main__':
    main()
