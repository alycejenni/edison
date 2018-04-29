#!/bin/bash
export WORKON_HOME=/envs
export VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3
export JAVA_HOME=//usr/lib/jvm/java-8-openjdk-armhf
source /usr/local/bin/virtualenvwrapper.sh
workon garden
#
HERE=$(dirname $BASH_SOURCE)
mkdir -p $HERE/log
case ${1:-start} in
   start) rm -rf ${HERE:-xxx}/backgrounds
          export RES_WIDTH=1024
          export RES_HEIGHT=576
          python $HERE/main.py -c motion </dev/null >/home/sissy/cam/log/garden.err 2>&1 &
          ;;
    stop) pkill -f $HERE/main.py ;;
       *) echo "usage is $BASH_SOURCE start/stop" 
          exit ;;
esac

# End
