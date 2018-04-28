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
   start) python $HERE/main.py -c motion </dev/null >$HERE/log/garden.err 2>&1 &
          ;;
    stop) pkill -f $HERE/main.py ;;
       *) echo "usage is $BASH_SOURCE start/stop" 
          exit ;;
esac

# End
