# cron script to run Salish Sea NEMO model nowcast weather download worker.
#
# usage:
#   MEOPAR=/data/dlatorne/MEOPAR
#   NOWCAST_TOOLS=tools/SalishSeaTools/salishsea_toola/nowcast
#   0 2 * * *  ${MEOPAR}/${NOWCAST_TOOLS}/workers/weather_download.cron.sh

PYTHON=/home/dlatorne/anaconda/bin/python
NOWCAST=/data/dlatorne/MEOPAR/nowcast
CONFIG=${NOWCAST}/nowcast.yaml
${PYTHON} -m salishsea_toola.nowcast.workers.weather_download ${CONFIG} 06
