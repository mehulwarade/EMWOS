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
/bin/chmod +x mImgtbl

printf "\n##################### Checking file integrity for input files #####################\n"  1>&2
# do file integrity checks
pegasus-integrity --print-timings --verify=stdin 1>&2 << 'eof'
cposs2ukstu_red_001_005.fits:cposs2ukstu_red_001_002.fits:cposs2ukstu_red_002_003.fits:cposs2ukstu_red_003_001.fits:cposs2ukstu_red_001_006.fits:cposs2ukstu_red_006_005.fits:2-corrected.tbl:cposs2ukstu_red_005_004.fits:cposs2ukstu_red_004_003.fits:cposs2ukstu_red_003_005.fits:cposs2ukstu_red_004_006.fits:cposs2ukstu_red_006_002.fits:cposs2ukstu_red_005_001.fits:cposs2ukstu_red_003_002.fits:cposs2ukstu_red_002_001.fits:cposs2ukstu_red_001_003.fits:cposs2ukstu_red_002_004.fits:cposs2ukstu_red_004_001.fits:cposs2ukstu_red_001_001.fits:cposs2ukstu_red_002_002.fits:mImgtbl:cposs2ukstu_red_003_003.fits:cposs2ukstu_red_005_005.fits:cposs2ukstu_red_006_003.fits:cposs2ukstu_red_001_004.fits:cposs2ukstu_red_006_006.fits:cposs2ukstu_red_003_006.fits:cposs2ukstu_red_002_005.fits:cposs2ukstu_red_004_004.fits:cposs2ukstu_red_005_002.fits:cposs2ukstu_red_004_002.fits:cposs2ukstu_red_004_005.fits:cposs2ukstu_red_003_004.fits:cposs2ukstu_red_005_006.fits:cposs2ukstu_red_002_006.fits:cposs2ukstu_red_006_001.fits:cposs2ukstu_red_005_003.fits:cposs2ukstu_red_006_004.fits
eof

pegasus_lite_section_end stage_in
set +e
job_ec=0
pegasus_lite_section_start task_execute
printf "\n######################[Pegasus Lite] Executing the user task ######################\n"  1>&2
pegasus-kickstart  -n mImgtbl -N ID0001412 -R condorpool  -s 2-updated-corrected.tbl=2-updated-corrected.tbl -L montage -T 2023-12-14T00:10:51+00:00 ./mImgtbl . -t 2-corrected.tbl 2-updated-corrected.tbl
job_ec=$?
pegasus_lite_section_end task_execute
set -e
pegasus_lite_section_start stage_out
pegasus_lite_section_end stage_out

set -e


# clear the trap, and exit cleanly
trap - EXIT
pegasus_lite_final_exit

