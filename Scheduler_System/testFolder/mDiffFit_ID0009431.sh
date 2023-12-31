#!/bin/bash
set -e
pegasus_lite_version_major="5"
pegasus_lite_version_minor="0"
pegasus_lite_version_patch="6"
pegasus_lite_enforce_strict_wp_check="true"
pegasus_lite_version_allow_wp_auto_download="true"


. pegasus-lite-common.sh

pegasus_lite_init

# cleanup in case of failures
trap pegasus_lite_signal_int INT
trap pegasus_lite_signal_term TERM
trap pegasus_lite_unexpected_exit EXIT

printf "\n########################[Pegasus Lite] Setting up workdir ########################\n"  1>&2
# work dir
export pegasus_lite_work_dir=$PWD
pegasus_lite_setup_work_dir

printf "\n##############[Pegasus Lite] Figuring out the worker package to use ##############\n"  1>&2
# figure out the worker package to use
pegasus_lite_worker_package

pegasus_lite_section_start stage_in
printf "\n##################### Setting the xbit for executables staged #####################\n"  1>&2
# set the xbit for any executables staged
/bin/chmod +x mDiff
/bin/chmod +x mFitplane
/bin/chmod +x mDiffFit

printf "\n##################### Checking file integrity for input files #####################\n"  1>&2
# do file integrity checks
pegasus-integrity --print-timings --verify=stdin 1>&2 << 'eof'
region-oversized.hdr:mDiff:pposs2ukstu_red_007_007.fits:pposs2ukstu_red_007_007_area.fits:pposs2ukstu_red_007_001.fits:mFitplane:pposs2ukstu_red_007_001_area.fits:mDiffFit
eof

pegasus_lite_section_end stage_in
set +e
job_ec=0
pegasus_lite_section_start task_execute
printf "\n######################[Pegasus Lite] Executing the user task ######################\n"  1>&2
pegasus-kickstart  -n mDiffFit -N ID0009431 -R condorpool  -s 2-fit.000061.000067.txt=2-fit.000061.000067.txt -L montage -T 2023-08-31T05:02:57+00:00 ./mDiffFit -d -s 2-fit.000061.000067.txt pposs2ukstu_red_007_001.fits pposs2ukstu_red_007_007.fits 2-diff.000061.000067.fits region-oversized.hdr
job_ec=$?
pegasus_lite_section_end task_execute
set -e
pegasus_lite_section_start stage_out
pegasus_lite_section_end stage_out

set -e


# clear the trap, and exit cleanly
trap - EXIT
pegasus_lite_final_exit

