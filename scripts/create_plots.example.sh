#!/bin/bash
# Run this script from crontab periodically to create plots and upload to web site.

# cd to the directory where the script is located.
cd "$(dirname "$0")"

/usr/bin/python3 plot_helicorders_and_spectrum.py

# Copy the latest helicorder files to the server.
# SSH was previously set up for certificate authentication.
HOST="user@hostname"
DEST="~/directory/"
SRCS=""
SRCS+="helicorder_broadband_AM_OMDBO_01_BHZ.png "
SRCS+="helicorder_teleseismic_AM_OMDBO_01_BHZ.png "
scp ${SRCS} ${HOST}:${DEST}

# Copy most recent spectrums to a staging directory. 
mkdir -p staging
find . -maxdepth 1 -type f -name "spectrum_*.png" -mtime -3 -exec cp -aRpf {} ./staging/ \;

# Delete spectrums older than 3 days.
find staging/ -type f -name "spectrum_*.png" -mtime +3 -delete

NUM_FILES=$(ls staging |wc -l)
echo "Staging ${NUM_FILES} spectrograms..."

# Rsync the spectrogram files to the server. Delete files that don't exist in the staging dir.
DEST="~/directory/spectrum"
rsync -avz -e ssh --progress --delete staging/ ${HOST}:${DEST}

# On the server, generate an index of the spectrums.
INDEX_CMD=$(cat << EOF
tree -H "." \
	-L 1 \
	--noreport \
	--dirsfirst \
	--charset utf-8 \
	--ignore-case \
	--timefmt "%d-%b-%Y %H:%M" \
	-I "index.html" \
	-T "Latest seismometer spectrograms" \
	-s -D \
	-P "*.png" \
	-o index.html
EOF
)
echo ${INDEX_CMD}
ssh -t ${HOST} "cd ${DEST} && ${INDEX_CMD}"

