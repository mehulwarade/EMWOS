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
/bin/chmod +x mAdd

printf "\n##################### Checking file integrity for input files #####################\n"  1>&2
# do file integrity checks
pegasus-integrity --print-timings --verify=stdin 1>&2 << 'eof'
cposs2ukstu_ir_003_004_area.fits:cposs2ukstu_ir_003_006.fits:cposs2ukstu_ir_001_004.fits:cposs2ukstu_ir_001_002_area.fits:cposs2ukstu_ir_006_002_area.fits:cposs2ukstu_ir_005_002.fits:cposs2ukstu_ir_004_004.fits:cposs2ukstu_ir_006_006.fits:cposs2ukstu_ir_005_006_area.fits:cposs2ukstu_ir_003_001.fits:cposs2ukstu_ir_005_003.fits:cposs2ukstu_ir_006_001.fits:cposs2ukstu_ir_005_003_area.fits:3-updated-corrected.tbl:cposs2ukstu_ir_004_005.fits:cposs2ukstu_ir_002_005_area.fits:cposs2ukstu_ir_002_002.fits:cposs2ukstu_ir_003_001_area.fits:cposs2ukstu_ir_001_006_area.fits:cposs2ukstu_ir_003_005_area.fits:cposs2ukstu_ir_002_002_area.fits:cposs2ukstu_ir_001_003.fits:cposs2ukstu_ir_004_004_area.fits:cposs2ukstu_ir_006_006_area.fits:cposs2ukstu_ir_002_003.fits:cposs2ukstu_ir_001_003_area.fits:cposs2ukstu_ir_004_001_area.fits:cposs2ukstu_ir_005_004_area.fits:region.hdr:cposs2ukstu_ir_001_006.fits:cposs2ukstu_ir_003_002_area.fits:cposs2ukstu_ir_005_004.fits:cposs2ukstu_ir_003_002.fits:cposs2ukstu_ir_002_006_area.fits:cposs2ukstu_ir_005_001.fits:cposs2ukstu_ir_006_003_area.fits:cposs2ukstu_ir_003_005.fits:cposs2ukstu_ir_002_003_area.fits:cposs2ukstu_ir_002_005.fits:cposs2ukstu_ir_004_001.fits:mAdd:cposs2ukstu_ir_003_003.fits:cposs2ukstu_ir_005_001_area.fits:cposs2ukstu_ir_005_005.fits:cposs2ukstu_ir_004_005_area.fits:cposs2ukstu_ir_006_003.fits:cposs2ukstu_ir_004_002.fits:cposs2ukstu_ir_006_004.fits:cposs2ukstu_ir_002_006.fits:cposs2ukstu_ir_005_006.fits:cposs2ukstu_ir_006_004_area.fits:cposs2ukstu_ir_003_004.fits:cposs2ukstu_ir_001_004_area.fits:cposs2ukstu_ir_003_006_area.fits:cposs2ukstu_ir_004_002_area.fits:cposs2ukstu_ir_001_001.fits:cposs2ukstu_ir_001_001_area.fits:cposs2ukstu_ir_004_006_area.fits:cposs2ukstu_ir_003_003_area.fits:cposs2ukstu_ir_006_005.fits:cposs2ukstu_ir_002_001.fits:cposs2ukstu_ir_005_005_area.fits:cposs2ukstu_ir_006_001_area.fits:cposs2ukstu_ir_002_004_area.fits:cposs2ukstu_ir_001_005.fits:cposs2ukstu_ir_001_002.fits:cposs2ukstu_ir_001_005_area.fits:cposs2ukstu_ir_005_002_area.fits:cposs2ukstu_ir_006_005_area.fits:cposs2ukstu_ir_002_004.fits:cposs2ukstu_ir_004_003_area.fits:cposs2ukstu_ir_004_006.fits:cposs2ukstu_ir_006_002.fits:cposs2ukstu_ir_002_001_area.fits:cposs2ukstu_ir_004_003.fits
eof

pegasus_lite_section_end stage_in
set +e
job_ec=0
pegasus_lite_section_start task_execute
printf "\n######################[Pegasus Lite] Executing the user task ######################\n"  1>&2
pegasus-kickstart  -n mAdd -N ID0002120 -R condorpool  -s 3-mosaic_area.fits=3-mosaic_area.fits -s 3-mosaic.fits=3-mosaic.fits -L montage -T 2023-12-14T00:10:51+00:00 ./mAdd -e 3-updated-corrected.tbl region.hdr 3-mosaic.fits
job_ec=$?
pegasus_lite_section_end task_execute
set -e
pegasus_lite_section_start stage_out
pegasus_lite_section_end stage_out

set -e


# clear the trap, and exit cleanly
trap - EXIT
pegasus_lite_final_exit

