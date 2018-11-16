# Watchtorian
System monitor for Raspbian/Debian systems, can email and publish to MQTT

### Before you begin
You'll need to install either configure your own app in Chrome store
or use the existing one.
Place the key in the `~/.credentials/` folder 
On the first run, a sendEmail.json file will be created (user interactive?)



### Install
 ```
 pip3 install psutil
 pip3 install --upgrade google-api-python-client
 pip3 install httplib2
 pip3 install oauth2client
 pip3 install paho-mqtt
 mkdir -p ~/projects/Watchtorian
 cd ~/projects
 wget https://github.com/SupremeC/Watchtorian/archive/master.zip
 unzip master.zip
 mv Watchtorian-master/* ./Watchtorian
 rm -rf Watchtorian-master
 rm master.zip
  ```
Give read access to ~/.credentials/sendEmail.json file

### Configuration
logging_config.ini
config.ini


### Manual run
 ```
cd ~/projects/Watchtorian/watchtorian.py
python3 watchtorian.py
 ```
 
### Scheduled run
 ```
crontab -e
0 * * * * python3 /home/[username]/projects/Watchtorian/watchtorian.py
 ```