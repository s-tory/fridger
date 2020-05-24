#!/bin/sh
sudo cp -f fridger.service /etc/systemd/system
sudo chown root:root /etc/systemd/system/fridger.service
sudo chmod 644 /etc/systemd/system/fridger.service
sudo systemctl daemon-reload
sudo systemctl enable fridger.service
sudo systemctl start fridger.service
sudo systemctl status fridger.service