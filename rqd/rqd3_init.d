#!/bin/sh
#
# RQD3:    Start/stop rqd3 services
#
# chkconfig:    345 98 02
# description:  RQD for spicue3
#

# Source function library.
. /etc/rc.d/init.d/functions

IS_ON=/sbin/chkconfig

RQD_PATH=/usr/local/spi/rqd3/

RQD=${RQD_PATH}rqd.py

start()
{
    [ -f /usr/local/etc/sweatbox.csh ] && echo "Refusing to start RQD3 on a sweatbox" && exit 0
    echo -n $"Starting rqd3 services:"
    cd ${RQD_PATH}
    daemon "${RQD}" -d
    echo ""
}

idle_restart()
{
    echo -n "Requesting idle restart of rqd3 services:"
    cd ${RQD_PATH}
    daemon "./cuerqd.py" -restart
    echo ""
}

stop()
{
    echo -n "Stopping rqd3 services:"
    cd ${RQD_PATH}
    daemon "./cuerqd.py" -exit_now
    sleep 2
    killproc ${RQD}  >/dev/null 2>&1 || :
    echo ""
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
  idle-restart)
        idle_restart
        ;;
  *)
        echo $"Usage: $0 {start|stop|restart|idle_restart}"
        exit 1
        ;;
esac

exit 0
