Start/Stop:

  sudo systemctl start garden
  sudo systemctl stop garden

Service file:

  sudo vi /etc/systemd/system/garden.service # run "sudo systemctl daemon-reload" after changing

Enable/Disable service:

  sudo systemctl enable garden
  sudo systemctl disable garden

Monitor service log:

  journalctl -u garden.service -f

Program log:

  ./log/garden.<weekday>.log e.g. garden.Sunday.log

Watchdog:

  Service has a setting for number of seconds to live without getting a hearbeat from the program:
    Restart=on-watchdog
    WatchdogSec=60
  ..in main.py "sdnotify" is used to create a notifier and this is passed into MotionDetector
    and then checktrigger issues a heartbeat at the start of its loop via: self.notifier.notify("WATCHDOG=1")

References:

  https://www.freedesktop.org/software/systemd/man/systemd.service.html
  http://0pointer.de/blog/projects/watchdog.html

