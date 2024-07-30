#!/bin/sh
#
# RQD3:    Start/stop rqd3 services
#
# chkconfig:    345 98 02
# description:  Opencue RQD agent
#

# Source function library.
. /etc/rc.d/init.d/functions

IS_ON=/sbin/chkconfig

RQD_PATH=/usr/local/spi/rqd3/

RQD=${RQD_PATH}rqd.py

start()
{
    [ -f /usr/local/etc/sweatbox.csh ] && echo "Refusing to start RQD3 on a sweatbox" && exit 0
    echo -n $"Starting openrqd services:"
    cd ${RQD_PATH}
    daemon "${RQD}" -d
    echo ""
}

stop()
{
    echo -n "Stopping openrqd services:"
    cd ${RQD_PATH}
    daemon "rqd/cuerqd.py" --exit_now
    echo "Stop Request completed"
}

case "$1" in
  start)
        start
        ;;
  stop)
        stop
        ;;
  restart)
        stop
        sleep 3
        start
        ;;
  *)
        echo $"Usage: $0 {start|stop|restart|idle_restart}"
        exit 1
        ;;
esac

exit 0
