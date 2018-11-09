import sys
import os
import argparse
import re
import glob
import numpy as np
from scipy.io import wavfile

def cutter(path_to_rttm, frame_length, output_file, prefix, labels_map):
    """
    Given a rttm file, create a new file whose represents the same rttm cutted in frames.
    If one frame has been classified as several classes in the original rttm, it concatenates classes.
    Note that all of the frames that have not been classified in the original rttm are considered as being SIL.
    Note that it will read the associated wav file to get the total duration of the recording.

    Parameters
    ----------
    path_to_rttm :      path to the rttm file.
    frame_length :      frame length.
    output_file :       path to the output file.
    prefix :            the prefix that needs to be remove (from rttm) to map the rttm to the wav file.
    labels_map :        to map the labels from original rttm (values) to the output rttm (keys).

    Write a rttm whose name is the same than the rttm's one suffixed by _cutted.rttm
    """
    basename = os.path.splitext(os.path.basename(path_to_rttm))[0]
    if prefix != "":
        basename = basename.split(prefix)[1]
    dirname = os.path.dirname(path_to_rttm)
    wav_path = os.path.join(dirname,basename+'.wav')
    if os.path.isfile(wav_path):
        fs, data = wavfile.read(wav_path)
        tot_dur_s = len(data)*1.0/fs
    else:
        print("Something went wrong while reading the wav file %s. Can not get total duration..." % wav_path)
        sys.exit(1)

    frame_length_s = float(frame_length)/1000.0
    frames = np.arange(0.0, tot_dur_s, frame_length_s)
    # We don't want to loose any data
    if frames[-1] < tot_dur_s:
        frames = np.append(frames, frames[-1]+frame_length_s)

    with open(path_to_rttm, 'r') as rttm:
        with open(output_file, 'w') as output:
            onset_prev_s = 0.0
            dur_prev_s = 0.0
            act_prev = None
            append_prev = False
            onset_s = None

            for line in rttm:
                line = line.replace('\t', ' ')
                line = re.sub('\s+', ' ', line).strip()
                anno_fields = line.split(' ')
                onset_s = float(anno_fields[3])
                dur_s = float(anno_fields[4])
                curr_activity = anno_fields[7]

                if onset_s > onset_prev_s + dur_prev_s : #There's been silence just before !
                    sil_dur_s = onset_s - onset_prev_s - dur_prev_s
                    onset_sil_s = onset_prev_s + dur_prev_s
                    single_activity_cutter(basename, output, frame_length_s,
                                           sil_dur_s, onset_sil_s, 'SIL', tot_dur_s, labels_map)
                    act_prev = 'SIL'
                    dur_prev_s = sil_dur_s
                    onset_prev_s = onset_sil_s

                single_activity_cutter(basename, output, frame_length_s,
                                       dur_s, onset_s, curr_activity, tot_dur_s, labels_map)

                # Update previous fields
                act_prev = curr_activity
                dur_prev_s = dur_s
                onset_prev_s = onset_s

            # Fill the last one by SILENCE
            ## Handle empty rttm
            if onset_s is None:
                onset_s = 0.0
                dur_s = 0.0

            if onset_s + dur_s < tot_dur_s:
                sil_dur_s = tot_dur_s - onset_s-dur_s
                onset_sil_s = onset_s + dur_s
                single_activity_cutter(basename, output, frame_length_s,
                                       sil_dur_s, onset_sil_s, 'SIL', tot_dur_s, labels_map)


def single_activity_cutter(basename, output, frame_length_s, dur_s, onset_s, curr_activity, tot_dur_s, labels_map):
    """
    Given an activity, its onset and its duration, cut it into frames of length frame_length_s.

    Parameters
    ----------
    basename        The basename of the input rttm.
    output          The path of the output file.
    frame_length_s  The frame length (in s).
    dur_s           The duration of the current activity (in s).
    onset_s         The onset of the current activity (in s).
    curr_activity   The current activity.
    labels_map :    To map the labels from original rttm (values) to the output rttm (keys).

    """
    # We don't want to consider any fake labels generated after the duration of the wav file
    if onset_s + dur_s > tot_dur_s:
        dur_s = max(tot_dur_s - onset_s, 0)
        if onset_s > tot_dur_s:
            onset_s = 0.0

    diff_s = onset_s - int(onset_s / frame_length_s) * frame_length_s
    onset_s = int(onset_s / frame_length_s) * frame_length_s
    n_frames = int((dur_s+diff_s) / frame_length_s)
    # Get the output label (we want a full match or nothing)
    activity = [k for k,v in labels_map.items() if re.match("("+v+")\Z", curr_activity) is not None]
    if len(activity) != 1:
        print("Can not map the input label to the output one : %s" % curr_activity)
        sys.exit(1)
    else:
        activity = activity[0]

    for i in range(0, n_frames):
        output.write("SPEAKER %s 1 %s %s <NA> <NA> %s <NA>\n" % \
                     (basename, onset_s + frame_length_s * i,
                      str(frame_length_s), activity))

    if not np.isclose(onset_s + frame_length_s * n_frames, onset_s+dur_s+diff_s, rtol=1e-05, atol=1e-08, equal_nan=False):
        output.write("SPEAKER %s 1 %s %s <NA> <NA> %s <NA>\n" % \
                     (basename, onset_s + frame_length_s * n_frames,
                      str(frame_length_s), activity))


