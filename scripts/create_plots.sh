#!/bin/bash
# Run this script from crontab periodically to create plots and upload to web site.

# cd to the directory where the script is located.
cd "$(dirname "$0")"

# OMDBO
echo "OMDBO helicorders"
/usr/bin/python3 plot_helicorders_and_spectrum.py

# GBLCO
echo "GBLCO helicorders"
/usr/bin/python3 plot_helicorders_and_spectrum_gblco.py

# XXXX
echo "XXXXX helicorders"
/usr/bin/python3 plot_helicorders_and_spectrum_xxxxx.py

# Create PPSD plots every 4 hours.
if [ ! -f ./ppsd_AM_OMDBO_01_BHZ.png -o "$(find ./ppsd_AM_OMDBO_01_BHZ.png -mmin +240)" ]; then
    echo "OMDBO PPSD"
    /usr/bin/python3 plot_ppsd.py \
        --path /data/seismometer_data/mseed \
        --respfile AM_OMDBO.xml \
        --channel AM.OMDBO.01.BHZ \
        --outfile ppsd_AM_OMDBO_01_BHZ.png \
        --segment_len=3600 \
        --segment_overlap=0.5 \
        --rotate 10
fi
if [ ! -f ./ppsd_AM_GBLCO_01_BHZ.png -o "$(find ./ppsd_AM_GBLCO_01_BHZ.png -mmin +240)" ]; then
    echo "GBLCO PPSD"
    /usr/bin/python3 plot_ppsd.py \
        --path /data/seismometer_data/mseed \
        --respfile AM_GBLCO.xml \
        --channel AM.GBLCO.01.BHZ \
        --outfile ppsd_AM_GBLCO_01_BHZ.png \
        --segment_len=3600 \
        --segment_overlap=0.5 \
        --rotate 10
fi
if [ ! -f ./ppsd_AM_XXXXX_01_BHZ.png -o "$(find ./ppsd_AM_XXXXX_01_BHZ.png -mmin +240)" ]; then
    echo "XXXXX PPSD"
    /usr/bin/python3 plot_ppsd.py \
        --path /data/seismometer_data/mseed \
        --respfile AM_XXXXX.xml \
        --channel AM.XXXXX.01.BHZ \
        --outfile ppsd_AM_XXXXX_01_BHZ.png \
        --segment_len=3600 \
        --segment_overlap=0.5 \
        --rotate 10
fi
if [ ! -f ./ppsd_UO_WAGON__HHZ.png -o "$(find ./ppsd_UO_WAGON__HHZ.png -mmin +240)" ]; then
    echo "UO.WAGON..HHZ PPSD"
    # WAGON - 20 miles SE of GBLCO
    # Trillium Cascadia Compact
    /usr/bin/python3 plot_ppsd.py \
        --iris \
        --channel UO.WAGON..HHZ \
        --respfile UO_WAGON.xml \
        --outfile ppsd_UO_WAGON__HHZ.png \
        --segment_len=3600 \
        --segment_overlap=0.5 \
        --rotate 10
fi

# Generate temperature plots.
# These are hanging at the moment...
echo "Daily temperature plots"
/usr/bin/python3 plot_daily_temperature.py

# Copy the latest helicorder files to the server.
# SSH was previously set up for certificate authentication.
# webserver_host is an alias defined in ~/.ssh/config
HOST="webserver_host"
DEST="~/www/yuma/"
SRCS=""
SRCS+="helicorder_broadband_AM_OMDBO_01_BHZ.png "
SRCS+="helicorder_broadband_AM_GBLCO_01_BHZ.png "
SRCS+="helicorder_broadband_AM_XXXXX_01_BHZ.png "
SRCS+="helicorder_broadband_annotated_AM_OMDBO_01_BHZ.png "
SRCS+="helicorder_broadband_annotated_AM_GBLCO_01_BHZ.png "
SRCS+="helicorder_broadband_annotated_AM_XXXXX_01_BHZ.png "
SRCS+="helicorder_teleseismic_AM_OMDBO_01_BHZ.png "
SRCS+="helicorder_teleseismic_AM_GBLCO_01_BHZ.png "
SRCS+="helicorder_teleseismic_AM_XXXXX_01_BHZ.png "
SRCS+="helicorder_teleseismic_annotated_AM_OMDBO_01_BHZ.png "
SRCS+="helicorder_teleseismic_annotated_AM_GBLCO_01_BHZ.png "
SRCS+="helicorder_teleseismic_annotated_AM_XXXXX_01_BHZ.png "
SRCS+="ppsd_AM_OMDBO_01_BHZ.png "
SRCS+="ppsd_AM_GBLCO_01_BHZ.png "
SRCS+="ppsd_AM_XXXXX_01_BHZ.png "
SRCS+="ppsd_UO_WAGON__HHZ.png "
SRCS+="daily_temperature_AM_OMDBO_01.png "
SRCS+="daily_temperature_AM_GBLCO_01.png "
SRCS+="daily_temperature_AM_XXXXX_01.png "
echo "Copying files: ${SRCS}"
scp ${SRCS} ${HOST}:${DEST}

# Copy most recent spectrums to a staging directory. 
mkdir -p staging
find . -maxdepth 1 -type f -name "spectrum_*.png" -mtime -3 -exec cp -aRpf {} ./staging/ \;

# Delete spectrums older than 3 days.
find staging/ -type f -name "spectrum_*.png" -mtime +3 -delete

NUM_FILES=$(ls staging |wc -l)
echo "Staging ${NUM_FILES} spectrograms..."

# Rsync the spectrogram files to the server. Delete files that don't exist in the staging dir.
DEST="~/www/yuma/spectrum"
echo "Running rsync"
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
echo "Generating index"
ssh -t ${HOST} "cd ${DEST} && ${INDEX_CMD}"

