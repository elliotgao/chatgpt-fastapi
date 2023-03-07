#!/bin/bash
# current working directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd $DIR
source ./venv/bin/activate

APP_NAME="ChatGPT-ChatRoom-Server"
APP_PATH="main:app"
APP_LOG="$DIR/console.log"
HOST="0.0.0.0"
PORT="8080"

COLOR_RED="\x1b[31m"
RESET="\x1b[0m"

# inspect params
function alertUsage() {
  echo "usage: $0 {start|stop|kill|restart|debug} [--host host] [--port port]"
  echo "start, stop, restart, or debug $APP_NAME with optional host and port parameters."
}
function alertUsageError() {
  echo -e "$COLOR_RED error: Invalid parameters $RESET"
  alertUsage
  exit 1
}
if [ $# -lt 1 ]; then
  alertUsageError
fi
COMMAND=$1
if [[ ! "$COMMAND" =~ ^(start|stop|kill|restart|debug)$ ]]; then
  alertUsageError
fi

# assign params
while [[ $# -gt 0 ]]; do
  key="$1"

  case $key in
  start | stop | kill | restart | debug)
    COMMAND="$1"
    shift
    ;;
  --host)
    HOST="$2"
    shift
    shift
    ;;
  --port)
    PORT="$2"
    shift
    shift
    ;;
  *)
    alertUsageError
    exit 1
    ;;
  esac
done

# main task
function getPID() {
  echo $(ps -ef | grep "$DIR/venv/bin/uvicorn" | grep -v grep | awk '{print $2}')
}
PID=$(getPID)
function launchService() {
  nohup uvicorn $APP_PATH --host $HOST --port $PORT > $APP_LOG 2>&1 &
  echo "tail -f -n 100 $APP_LOG"
  tail -f -n 100 $APP_LOG &
}
function alertAppAlreadyRun() {
  echo -e "$COLOR_RED error: $APP_NAME <$PID> is already running. $RESET"
}
function alertAppNotRun() {
  echo -e "$COLOR_RED error: $APP_NAME is not running. $RESET"
}
function kill_tail() {
  kill $(ps aux | grep "tail -f -n 100 $APP_LOG" | awk '{print $2}') > /dev/null 2>&1
}
function kill_app() {
  signal=${2:-15}
  if [ -z "$signal" ]; then
    signal=15
  fi
  kill -$signal $PID
  kill_tail
}

case $COMMAND in
start)
  if [[ ${#PID} -gt 0 ]]; then
    alertAppAlreadyRun
    exit 1
  fi
  echo "Starting $APP_NAME..."
  launchService
  ;;
debug)
  if [[ ${#PID} -gt 0 ]]; then
    alertAppAlreadyRun
    exit 1
  fi
  export CHATGPT_CHATROOM_SERVER_DEBUG=1
  echo "Starting $APP_NAME in debug mode..."
  launchService
  ;;
stop)
  kill_tail
  if [[ ${#PID} -eq 0 ]]; then
    alertAppNotRun
    exit 1
  fi
  echo "exiting $APP_NAME <$PID>..."
  kill_app
  ;;
kill)
  kill_tail
  if [[ ${#PID} -eq 0 ]]; then
    alertAppNotRun
    exit 1
  fi
  echo "killing -9 <$PID>..."
  kill_app 9
  ;;
restart)
  if [[ ${#PID} -gt 0 ]]; then
    echo "Stopping $APP_NAME <$PID>..."
    kill_app
    sleep 1
  fi
  echo "Restarting $APP_NAME..."
  launchService
  ;;
esac