def aggregate_overlap(path_to_rttm, output_file):
    """
    Given a cutted rttm file, aggregate the activities that happen in the same time.
    The class of the generated frame will take the form of spkr1/spkr2 ...

    Parameters
    ----------
    path_to_rttm        Path to the input rttm file that have been previously cutted.
    output_file         Path to the output file.
    """
    basename = os.path.splitext(os.path.basename(path_to_rttm))[0]
    with open(path_to_rttm, 'r') as rttm:
        with open(output_file, 'w') as output:
            lines = rttm.readlines()
            lines = sorted(lines, key=lambda line: float(line.split()[3]))
            k = 0
            while k < len(lines):       # Loop through the whole file
                line_k = lines[k].split()
                onset_k, dur_k, act_k = line_k[3], line_k[4], line_k[7]
                frame_activity = [act_k]
                j = k + 1
                while j < len(lines):   # Loop through the activities that have the same onset
                    line_j = lines[j].split()
                    onset_j, dur_j, act_j = line_j[3], line_j[4], line_j[7]
                    if onset_k != onset_j:
                        output.write("SPEAKER %s 1 %s %s <NA> <NA> %s <NA>\n" % \
                                     (basename, onset_k, dur_k, '/'.join(frame_activity)))
                        break
                    else:   # onset_k == onset_j:
                        if act_j not in frame_activity:
                            frame_activity.append(act_j)
                            frame_activity.sort()   # Consider alphabetical order
                        k += 1
                    j += 1
                k += 1

            output.write("SPEAKER %s 1 %s %s <NA> <NA> %s <NA>\n" % \
                         (basename, onset_k, dur_k, '/'.join(frame_activity)))




def main():
    parser = argparse.ArgumentParser(description="convert a rttm file into another rttm cutted in frames.")
    parser.add_argument('-i', '--input', type=str, required=True,
                        help="path to the input .rttm file or the folder containing rttm files.")
    parser.add_argument('-l', '--length', type=float, required=False, default=100.0,
                        help="the frame length in ms (Default to 100 ms).")
    parser.add_argument('-p', '--prefix', type=str, default="",
                        help="the prefix that needs to be removed to map the rttm to the wav.")
    args = parser.parse_args()

    labels_map = {"CHI": "CHI.?|CXN|CHN|C.?",
                  "FEM": "FAN|FAF|FEM|F|MOT.?|FA.?",
                  "MAL": "MAL|M|MAN|MA.?",
                  "SIL": "SIL|S"}

    # Initialize the output folder as the same folder than the input
    # if not provided by the user.
    if args.input[-5:] == '.rttm':
        output = os.path.dirname(args.input)
    else:
        output = args.input

    data_dir = '/vagrant'
    args.input = os.path.join(data_dir, args.input)
    output = os.path.join(data_dir, output)

    if not os.path.isdir(output):
        os.mkdir(output)

    if args.input[-5:] == '.rttm':   # A single file has been provided by the user
        output = os.path.splitext(args.input)[0]+'_cutted.rttm'
        print(output)
        cutter(args.input, args.length, output+'.tmp', args.prefix, labels_map)
        aggregate_overlap(output+'.tmp', output)
        os.remove(output+'.tmp')
    else:                           # A whole folder has been provided
        rttm_files = glob.iglob(os.path.join(args.input, '*.rttm'))
        for rttm_path in rttm_files:
            print("Processing %s" % rttm_path)
            output = os.path.splitext(rttm_path)[0] + '_cutted.rttm'
            cutter(rttm_path, args.length, output + '.tmp', args.prefix, labels_map)
            aggregate_overlap(output + '.tmp', output)
            os.remove(output + '.tmp')

if __name__ == '__main__':
    main()